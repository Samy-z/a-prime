"""Fault injection.

Breaks a working system in known ways so the detector can be scored against
ground truth. Every fault here corresponds to a class in the frozen taxonomy
(`docs/knowledge/fault-taxonomy.md`); nothing is invented, because the
taxonomy's whole validity argument is that it is drawn from documented reality.

## Per-input activation is mandatory, not optional bookkeeping

A fault labelled at the cell level is **wrong for every input it never
touched**. Truncation only bites long outputs; a schema break only bites JSON;
a refusal only bites where the system would otherwise have answered. Labelling
all of a cell's inputs positive is label noise by construction, and it is the
kind that inflates every downstream number in a direction that looks like
success.

So every injection records whether it actually fired, per input, per sample.
`ActivationLog` is the ground truth the detector is graded against — never the
cell label.

## Blast radius is an axis, not an attribute (BCH-001)

The documented split is request-path versus shared-artifact, not real versus
injected. A prompt edit is global by construction because there is one copy of
the prompt; a routing fault runs at 0.0004% to 16%. Injecting everything
globally would teach a classifier that "global implies injected" — a harness
artifact with no counterpart in the wild.

| Regime | Who is affected |
|---|---|
| `B0` | everyone — shared artifact |
| `B1` | one platform surface, others untouched |
| `B2` | a uniform random share of requests |
| `B3` | a sticky share of *principals*, so the user-level rate exceeds the request-level rate by roughly 20x |

## Severity floors come from published evidence, not from us (BCH-004)

Retrieval corruption at 10% produced *identical* metrics to 0% on n=500. If the
harness injects that and the detector misses it, **that is not a detector
failure** and must not be scored as one. Real production prompt edits are one to
three lines; a harness that rewrites whole prompts is injecting something that
does not occur in the wild.
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import dataclass, field
from typing import Callable, Literal, Sequence

from .adapter import Invocation, Response, SystemUnderTest, Trace

Regime = Literal["B0", "B1", "B2", "B3"]

_SENT = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class FaultSpec:
    """One fault at one severity in one blast regime."""

    fault_class: str          # F3, F7, ... as in the frozen taxonomy
    name: str
    severity: float           # 0..1, meaning is per-fault; see the ladders
    regime: Regime = "B0"
    share: float = 1.0        # for B2/B3: fraction of requests / principals
    seed: int = 0

    @property
    def cell_id(self) -> str:
        return f"{self.fault_class}:{self.name}@{self.severity:g}/{self.regime}"


# --------------------------------------------------------------------------
# the injections themselves
# --------------------------------------------------------------------------
#
# Each returns (new_output, activated). `activated` is False when the fault had
# nothing to bite on — that input is a true negative, not a missed detection.

Injection = Callable[[str, FaultSpec, random.Random], tuple[str, bool]]

_INJECTIONS: dict[str, Injection] = {}


def _injection(name: str):
    def deco(fn: Injection) -> Injection:
        _INJECTIONS[name] = fn
        return fn

    return deco


@_injection("omission")
def _omission(out: str, spec: FaultSpec, rng: random.Random) -> tuple[str, bool]:
    """Drop a trailing sentence. F5/F3 shaped; the class the semantic channels
    struggle with most."""
    parts = [p for p in _SENT.split(out.strip()) if p]
    if len(parts) < 2:
        return out, False
    n_drop = max(1, int(round(len(parts) * spec.severity)))
    n_drop = min(n_drop, len(parts) - 1)
    return " ".join(parts[:-n_drop]), True


@_injection("output_truncation")
def _truncation(out: str, spec: FaultSpec, rng: random.Random) -> tuple[str, bool]:
    """F12. Cut mid-sentence, which is the documented signature. Only bites
    outputs long enough to cut."""
    words = out.split()
    if len(words) < 8:
        return out, False
    keep = max(4, int(len(words) * (1.0 - spec.severity)))
    if keep >= len(words):
        return out, False
    return " ".join(words[:keep]), True


@_injection("script_corruption")
def _script(out: str, spec: FaultSpec, rng: random.Random) -> tuple[str, bool]:
    """F7. Three unrelated real causes converge on this one signature:
    wrong-script characters appearing mid-output."""
    if not out.strip():
        return out, False
    glyphs = "สวัสดี"
    words = out.split()
    n = max(1, int(round(len(words) * spec.severity)))
    for _ in range(n):
        words.insert(rng.randrange(len(words) + 1), glyphs)
    return " ".join(words), True


@_injection("unicode_escape")
def _escape(out: str, spec: FaultSpec, rng: random.Random) -> tuple[str, bool]:
    """F7, the quantization variant: raw escapes instead of decoded glyphs."""
    if not out.strip():
        return out, False
    return out + " \\uC548\\uB155", True


@_injection("refusal")
def _refusal(out: str, spec: FaultSpec, rng: random.Random) -> tuple[str, bool]:
    """F13. Replaces the answer entirely — a refusal is not a partial answer."""
    if not out.strip():
        return out, False
    return "I'm sorry, but I can't help with that request.", True


@_injection("schema_break")
def _schema(out: str, spec: FaultSpec, rng: random.Random) -> tuple[str, bool]:
    """F3. Only bites JSON, which is exactly why activation is recorded."""
    s = out.strip()
    try:
        obj = json.loads(s)
    except (ValueError, TypeError):
        return out, False
    if not isinstance(obj, dict) or not obj:
        return out, False
    if spec.severity >= 0.75:
        return s.rstrip("}") + ",}", True        # unparseable
    key = sorted(obj)[0]
    obj.pop(key)
    return json.dumps(obj), True                  # key silently dropped


@_injection("verbosity")
def _verbosity(out: str, spec: FaultSpec, rng: random.Random) -> tuple[str, bool]:
    """F9-shaped: stance added, no fact changed. Reported as REGISTER in the
    probe suite; here it is a fault the detector may or may not be expected to
    flag, which is itself the question."""
    if not out.strip():
        return out, False
    return "Based on the information available at the time of review, " + out, True


AVAILABLE = tuple(sorted(_INJECTIONS))


# --------------------------------------------------------------------------
# activation record
# --------------------------------------------------------------------------


@dataclass
class ActivationLog:
    """Which inputs a fault actually touched.

    This, never the cell label, is the ground truth the detector is graded
    against. `touched` holds input ids where the fault fired at least once.
    """

    spec: FaultSpec
    fired: dict[tuple[str, int], bool] = field(default_factory=dict)

    def record(self, input_id: str, sample_idx: int, activated: bool) -> None:
        self.fired[(input_id, sample_idx)] = activated

    @property
    def touched(self) -> set[str]:
        return {iid for (iid, _), hit in self.fired.items() if hit}

    def activation_rate(self, input_ids: Sequence[str] | None = None) -> float:
        ids = set(input_ids) if input_ids is not None else {i for i, _ in self.fired}
        if not ids:
            return 0.0
        return len(self.touched & ids) / len(ids)

    def summary(self, input_ids: Sequence[str] | None = None) -> str:
        return (
            f"{self.spec.cell_id}: fired on {len(self.touched)} inputs "
            f"({self.activation_rate(input_ids):.1%} of corpus)"
        )


# --------------------------------------------------------------------------
# the injector
# --------------------------------------------------------------------------


def _in_blast(spec: FaultSpec, inv: Invocation) -> bool:
    """Does this fault apply to this request at all, before activation?"""
    if spec.regime == "B0":
        return True
    if spec.regime == "B1":
        # Platform-localized: modelled as applying to this arm's deployment,
        # which the caller expresses by simply not wrapping the other platform.
        return True
    key = inv.input_id if spec.regime == "B2" else (inv.principal or inv.input_id)
    if spec.regime == "B3" and inv.principal is None:
        raise ValueError(
            "regime B3 is sticky per principal, so every invocation needs one. "
            "Without it the request-level and user-level rates cannot come "
            "apart, which is the only reason B3 exists."
        )
    h = hashlib.sha256(f"{spec.seed}|{spec.cell_id}|{key}".encode()).digest()
    return (int.from_bytes(h[:4], "big") / 0xFFFFFFFF) < spec.share


@dataclass
class FaultInjector:
    """Wraps a system and breaks its outputs in one known way.

    The wrapped system is unchanged; only what comes back is altered. That keeps
    the fault out of the system under test's own configuration, so the same
    baseline object can serve the A and A_prime arms while B is wrapped.
    """

    inner: SystemUnderTest
    spec: FaultSpec
    log: ActivationLog = field(init=False)
    _counter: dict = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.spec.name not in _INJECTIONS:
            raise ValueError(
                f"unknown injection {self.spec.name!r}; available: {AVAILABLE}"
            )
        self.log = ActivationLog(self.spec)

    @property
    def name(self) -> str:
        return f"{self.inner.name}+{self.spec.cell_id}"

    @property
    def arm(self) -> str:
        return self.inner.arm

    def invoke(self, inv: Invocation) -> Response:
        resp = self.inner.invoke(inv)
        idx = self._counter.get(inv.input_id, 0)
        self._counter[inv.input_id] = idx + 1

        if not _in_blast(self.spec, inv):
            self.log.record(inv.input_id, idx, False)
            return resp

        rng = random.Random(
            hashlib.sha256(
                f"{self.spec.seed}|{inv.input_id}|{idx}".encode()
            ).digest()[:8]
        )
        new_out, activated = _INJECTIONS[self.spec.name](resp.output, self.spec, rng)
        self.log.record(inv.input_id, idx, activated)
        if not activated:
            return resp
        return Response(
            output=new_out,
            trace=Trace(
                latency_ms=resp.trace.latency_ms,
                tools_called=resp.trace.tools_called,
                steps=resp.trace.steps,
                finish_reason=(
                    "length" if self.spec.name == "output_truncation"
                    else resp.trace.finish_reason
                ),
                model_id=resp.trace.model_id,
                error=resp.trace.error,
                extra={**resp.trace.extra, "injected": self.spec.cell_id},
            ),
        )
