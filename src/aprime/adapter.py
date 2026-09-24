"""The system-under-test boundary.

Everything a-prime knows about a system it is measuring passes through here:
an input goes in, an output and a trace come out. No logprobs, no internals,
no access to the system's knowledge. That restriction is the product claim, not
a limitation to be worked around — a detector built against information it will
not have for a real customer's system is not the detector we are testing.

**Resist widening this interface.** Every request to add a field is a request to
make the detector depend on something a stranger's system may not expose. When
the pressure comes, record it in `docs/engine/LEDGER.md` rather than acting on
it, so the accumulated pressure is visible instead of each concession looking
individually reasonable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Invocation:
    """One request to a system under test.

    `session_id` and `principal` exist because of fault class F8. Sticky
    routing concentrates a request-level fault onto a subset of *users* — the
    Anthropic routing error ran at 0.8-16% of requests but touched ~30% of
    users — and an identity-aware system produces per-user clustering with no
    fault present at all. A detector that cannot see which requests belong
    together cannot tell those apart, and MTH-009's cluster-splitting is never
    validated against the case it exists for.

    Both are optional: plenty of systems are genuinely identity-blind, and the
    control arm for F8b is an identity-aware system with no fault injected.
    """

    input_id: str
    text: str
    session_id: str | None = None
    principal: str | None = None


@dataclass(frozen=True)
class Trace:
    """What the system did, as far as an outside observer can tell.

    Every field here is observable from the caller's side of a normal API. If a
    field can only be filled by instrumenting the system's internals, it does
    not belong in a Trace — it belongs in the harness's own fault-activation
    record, which is a separate thing and is not visible to the detector.
    """

    latency_ms: float
    tools_called: tuple[str, ...] = ()
    steps: int = 1
    finish_reason: str | None = None
    model_id: str | None = None
    error: str | None = None
    extra: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Response:
    output: str
    trace: Trace


@runtime_checkable
class SystemUnderTest(Protocol):
    """A system a-prime can measure.

    One instance represents one *arm*: the baseline and the candidate are two
    instances, not one instance with a flag, so that nothing in the detector can
    accidentally condition on which arm it is looking at.
    """

    name: str
    arm: str  # "A", "A_prime", or "B"

    def invoke(self, inv: Invocation) -> Response: ...


ARMS = ("A", "A_prime", "B")


def check_arm(arm: str) -> str:
    if arm not in ARMS:
        raise ValueError(f"arm must be one of {ARMS}, got {arm!r}")
    return arm
