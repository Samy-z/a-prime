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
from typing import Callable, Iterable, Sequence

import warnings

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


def load_checkpoint(
    path: str | Path,
    retry_dead_triples: bool = True,
) -> tuple[list[Sample], set[tuple[str, int]], int]:
    """Read a checkpoint, keeping only complete triples.

    Returns usable samples, the set of finished (input_id, sample_idx) triples,
    and the next session number. A triple missing any arm is dropped entirely
    and will be redone, because a partial triple is exactly the split-load-regime
    case MTH-015 forbids.

    **A triple where every arm errored is not finished either.** It holds three
    error strings and no outputs, so counting it as done means a resume skips it
    forever and the recording stays permanently short. This is not hypothetical:
    a server that stopped listening 90 seconds into a run produced 698
    consecutive connection failures, every one written as a complete triple, and
    the checkpoint then reported itself 100% recorded (ENG-008). With
    `retry_dead_triples` those are left out of `done`, so rerunning collects them
    properly. Pass false to inspect a checkpoint exactly as written.
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
    # The file is append-only, so one (triple, arm) can appear more than once:
    # a triple that failed and was later redone has both attempts on disk. The
    # last write is the live one. Without this, a retried triple is judged on the
    # errors it used to have and stays dead forever, which makes the whole
    # recovery path a no-op.
    latest: dict[tuple[tuple[str, int], str], Sample] = {}
    for s in rows:
        latest[(s.triple, s.arm)] = s
    live = list(latest.values())

    seen: dict[tuple[str, int], set[str]] = {}
    for s in live:
        seen.setdefault(s.triple, set()).add(s.arm)
    complete = {t for t, got in seen.items() if set(ARMS) <= got}
    if retry_dead_triples:
        errored: dict[tuple[str, int], int] = {}
        for s in live:
            if s.triple in complete and s.error:
                errored[s.triple] = errored.get(s.triple, 0) + 1
        complete -= {t for t, n in errored.items() if n >= len(ARMS)}
    kept = [s for s in live if s.triple in complete]
    kept.sort(key=lambda x: x.order)
    next_session = max((s.session for s in kept), default=-1) + 1
    return kept, complete, next_session


def checkpoint_health(path: str | Path) -> dict:
    """What is actually in a checkpoint, errors included.

    `load_checkpoint` hides dead triples so that a resume redoes them, which is
    right for recording and wrong for judging a file. A run whose system under
    test died looks identical to a finished one from the outside, and this is
    what tells them apart.
    """
    p = Path(path)
    if not p.exists():
        return {"exists": False, "samples": 0, "errored": 0, "empty": 0,
                "triples": 0, "dead_triples": 0, "error_rate": 0.0,
                "messages": []}
    rows, _, _ = load_checkpoint(p, retry_dead_triples=False)
    by_triple: dict[tuple[str, int], list[Sample]] = {}
    for s in rows:
        by_triple.setdefault(s.triple, []).append(s)
    dead = sum(1 for g in by_triple.values() if all(x.error for x in g))
    errored = sum(1 for s in rows if s.error)
    return {"exists": True, "samples": len(rows), "errored": errored,
            "empty": sum(1 for s in rows if not s.output.strip()),
            "triples": len(by_triple), "dead_triples": dead,
            "error_rate": errored / max(1, len(rows)),
            "messages": sorted({str(s.error)[:80] for s in rows if s.error})[:5]}


# ---------------------------------------------------------------------------
# decoy independence
# ---------------------------------------------------------------------------

# Where a system keeps its sampling seed, if it exposes one at all. Checked by
# duck typing on purpose: the adapter Protocol does not carry sampling
# configuration and must not start to, because a detector that needs to see a
# stranger's sampling options is not the detector we are selling. So this is a
# best-effort courtesy for systems built in this repo, silent for anything else,
# and never a guarantee. The pressure this puts on the boundary is recorded in
# docs/engine/LEDGER.md rather than resolved by widening it.
_SEED_PATHS = (("seed",), ("chat", "seed"), ("sampling", "seed"))


def _visible_seed(system: object) -> object | None:
    for path in _SEED_PATHS:
        cur: object | None = system
        for step in path:
            cur = getattr(cur, step, None) if not isinstance(cur, dict)                 else cur.get(step)
            if cur is None:
                break
        if cur is not None:
            return cur
    return None


def decoy_independence_warnings(arms: dict[str, SystemUnderTest]) -> list[str]:
    """Reasons to doubt that A_prime can act as a null, where they are visible.

    A_prime is the second baseline run and it IS the null distribution that
    target-decoy FDR calibrates against. If both baseline arms are configured
    with the same pinned seed they land on the same handful of outputs: eight
    repeats of one request under a pinned seed produced 2 distinct outputs,
    against 8 with the seed unset (MTH-023). A null supported on two points
    calibrates a tail quantile no better than one supported on a single point,
    and nothing about that failure is loud. Every arm records cleanly and the
    FDR column fills with confident meaningless numbers.

    The rule is to mirror the deployment being audited rather than to force a
    difference. A deployment that really does pin its seed really does have
    near-zero self-variance, and for that one an exact diff answers the question
    and this tool is the wrong instrument.
    """
    out: list[str] = []
    a, ap = _visible_seed(arms.get("A")), _visible_seed(arms.get("A_prime"))
    if a is not None and ap is not None and a == ap:
        out.append(
            f"A and A_prime are both configured with seed {a!r}. The decoy arm "
            f"is the null distribution, and two arms sharing a pinned seed "
            f"collapse onto the same few outputs, so the false-alarm rate will "
            f"be estimated from a null of almost no width and every q will be "
            f"confidently wrong. Leave the seed unset on both if the deployment "
            f"leaves it unset, which is the ordinary case. If the deployment "
            f"really does pin its seed, its self-variance is genuinely near "
            f"zero and an exact diff answers the question better than this "
            f"tool does. See MTH-023."
        )
    return out


# ---------------------------------------------------------------------------
# pausing and resuming
# ---------------------------------------------------------------------------


class RecordingFailed(Exception):
    """Every arm has been failing long enough that the run is pointless.

    Raised rather than pressed on with. A recorder that keeps going while nothing
    answers will fill a checkpoint with error strings, report steady progress the
    whole time, and leave an artifact that looks like a finished run: 698
    consecutive connection failures over 24 minutes, and a checkpoint calling
    itself 100% complete (ENG-008). Wall clock is the cheapest thing lost there.

    Whatever is already on disk stays, and the dead triples are redone next
    attempt because `load_checkpoint` does not count them as finished.
    """

    def __init__(self, consecutive: int, completed: int, last_error: str):
        self.consecutive = consecutive
        self.completed = completed
        self.last_error = last_error
        super().__init__(
            f"every arm failed on {consecutive} triples in a row, after "
            f"{completed} that did not. Last error: {last_error}. Nothing is "
            f"being recorded that any analysis could use, so the run stopped "
            f"rather than filling the checkpoint with errors. Check the system "
            f"under test is up, then rerun: the failed triples are not counted "
            f"as done.")


class RunPaused(Exception):
    """A recording stopped at a triple boundary before finishing.

    **Raised rather than returned**, so that a paused run cannot be analysed by
    accident. A partial recording has short clouds for the inputs it reached and
    none at all for the rest, and a detector run over it produces numbers that
    look entirely ordinary and mean nothing: thresholds fitted to fewer decoys,
    mode shares over two samples instead of ten. There is no way to see that in
    the report, so the only safe place to stop it is here.

    Everything collected is already on disk. Rerun with the same configuration
    and it resumes.
    """

    def __init__(self, completed: int, remaining: int, checkpoint: Path | None):
        self.completed = completed
        self.remaining = remaining
        self.checkpoint = checkpoint
        where = f" Checkpoint: {checkpoint}" if checkpoint else (
            " NOTHING WAS SAVED: this run had no checkpoint, so the work is "
            "lost. Pass `checkpoint` to make a run resumable.")
        super().__init__(
            f"recording paused after {completed} triples with {remaining} "
            f"still to do.{where}")


def stop_requested(path: str | Path) -> Callable[[], bool]:
    """A stop signal that is a file appearing on disk.

    A file rather than a signal handler, because the point is to stop a run from
    outside the process that started it: a long recording is left running
    overnight and the person who wants it to stop is at a different terminal, or
    is asking an agent to do it. Checked at triple boundaries only, so a stop
    never lands mid-triple and never costs more than one triple of work.
    """
    p = Path(path)

    def check() -> bool:
        return p.exists()

    return check


def recording_progress(
    checkpoint: str | Path,
    invocations: Sequence[Invocation],
    k: int,
) -> dict:
    """How much of a planned recording is already on disk.

    Reads the checkpoint without touching a model, so progress can be reported
    while a run is stopped, or checked before deciding to start one.
    """
    want = {(inv.input_id, idx) for inv in invocations for idx in range(k)}
    if not Path(checkpoint).exists():
        return {"planned": len(want), "done": 0, "remaining": len(want),
                "fraction": 0.0, "sessions": 0}
    samples, done, next_session = load_checkpoint(checkpoint)
    have = done & want
    health = checkpoint_health(checkpoint)
    return {"planned": len(want), "done": len(have),
            "remaining": len(want - have),
            "fraction": len(have) / max(1, len(want)),
            "sessions": next_session, "samples_on_disk": len(samples),
            "stale_triples": len(done - want),
            # Surfaced, because a checkpoint whose system under test died
            # otherwise reports itself complete, and a caller reading only
            # `fraction` cannot tell a finished run from a failed one (ENG-008).
            "errored_samples": health["errored"],
            "dead_triples": health["dead_triples"],
            "error_rate": round(health["error_rate"], 3)}


def record(
    invocations: Sequence[Invocation],
    arms: dict[str, SystemUnderTest],
    k: int = 10,
    checkpoint: str | Path | None = None,
    progress_every: int = 0,
    group_by_input: bool = True,
    should_stop: Callable[[], bool] | None = None,
    abort_after_dead: int = 3,
) -> Recording:
    """Collect k samples per input per arm, interleaved across arms.

    `arms` maps arm name to system. All three of A, A_prime and B are required:
    the decoy arm is not optional, because without it there is no calibrated
    false-alarm rate and the thresholds are guesses (MTH-007).

    With `checkpoint`, each completed triple is appended to that file and a
    rerun skips what is already there. Safe to kill at any point.

    `should_stop`, if given, is checked at every triple boundary. When it
    returns true the run stops and raises `RunPaused` rather than returning a
    partial recording, because a partial recording is indistinguishable from a
    complete one once it reaches the detector. Everything already collected is
    on disk if `checkpoint` was given, and a rerun continues from there.

    `abort_after_dead` stops the run once that many consecutive triples have
    had every arm fail, raising `RecordingFailed`. Setting it to 0 disables the
    check, which is almost never right: the alternative is a checkpoint full of
    error strings that reports itself complete.

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
    # A warning rather than an error: the check is best-effort and cannot see
    # every system's configuration, so refusing on it would refuse runs it
    # cannot actually judge. Loud, because the failure it describes is silent.
    for msg in decoy_independence_warnings(arms):
        warnings.warn(msg, RuntimeWarning, stacklevel=2)

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
    dead_run = 0
    # Grouped: every sample of one input, then the next input. Ungrouped: one
    # sample of every input, then the next sample index.
    if group_by_input:
        schedule = [(inv, idx) for inv in invocations for idx in range(k)]
    else:
        schedule = [(inv, idx) for idx in range(k) for inv in invocations]
    try:
        for pos, (inv, idx) in enumerate(schedule):
            # Rotate which arm leads, so no arm owns the cold position.
            rotated = ARMS[idx % len(ARMS) :] + ARMS[: idx % len(ARMS)]
            if (inv.input_id, idx) in done:
                continue
            # Checked here, between triples, so a stop never splits a triple.
            if should_stop is not None and should_stop():
                left = sum(1 for j, (i2, x2) in enumerate(schedule)
                           if j >= pos and (i2.input_id, x2) not in done)
                raise RunPaused(n_new, left,
                                Path(checkpoint) if checkpoint else None)
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
            # A triple where every arm failed carries no output at all. One is
            # noise; a run of them means nothing is answering.
            if all(x.error for x in triple):
                dead_run += 1
                if abort_after_dead and dead_run >= abort_after_dead:
                    raise RecordingFailed(dead_run, n_new - dead_run,
                                          str(triple[-1].error))
            else:
                dead_run = 0
            if progress_every and n_new % progress_every == 0:
                failing = f" ({dead_run} failing)" if dead_run else ""
                print(f"  {n_new} triples this session, {len(samples)} samples "
                      f"total{failing}")
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
