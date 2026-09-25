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
after the fact rather than assumed.

## Resumption

Study runs are free in money and expensive in wall-clock, and they occupy the
owner's only machine. A multi-hour run that cannot be paused is not a long job,
it is a lockout — so recording checkpoints as it goes and restarts where it
stopped.

**The checkpoint unit is the triple, not the call.** All three arms for one
(input, sample index) are written together or not at all, and a partial triple
found on resume is discarded and redone. That is what preserves the property
MTH-015 exists for: A, A_prime and B for a given sample must be collected under
the same conditions, and a resume that restarted mid-triple would split them
across two load regimes.

A resumed run still has a seam *between* triples, recorded per sample as
`session` so the seam is visible in the data rather than invisible in the method.

## Grouping: by input, not by sample index

All k*3 calls for one input share a prompt prefix, so a server with prompt
caching pays prefill once per input instead of once per call. Measured on this
hardware that is the difference between roughly twenty days of prefill and a few
hours — larger than any other scheduling choice available.

Grouping does not weaken the interleaving guarantee, because the guarantee is
about the *triple*: A, A_prime and B for one sample must share conditions, and
grouping puts them closer together in time, not further apart.

What it does change is the timescale the noise floor spans. Grouped, an input's
k samples are drawn from one short window rather than across the whole run, so
the floor measures short-timescale variability. That is acceptable precisely
because B for that input sits in the same window — the comparison stays
apples-to-apples — but it means the floor no longer captures drift across the
run. Every sample therefore carries a wall-clock `ts`, so drift between the
first and last inputs of a long run can be checked after the fact instead of
assumed away.
"""

from __future__ import annotations

import json
import time
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
    ts: float = 0.0
    model_id: str | None = None
    finish_reason: str | None = None
    error: str | None = None
    session: int = 0

    @property
    def triple(self) -> tuple[str, int]:
        return (self.input_id, self.sample_idx)


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

    def wallclock_span_s(self) -> float:
        """Seconds between the first and last recorded sample.

        Grouping by input means an input's noise floor spans a short window
        while the run spans a long one. This is the number that says how far
        apart those two timescales are, and therefore how much room there is for
        drift the floor cannot see.
        """
        ts = [s.ts for s in self.samples if s.ts]
        return (max(ts) - min(ts)) if len(ts) > 1 else 0.0

    def spans_utc_date_boundary(self) -> bool:
        """Did this recording cross midnight UTC?

        Not a stylistic concern. At least one widely used chat template
        interpolates the current date into a hidden system prompt, so a run that
        straddles midnight has a system prompt that changed under it — a prompt
        regression (F2) at global blast radius that nobody made and nothing
        logged. If the arms fall on opposite sides, the decoy absorbs it as
        baseline noise and quietly destroys power.
        """
        ts = [s.ts for s in self.samples if s.ts]
        if len(ts) < 2:
            return False
        day = 86400
        return int(min(ts) // day) != int(max(ts) // day)

    @property
    def sessions(self) -> int:
        return len({s.session for s in self.samples})

    def to_jsonl(self, path: str | Path) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", encoding="utf-8") as fh:
            for s in sorted(self.samples, key=lambda x: x.order):
                fh.write(json.dumps(asdict(s)) + "\n")


def load_checkpoint(path: str | Path) -> tuple[list[Sample], set[tuple[str, int]], int]:
    """Read a checkpoint, keeping only complete triples.

    Returns usable samples, the set of finished (input_id, sample_idx) triples,
    and the next session number. A triple missing any arm is dropped entirely
    and will be redone, because a partial triple is exactly the split-load-regime
    case MTH-015 forbids.
    """
    p = Path(path)
    if not p.exists():
        return [], set(), 0
    rows: list[Sample] = []
    with p.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(Sample(**json.loads(line)))
            except (ValueError, TypeError):
                # A truncated final line is expected after a hard kill.
                continue
    seen: dict[tuple[str, int], set[str]] = {}
    for s in rows:
        seen.setdefault(s.triple, set()).add(s.arm)
    complete = {t for t, got in seen.items() if set(ARMS) <= got}
    kept = [s for s in rows if s.triple in complete]
    next_session = max((s.session for s in kept), default=-1) + 1
    return kept, complete, next_session


def record(
    invocations: Sequence[Invocation],
    arms: dict[str, SystemUnderTest],
    k: int = 10,
    checkpoint: str | Path | None = None,
    progress_every: int = 0,
    group_by_input: bool = True,
) -> Recording:
    """Collect k samples per input per arm, interleaved across arms.

    `arms` maps arm name to system. All three of A, A_prime and B are required:
    the decoy arm is not optional, because without it there is no calibrated
    false-alarm rate and the thresholds are guesses (MTH-007).

    With `checkpoint`, each completed triple is appended to that file and a
    rerun skips what is already there. Safe to kill at any point.

    `group_by_input` (default true) runs all k samples of one input before
    moving on, so a prompt-caching server pays prefill once per input rather
    than once per call. Set it false to spread each input's samples across the
    whole run, which makes the noise floor span the run's full conditions at
    large cost in prefill. See the module docstring.
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

    samples, done, session = [], set(), 0
    if checkpoint is not None:
        samples, done, session = load_checkpoint(checkpoint)
        if done:
            print(
                f"resuming: {len(done)} complete triples already recorded "
                f"(starting session {session})"
            )

    fh = None
    if checkpoint is not None:
        cp = Path(checkpoint)
        cp.parent.mkdir(parents=True, exist_ok=True)
        fh = cp.open("a", encoding="utf-8")

    order = max((s.order for s in samples), default=-1) + 1
    n_new = 0
    # Grouped: every sample of one input, then the next input. Ungrouped: one
    # sample of every input, then the next sample index.
    if group_by_input:
        schedule = [(inv, idx) for inv in invocations for idx in range(k)]
    else:
        schedule = [(inv, idx) for idx in range(k) for inv in invocations]
    try:
        for inv, idx in schedule:
            # Rotate which arm leads, so no arm owns the cold position.
            rotated = ARMS[idx % len(ARMS) :] + ARMS[: idx % len(ARMS)]
            if (inv.input_id, idx) in done:
                continue
            triple: list[Sample] = []
            for arm in rotated:
                try:
                    resp = arms[arm].invoke(inv)
                    triple.append(
                        Sample(
                            input_id=inv.input_id,
                            arm=arm,
                            sample_idx=idx,
                            order=order,
                            output=resp.output,
                            latency_ms=resp.trace.latency_ms,
                            ts=time.time(),
                            model_id=resp.trace.model_id,
                            finish_reason=resp.trace.finish_reason,
                            error=resp.trace.error,
                            session=session,
                        )
                    )
                except Exception as exc:  # noqa: BLE001
                    triple.append(
                        Sample(
                            input_id=inv.input_id,
                            arm=arm,
                            sample_idx=idx,
                            order=order,
                            output="",
                            latency_ms=0.0,
                            ts=time.time(),
                            error=f"{type(exc).__name__}: {exc}",
                            session=session,
                        )
                    )
                order += 1
            # All three arms or none. A kill between arms leaves a partial
            # set that load_checkpoint discards, so the triple is redone.
            samples.extend(triple)
            if fh is not None:
                for s in triple:
                    fh.write(json.dumps(asdict(s)) + "\n")
                fh.flush()
            n_new += 1
            if progress_every and n_new % progress_every == 0:
                print(f"  {n_new} triples this session, {len(samples)} samples total")
    finally:
        if fh is not None:
            fh.close()

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
