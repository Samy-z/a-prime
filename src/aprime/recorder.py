"""Three-arm replay.

Runs the baseline (A), the decoy (A_prime) and the candidate (B) over the same
inputs and records what came back.

The ordering is the part that matters. A_prime is not "a second run of A" — it
is a run of A collected under the same conditions as B, and the two constraints
that follow are not stylistic:

**Interleaved, never batched.** Temperature-0 decoding is not deterministic on
batched serving infrastructure: 1000 completions of one prompt at temperature 0
produced 80 unique outputs, and the divergence rate moves with server batch size
(MTH-015). A decoy arm collected at a quiet hour, or all in one burst before the
candidate runs, measures a different noise floor than the candidate experiences
and mis-calibrates every threshold downstream.

**Arm order rotates.** If A always went first it would systematically occupy the
cold-cache position. Rotating by sample index costs nothing and removes an
entire class of argument about the result.

Each sample carries a monotonic `order`, so that interleaving can be *checked*
after the fact rather than assumed. `tests/test_recorder.py` does check it.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

from .adapter import ARMS, Invocation, SystemUnderTest


@dataclass(frozen=True)
class Sample:
    input_id: str
    arm: str
    sample_idx: int
    order: int
    output: str
    latency_ms: float
    model_id: str | None = None
    finish_reason: str | None = None
    error: str | None = None


@dataclass
class Recording:
    samples: list[Sample]
    k: int
    input_ids: list[str]

    def cloud(self, input_id: str, arm: str) -> list[str]:
        """Every output this arm produced for this input."""
        return [
            s.output
            for s in self.samples
            if s.input_id == input_id and s.arm == arm and s.error is None
        ]

    def clouds(self, arm: str) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {iid: [] for iid in self.input_ids}
        for s in self.samples:
            if s.arm == arm and s.error is None:
                out[s.input_id].append(s.output)
        return out

    def interleaving_gap(self) -> int:
        """Largest run of consecutive calls that all hit the same arm.

        A batched collection produces a gap on the order of the corpus size; a
        properly interleaved one stays small. Reported rather than asserted here
        so a caller can decide what is acceptable for its own load regime.
        """
        worst = 0
        run = 0
        prev: str | None = None
        for s in sorted(self.samples, key=lambda x: x.order):
            run = run + 1 if s.arm == prev else 1
            prev = s.arm
            worst = max(worst, run)
        return worst

    def to_jsonl(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as fh:
            for s in sorted(self.samples, key=lambda x: x.order):
                fh.write(json.dumps(asdict(s)) + "\n")


def record(
    invocations: Sequence[Invocation],
    arms: dict[str, SystemUnderTest],
    k: int = 10,
) -> Recording:
    """Collect k samples per input per arm, interleaved across arms.

    `arms` maps arm name to system. All three of A, A_prime and B are required:
    the decoy arm is not optional, because without it there is no calibrated
    false-alarm rate and the thresholds are guesses (MTH-007).
    """
    missing = set(ARMS) - set(arms)
    if missing:
        raise ValueError(
            f"missing arms {sorted(missing)}. The decoy arm A_prime is mandatory; "
            "without it nothing downstream has a null to calibrate against."
        )
    for name, sys_ in arms.items():
        if sys_.arm != name:
            raise ValueError(f"arm {name!r} holds a system labelled {sys_.arm!r}")

    samples: list[Sample] = []
    order = 0
    for idx in range(k):
        for inv in invocations:
            # Rotate which arm leads, so no arm owns the cold position.
            rotated = ARMS[idx % len(ARMS) :] + ARMS[: idx % len(ARMS)]
            for arm in rotated:
                try:
                    resp = arms[arm].invoke(inv)
                    samples.append(
                        Sample(
                            input_id=inv.input_id,
                            arm=arm,
                            sample_idx=idx,
                            order=order,
                            output=resp.output,
                            latency_ms=resp.trace.latency_ms,
                            model_id=resp.trace.model_id,
                            finish_reason=resp.trace.finish_reason,
                            error=resp.trace.error,
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    samples.append(
                        Sample(
                            input_id=inv.input_id,
                            arm=arm,
                            sample_idx=idx,
                            order=order,
                            output="",
                            latency_ms=0.0,
                            error=f"{type(exc).__name__}: {exc}",
                        )
                    )
                order += 1
    return Recording(
        samples=samples,
        k=k,
        input_ids=[inv.input_id for inv in invocations],
    )


def iter_invocations(
    input_ids: Iterable[str],
    texts: dict[str, str] | None = None,
    principals: dict[str, str] | None = None,
) -> list[Invocation]:
    return [
        Invocation(
            input_id=iid,
            text=(texts or {}).get(iid, iid),
            principal=(principals or {}).get(iid),
        )
        for iid in input_ids
    ]
