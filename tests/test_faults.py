"""Fault injection.

The property that matters most here is not that faults break things. It is that
the harness knows *which inputs a fault actually touched*. A fault labelled at
the cell level is wrong for every input it never bit, and that is label noise
in the direction that looks like success.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime.adapter import Invocation, Response, Trace  # noqa: E402
from aprime.conformance import check, induce  # noqa: E402
from aprime.detect import detect  # noqa: E402
from aprime.faults import AVAILABLE, FaultInjector, FaultSpec  # noqa: E402
from aprime.recorder import iter_invocations, record  # noqa: E402
from aprime.stub import build_arms  # noqa: E402


class Fixed:
    """A system that always returns the same thing, so a fault's effect is the
    only variable."""

    def __init__(self, text: str, arm: str = "B"):
        self.text, self.arm, self.name = text, arm, "fixed"

    def invoke(self, inv: Invocation) -> Response:
        return Response(output=self.text, trace=Trace(latency_ms=1.0))


def _wrap(text, name, severity=0.5, **kw):
    return FaultInjector(Fixed(text), FaultSpec("Fx", name, severity, **kw))


def _one(inj, iid="i0", principal=None):
    return inj.invoke(Invocation(iid, "q", principal=principal)).output


# ------------------------------------------------------------- activation ---


def test_a_fault_that_finds_nothing_to_bite_records_no_activation():
    """Truncation cannot truncate four words. That input is a true negative,
    not a missed detection, and the log has to say so."""
    inj = _wrap("too short here", "output_truncation", 0.5)
    assert _one(inj) == "too short here"
    assert inj.log.touched == set()
    assert inj.log.activation_rate() == 0.0


def test_schema_break_only_bites_json():
    prose = _wrap("The claim was approved.", "schema_break", 0.5)
    _one(prose)
    assert prose.log.touched == set()

    js = _wrap(json.dumps({"a": 1, "b": 2}), "schema_break", 0.5)
    out = _one(js)
    assert js.log.touched == {"i0"}
    assert "a" not in json.loads(out)


def test_activation_rate_is_computed_over_the_corpus_not_the_hits():
    inj = _wrap("one. two. three. four.", "omission", 0.25)
    for i in range(4):
        _one(inj, f"i{i}")
    short = _wrap("x", "omission", 0.25)
    for i in range(4):
        _one(short, f"j{i}")
    assert inj.log.activation_rate() == 1.0
    assert short.log.activation_rate() == 0.0


# ----------------------------------------------------------- blast regimes ---


def test_b0_touches_every_request():
    inj = _wrap("one. two. three.", "omission", 0.34, regime="B0")
    for i in range(20):
        _one(inj, f"i{i}")
    assert len(inj.log.touched) == 20


def test_b2_touches_a_uniform_share_of_requests():
    inj = _wrap("one. two. three.", "omission", 0.34, regime="B2", share=0.25, seed=3)
    for i in range(400):
        _one(inj, f"i{i}")
    rate = len(inj.log.touched) / 400
    assert 0.18 < rate < 0.33, rate


def test_b3_is_sticky_per_principal_so_user_rate_exceeds_request_rate():
    """The Anthropic case: 0.8-16% of requests but ~30% of users."""
    inj = _wrap("one. two. three.", "omission", 0.34, regime="B3", share=0.25, seed=5)
    principals = [f"u{i % 20}" for i in range(400)]
    for i, pr in enumerate(principals):
        _one(inj, f"i{i}", principal=pr)
    hit_users = {
        principals[int(iid[1:])] for iid in inj.log.touched
    }
    # Every request from an affected user is affected, and no request from an
    # unaffected one is -- that is what "sticky" means.
    for i, pr in enumerate(principals):
        expected = pr in hit_users
        assert ((f"i{i}" in inj.log.touched) == expected), (i, pr)


def test_b3_without_a_principal_is_an_error_not_a_silent_fallback():
    inj = _wrap("one. two.", "omission", 0.5, regime="B3", share=0.5)
    with pytest.raises(ValueError, match="principal"):
        _one(inj)


# ---------------------------------------------------------- the injections ---


def test_every_registered_injection_is_reachable():
    assert set(AVAILABLE) >= {
        "omission", "output_truncation", "script_corruption",
        "unicode_escape", "refusal", "schema_break", "verbosity",
    }


def test_truncation_sets_finish_reason_so_it_is_trace_visible():
    inj = _wrap("one two three four five six seven eight nine ten", "output_truncation", 0.5)
    r = inj.invoke(Invocation("i0", "q"))
    assert r.trace.finish_reason == "length"
    assert r.trace.extra["injected"].startswith("Fx:output_truncation")


def test_omission_removes_content_and_keeps_the_rest():
    inj = _wrap("Alpha happened. Beta happened. Gamma is conditional.", "omission", 0.34)
    out = _one(inj)
    assert "Alpha happened." in out
    assert "Gamma is conditional." not in out


def test_severity_is_monotone_for_truncation():
    text = " ".join(f"w{i}" for i in range(40))
    lens = [len(_one(_wrap(text, "output_truncation", s)).split()) for s in (0.2, 0.5, 0.8)]
    assert lens == sorted(lens, reverse=True), lens


# ------------------------------------------------- caught by the detector ---


def test_an_injected_script_corruption_is_caught_by_conformance():
    clean = ["The request was approved on time."] * 20
    contract = induce(clean, list(clean))
    inj = _wrap("The request was approved on time.", "script_corruption", 0.2)
    dirty = [_one(inj, f"i{i}") for i in range(20)]
    assert any(v.rule.kind == "script_subset" for v in check(contract, dirty))


def test_an_injected_fault_shows_up_end_to_end():
    """Wrap only the B arm, leaving A and the decoy untouched -- which is why
    the injector wraps a system rather than reconfiguring it."""
    ids = [f"i{n}" for n in range(40)]
    a, ap, b = build_arms(ids, set())
    spec = FaultSpec("F13", "refusal", 1.0, regime="B2", share=0.3, seed=11)
    b_broken = FaultInjector(b, spec)
    rec = record(iter_invocations(ids), {"A": a, "A_prime": ap, "B": b_broken}, k=8)

    rep = detect(rec, q=0.10)
    touched = b_broken.log.touched
    assert touched, "the fault never fired"
    flagged = {f.input_id for f in rep.findings}
    # Graded against activation, never the cell label.
    assert len(flagged & touched) / len(touched) > 0.5, rep.text()
    assert not (flagged - touched), "flagged an input the fault never touched"
