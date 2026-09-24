"""A synthetic system under test.

The point of a stub is not to imitate an LLM. It is to be a system whose *true*
behaviour we know exactly, so that the detector's output can be checked against
ground truth rather than against a plausible story.

Specifically it lets us answer the question the whole calibration rests on:
**when the machinery claims a false-discovery rate of q, is the realised rate
actually q?** No real system can answer that, because no real system tells you
which inputs genuinely changed.

Design: each input maps to a fixed set of candidate outputs with a probability
vector. That is deliberately multimodal — MTH-005 showed that summarising an
output cloud as a point with a radius is blind to exactly the mode-share shifts
that matter, so the stub has to be able to produce them.

Arms A and A_prime share one behaviour table: they are the same system, and any
difference between them is sampling noise by construction. Arm B carries a
perturbed table on a known subset of inputs — that subset is the ground truth
the detector is graded against, and it is not visible to anything downstream.
"""

from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass, field

from .adapter import Invocation, Response, Trace, check_arm


def _stable_hash(*parts: str) -> int:
    h = hashlib.sha256("|".join(parts).encode()).digest()
    return int.from_bytes(h[:8], "big")


@dataclass
class Behaviour:
    """What one input does: candidate outputs and their probabilities."""

    modes: tuple[str, ...]
    probs: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.modes) != len(self.probs):
            raise ValueError("modes and probs must be the same length")
        total = sum(self.probs)
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"probs must sum to 1, got {total}")


def default_table(input_ids: list[str], n_modes: int = 3) -> dict[str, Behaviour]:
    """A deterministic-per-input, stochastic-per-sample behaviour table.

    Mode shares vary across inputs so the corpus contains both near-deterministic
    inputs (where the floor is ~0) and genuinely spread ones. Both regimes have
    to work: MTH-003 established that a near-zero observed floor at small k is
    weak evidence of determinism, and the decoy arm is what handles it.
    """
    table: dict[str, Behaviour] = {}
    for iid in input_ids:
        rng = random.Random(_stable_hash("behaviour", iid))
        modes = tuple(f"{iid}::mode{j}" for j in range(n_modes))
        # Dirichlet-ish: occasionally near-deterministic, usually spread.
        weights = [rng.random() ** rng.choice([0.3, 1.0, 3.0]) for _ in range(n_modes)]
        total = sum(weights)
        table[iid] = Behaviour(modes, tuple(w / total for w in weights))
    return table


# --------------------------------------------------------------------------
# perturbations — what "B is different" can mean
# --------------------------------------------------------------------------


def shift_mode_share(b: Behaviour, strength: float, rng: random.Random) -> Behaviour:
    """Move probability mass between existing modes, changing nothing else.

    This is the change MTH-005 showed a centroid-and-spread summary cannot see.
    `strength` in [0, 1] is the fraction of mass moved to the currently-least
    likely mode.
    """
    probs = list(b.probs)
    lo = min(range(len(probs)), key=lambda i: probs[i])
    moved = 0.0
    for i in range(len(probs)):
        if i == lo:
            continue
        take = probs[i] * strength
        probs[i] -= take
        moved += take
    probs[lo] += moved
    return Behaviour(b.modes, tuple(probs))


def add_mode(b: Behaviour, strength: float, rng: random.Random) -> Behaviour:
    """Introduce an output the baseline never produced."""
    probs = [p * (1 - strength) for p in b.probs]
    return Behaviour(b.modes + ("__novel__",), tuple(probs) + (strength,))


def collapse(b: Behaviour, strength: float, rng: random.Random) -> Behaviour:
    """Concentrate mass on the modal output — a reliability change, not a
    content change. Centroid displacement for this is zero (MTH-005)."""
    probs = list(b.probs)
    hi = max(range(len(probs)), key=lambda i: probs[i])
    freed = 0.0
    for i in range(len(probs)):
        if i == hi:
            continue
        take = probs[i] * strength
        probs[i] -= take
        freed += take
    probs[hi] += freed
    return Behaviour(b.modes, tuple(probs))


PERTURBATIONS = {
    "mode_share": shift_mode_share,
    "add_mode": add_mode,
    "collapse": collapse,
}


@dataclass
class StubSystem:
    """One arm of a synthetic system.

    `sticky_principals` supports fault class F8a: when set, the perturbation
    applies only to invocations whose principal is in the set, so the fault
    concentrates per user rather than spreading uniformly across requests.
    """

    name: str
    arm: str
    table: dict[str, Behaviour]
    perturbed: dict[str, Behaviour] | None = None
    sticky_principals: frozenset[str] | None = None
    seed: int = 0
    latency_ms: float = 1.0
    _counter: dict = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        check_arm(self.arm)
        if (self.perturbed is None) != (self.sticky_principals is None):
            raise ValueError(
                "perturbed and sticky_principals must be set together: a sticky "
                "fault needs both the altered behaviour and who it applies to"
            )

    def invoke(self, inv: Invocation) -> Response:
        # A sticky fault behaves normally for everyone it does not touch. That
        # is the whole point of F8a: the request-level rate and the user-level
        # rate come apart because the same users keep landing on the bad path.
        table = self.table
        if self.sticky_principals is not None:
            if inv.principal is None:
                raise ValueError(
                    "this arm carries a sticky fault, so every invocation needs "
                    "a principal; otherwise the fault has nobody to stick to"
                )
            if inv.principal in self.sticky_principals:
                assert self.perturbed is not None
                table = self.perturbed
        b = table[inv.input_id]
        # A fresh draw per call. Seeded on the call count so a run is
        # reproducible, but successive samples of the same input genuinely
        # differ — which is the noise floor the decoy arm measures.
        n = self._counter.get(inv.input_id, 0)
        self._counter[inv.input_id] = n + 1
        rng = random.Random(_stable_hash(str(self.seed), self.arm, inv.input_id, str(n)))
        out = rng.choices(b.modes, weights=b.probs, k=1)[0]
        return Response(
            output=out,
            trace=Trace(latency_ms=self.latency_ms, model_id=f"{self.name}:{self.arm}"),
        )


def build_arms(
    input_ids: list[str],
    affected: set[str],
    perturbation: str = "mode_share",
    strength: float = 0.5,
    seed: int = 0,
    sticky_principals: frozenset[str] | None = None,
) -> tuple[StubSystem, StubSystem, StubSystem]:
    """Construct A, A_prime and B with a known ground-truth affected set.

    A and A_prime share a table object by value, not by reference, so a bug that
    mutated one would not silently fix itself in the other.
    """
    if perturbation not in PERTURBATIONS:
        raise ValueError(f"unknown perturbation {perturbation!r}")
    base = default_table(input_ids)
    fn = PERTURBATIONS[perturbation]
    rng = random.Random(seed)
    b_table = {
        iid: (fn(bh, strength, rng) if iid in affected else Behaviour(bh.modes, bh.probs))
        for iid, bh in base.items()
    }
    a = StubSystem("stub", "A", dict(base), seed=seed)
    a_prime = StubSystem("stub", "A_prime", dict(base), seed=seed + 1_000_003)
    if sticky_principals is None:
        # Uniform fault: B carries the perturbed behaviour for everyone.
        b = StubSystem("stub", "B", b_table, seed=seed + 2_000_003)
    else:
        # Sticky fault (F8a): B behaves like the baseline except for the
        # principals it sticks to.
        b = StubSystem(
            "stub",
            "B",
            dict(base),
            perturbed=b_table,
            sticky_principals=sticky_principals,
            seed=seed + 2_000_003,
        )
    return a, a_prime, b
