"""An Ollama-backed system under test, with the pinning discipline built in.

D12 settled as *pin, do not migrate*: the problem observed was the client
updating itself mid-survey, which is F4 provider drift injected by our own
tooling. This adapter makes that detectable rather than invisible, and refuses
to run when the stack has moved underneath a pinned study.

## Three things this refuses to let you do

**Run without an explicit system message.** Omitting it does not mean "no system
prompt" — it means the vendor template supplies one. Ministral 3's Ollama
template injects roughly 540 tokens that interpolate `{{ currentDate }}`, so the
system prompt changes every midnight and an A arm on one date differs from a B
arm on the next by a prompt edit nobody made. That is F2 at global blast radius
with a 24-hour period (BCH-009). `system` is therefore required, not defaulted.

**Run on vendor sampling defaults.** They differ per model — temperature 1.0 for
one member of the pool, 0.15 for another. Comparing defaults compares sampling
configurations, not models. Every parameter is explicit.

**Run against an unpinned stack.** `pin()` captures the server version and the
model digest; `verify_pin()` refuses when either has moved. A study whose serving
stack changed halfway through has two baselines, and the decoy arm will absorb
the difference as ordinary noise rather than reporting it.

## One thing it detects rather than prevents

Qwen3.5 defaults `thinking` on and can spend an entire token budget reasoning,
returning empty content. That signature is indistinguishable from F12 output
truncation, which the harness injects deliberately — so an empty response with a
non-zero token count is flagged in the trace as `empty_with_tokens` rather than
silently passed through as a short answer.

Transport is injectable so the adapter can be tested without a live server.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from ..adapter import Invocation, Response, Trace, check_arm


class Transport(Protocol):
    def post(self, url: str, payload: dict, timeout: float) -> dict: ...
    def get(self, url: str, timeout: float) -> dict: ...


class HttpTransport:
    def post(self, url: str, payload: dict, timeout: float = 300.0) -> dict:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())

    def get(self, url: str, timeout: float = 30.0) -> dict:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode())


@dataclass(frozen=True)
class OllamaConfig:
    """Every field that affects output, stated rather than defaulted.

    `system` and the sampling parameters have no defaults on purpose. A default
    here would be a silent choice, and silent choices are what BCH-009 is about.
    """

    model: str
    system: str
    num_ctx: int
    temperature: float
    top_p: float
    top_k: int
    seed: int | None = None
    num_predict: int = 256
    think: bool = False
    host: str = "http://127.0.0.1:11434"

    def options(self) -> dict[str, Any]:
        opts = {
            "num_ctx": self.num_ctx,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "num_predict": self.num_predict,
        }
        if self.seed is not None:
            opts["seed"] = self.seed
        return opts

    def fingerprint(self) -> str:
        """Everything about the request that could change the output."""
        return json.dumps(
            {
                "model": self.model,
                "system": self.system,
                **self.options(),
                "think": self.think,
            },
            sort_keys=True,
        )


class PinMismatch(RuntimeError):
    """The serving stack moved under a pinned study."""


@dataclass
class OllamaSystem:
    config: OllamaConfig
    arm: str
    transport: Transport = field(default_factory=HttpTransport)
    pinned: dict | None = None
    name: str = ""

    def __post_init__(self) -> None:
        check_arm(self.arm)
        if not self.config.system.strip():
            raise ValueError(
                "system message must be non-empty. An absent system message does "
                "not mean 'no system prompt' -- it means the vendor template "
                "supplies one, and at least one template in the pool "
                "interpolates the current date (BCH-009)."
            )
        if not self.name:
            self.name = self.config.model

    # ---------------------------------------------------------------- pinning

    def pin(self) -> dict:
        """Capture what has to stay fixed for a study to be one study."""
        version = self.transport.get(f"{self.config.host}/api/version")
        tags = self.transport.get(f"{self.config.host}/api/tags")
        digest = None
        for m in tags.get("models", []):
            if m.get("name") == self.config.model:
                digest = m.get("digest")
                break
        if digest is None:
            raise PinMismatch(
                f"model {self.config.model!r} is not present on the server; "
                f"available: {[m.get('name') for m in tags.get('models', [])]}"
            )
        return {
            "server_version": version.get("version"),
            "model": self.config.model,
            "model_digest": digest,
            "request_fingerprint": self.config.fingerprint(),
        }

    def verify_pin(self) -> None:
        """Refuse to run when the stack has moved.

        This is the whole point of D12. A study whose serving stack changed
        halfway through has two baselines, and the decoy arm will absorb the
        difference as ordinary noise instead of reporting it.
        """
        if self.pinned is None:
            self.pinned = self.pin()
            return
        now = self.pin()
        drift = {
            k: (self.pinned.get(k), now.get(k))
            for k in ("server_version", "model_digest", "request_fingerprint")
            if self.pinned.get(k) != now.get(k)
        }
        if drift:
            raise PinMismatch(
                "serving stack moved under a pinned study: "
                + "; ".join(f"{k}: {a!r} -> {b!r}" for k, (a, b) in drift.items())
                + ". This is F4 provider drift injected by our own tooling; "
                "re-pin deliberately or restore the pinned version."
            )

    # ---------------------------------------------------------------- calling

    def invoke(self, inv: Invocation) -> Response:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": self.config.system},
                {"role": "user", "content": inv.text},
            ],
            "stream": False,
            "think": self.config.think,
            "options": self.config.options(),
        }
        import time

        t0 = time.perf_counter()
        try:
            body = self.transport.post(f"{self.config.host}/api/chat", payload, 300.0)
        except (urllib.error.URLError, OSError, ValueError) as exc:
            return Response(
                output="",
                trace=Trace(
                    latency_ms=(time.perf_counter() - t0) * 1000.0,
                    model_id=self.config.model,
                    error=f"{type(exc).__name__}: {exc}",
                ),
            )
        latency = (time.perf_counter() - t0) * 1000.0

        msg = body.get("message") or {}
        content = msg.get("content") or ""
        eval_count = body.get("eval_count") or 0
        extra: dict[str, Any] = {
            "eval_count": eval_count,
            "prompt_eval_count": body.get("prompt_eval_count"),
        }
        # The Qwen trap: tokens spent, nothing returned. Indistinguishable from
        # injected F12 truncation unless it is named here.
        if not content.strip() and eval_count > 0:
            extra["empty_with_tokens"] = True
        if msg.get("thinking"):
            extra["thinking_chars"] = len(msg["thinking"])

        return Response(
            output=content,
            trace=Trace(
                latency_ms=latency,
                tools_called=tuple(
                    c.get("function", {}).get("name", "")
                    for c in (msg.get("tool_calls") or [])
                ),
                finish_reason=body.get("done_reason"),
                model_id=self.config.model,
                extra=extra,
            ),
        )


def build_arms(
    baseline: OllamaConfig,
    candidate: OllamaConfig,
    transport_factory: Callable[[], Transport] = HttpTransport,
) -> dict[str, OllamaSystem]:
    """A, A_prime and B, where A and A_prime share one configuration exactly.

    The decoy arm must be the *same* system, so it takes the identical config
    object rather than a copy that could drift. Only B differs, and what differs
    is whatever the caller changed — that is the thing under test.
    """
    return {
        "A": OllamaSystem(baseline, "A", transport_factory()),
        "A_prime": OllamaSystem(baseline, "A_prime", transport_factory()),
        "B": OllamaSystem(candidate, "B", transport_factory()),
    }
