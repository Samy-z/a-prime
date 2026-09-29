"""The Ollama adapter, tested against a fake transport.

No live server: the adapter's job is to enforce the pinning discipline D12
settled on, and that is testable without a GPU. What cannot be tested here is
whether a real server behaves as the fake does — flagged in
`docs/knowledge/systems.md` rather than assumed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime.adapter import Invocation  # noqa: E402
from aprime.systems.ollama import (  # noqa: E402
    OllamaConfig,
    OllamaSystem,
    PinMismatch,
    build_arms,
)


class FakeTransport:
    """Scriptable stand-in. `reply` is what /api/chat returns."""

    def __init__(self, version="0.34.4", digest="sha256:aaaa1111", reply=None):
        self.version, self.digest = version, digest
        self.reply = reply or {
            "message": {"content": "The claim was approved."},
            "eval_count": 7,
            "prompt_eval_count": 40,
            "done_reason": "stop",
        }
        self.calls: list[dict] = []

    def get(self, url, timeout=30.0):
        if url.endswith("/api/version"):
            return {"version": self.version}
        if url.endswith("/api/tags"):
            return {"models": [{"name": "granite4.2:8b", "digest": self.digest}]}
        raise AssertionError(url)

    def post(self, url, payload, timeout=300.0):
        self.calls.append(payload)
        return self.reply


def _cfg(**kw):
    base = dict(
        model="granite4.2:8b",
        system="You are a claims assessor. Answer in one paragraph.",
        num_ctx=8192,
        temperature=0.2,
        top_p=0.9,
        top_k=40,
        seed=7,
    )
    base.update(kw)
    return OllamaConfig(**base)


# ------------------------------------------------------- refusals by design ---


def test_an_empty_system_message_is_refused():
    """An absent system message does not mean no system prompt -- it means the
    vendor template supplies one, and one in the pool interpolates the date."""
    with pytest.raises(ValueError, match="system message"):
        OllamaSystem(_cfg(system="   "), "A", FakeTransport())


def test_every_sampling_parameter_is_sent_explicitly():
    """Vendor defaults differ across the pool (temperature 1.0 vs 0.15), so
    comparing defaults compares configs rather than models."""
    t = FakeTransport()
    s = OllamaSystem(_cfg(), "A", t)
    s.invoke(Invocation("i0", "Was the claim approved?"))
    opts = t.calls[0]["options"]
    for key in ("num_ctx", "temperature", "top_p", "top_k", "num_predict", "seed"):
        assert key in opts, key
    assert t.calls[0]["think"] is False


def test_the_system_message_is_actually_sent():
    t = FakeTransport()
    s = OllamaSystem(_cfg(), "A", t)
    s.invoke(Invocation("i0", "q"))
    roles = [m["role"] for m in t.calls[0]["messages"]]
    assert roles == ["system", "user"]
    assert "claims assessor" in t.calls[0]["messages"][0]["content"]


# -------------------------------------------------------------------- pinning ---


def test_pin_captures_version_digest_and_request_shape():
    s = OllamaSystem(_cfg(), "A", FakeTransport())
    p = s.pin()
    assert p["server_version"] == "0.34.4"
    assert p["model_digest"] == "sha256:aaaa1111"
    assert "granite4.2:8b" in p["request_fingerprint"]


def test_a_missing_model_is_a_pin_failure_not_a_runtime_surprise():
    s = OllamaSystem(_cfg(model="nonexistent:8b"), "A", FakeTransport())
    with pytest.raises(PinMismatch, match="not present"):
        s.pin()


def test_a_server_version_change_mid_study_is_refused():
    """The observed incident: the client updated itself 0.32.5 -> 0.34.4
    unprompted. That is F4 provider drift injected by our own tooling."""
    t = FakeTransport(version="0.34.4")
    s = OllamaSystem(_cfg(), "A", t)
    s.verify_pin()          # first call pins
    t.version = "0.35.0"    # the stack moves underneath
    with pytest.raises(PinMismatch, match="server_version"):
        s.verify_pin()


def test_a_model_digest_change_is_refused():
    t = FakeTransport()
    s = OllamaSystem(_cfg(), "A", t)
    s.verify_pin()
    t.digest = "sha256:bbbb2222"
    with pytest.raises(PinMismatch, match="model_digest"):
        s.verify_pin()


def test_an_unchanged_stack_verifies_quietly():
    t = FakeTransport()
    s = OllamaSystem(_cfg(), "A", t)
    s.verify_pin()
    s.verify_pin()  # must not raise


# ------------------------------------------------------ detected, not fixed ---


def test_empty_content_with_tokens_spent_is_flagged():
    """Qwen3.5 defaults thinking on and can spend the whole budget reasoning,
    returning nothing. That signature is indistinguishable from the F12
    truncation the harness injects deliberately, unless it is named."""
    t = FakeTransport(reply={
        "message": {"content": "", "thinking": "let me think about this..."},
        "eval_count": 150,
        "done_reason": "length",
    })
    r = OllamaSystem(_cfg(), "A", t).invoke(Invocation("i0", "q"))
    assert r.output == ""
    assert r.trace.extra["empty_with_tokens"] is True
    assert r.trace.extra["thinking_chars"] > 0


def test_a_normal_short_answer_is_not_flagged():
    r = OllamaSystem(_cfg(), "A", FakeTransport()).invoke(Invocation("i0", "q"))
    assert "empty_with_tokens" not in r.trace.extra
    assert r.output == "The claim was approved."
    assert r.trace.finish_reason == "stop"


def test_tool_calls_land_in_the_trace():
    t = FakeTransport(reply={
        "message": {"content": "", "tool_calls": [
            {"function": {"name": "get_balance"}},
            {"function": {"name": "get_account"}},
        ]},
        "eval_count": 20,
    })
    r = OllamaSystem(_cfg(), "A", t).invoke(Invocation("i0", "q"))
    assert r.trace.tools_called == ("get_balance", "get_account")


def test_a_transport_failure_becomes_an_errored_sample_not_an_exception():
    """The recorder captures errored samples rather than aborting a multi-hour
    run, so the adapter must not raise on a transient server failure."""

    class Broken:
        def get(self, url, timeout=30.0):
            raise OSError("connection refused")

        def post(self, url, payload, timeout=300.0):
            raise OSError("connection refused")

    r = OllamaSystem(_cfg(), "A", Broken()).invoke(Invocation("i0", "q"))
    assert r.output == ""
    assert "connection refused" in r.trace.error


# ---------------------------------------------------------------------- arms ---


def test_baseline_and_decoy_share_one_configuration_exactly():
    """The decoy arm must be the same system, not a copy that could drift."""
    base, cand = _cfg(), _cfg(temperature=0.9)
    arms = build_arms(base, cand, FakeTransport)
    assert arms["A"].config is arms["A_prime"].config
    assert arms["B"].config is not base
    assert [arms[a].arm for a in ("A", "A_prime", "B")] == ["A", "A_prime", "B"]


def test_a_changed_sampling_parameter_changes_the_fingerprint():
    """Otherwise a study could change temperature and the pin would not notice."""
    assert _cfg().fingerprint() != _cfg(temperature=0.9).fingerprint()
    assert _cfg().fingerprint() != _cfg(num_ctx=4096).fingerprint()
    assert _cfg().fingerprint() != _cfg(system="different").fingerprint()
    assert _cfg().fingerprint() == _cfg().fingerprint()
