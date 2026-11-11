"""The recorder beyond three arms (MTH-027 third append's engine package).

The properties that make the three-arm recorder trustworthy must hold per
roster: tuple-atomicity, resume, rotation, the mandatory decoy pair — and a
three-arm checkpoint recorded before the generalisation must load and resume
exactly as before, because every committed recording is one.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.adapter import ARMS, Invocation, Response, Trace  # noqa: E402
from aprime.recorder import (  # noqa: E402
    load_checkpoint,
    record,
    recording_progress,
    iter_invocations,
)


class _Sys:
    def __init__(self, arm):
        self.arm = arm
        self.name = f"sys-{arm}"

    def invoke(self, inv: Invocation) -> Response:
        return Response(output=f"{self.arm}:{inv.input_id}",
                        trace=Trace(latency_ms=1.0))


def _arms(names):
    return {n: _Sys(n) for n in names}


ROSTER4 = ("A", "A_prime", "B", "B_prime")
ROSTER5 = ("A", "A_prime", "A_prime2", "B", "B_prime")


def test_four_arm_recording_is_tuple_complete(tmp_path):
    cp = tmp_path / "r4.jsonl"
    ids = [f"i{j}" for j in range(6)]
    rec = record(iter_invocations(ids), _arms(ROSTER4), k=2, checkpoint=cp,
                 check_arms_first=False)
    assert len(rec.samples) == 6 * 2 * 4
    samples, done, _ = load_checkpoint(cp, arms=ROSTER4)
    assert len(done) == 12
    by_tuple = {}
    for s in samples:
        by_tuple.setdefault(s.triple, set()).add(s.arm)
    assert all(got == set(ROSTER4) for got in by_tuple.values())


def test_partial_tuple_is_discarded_and_redone_at_four_arms(tmp_path):
    cp = tmp_path / "r4.jsonl"
    ids = ["i0", "i1", "i2"]
    record(iter_invocations(ids), _arms(ROSTER4), k=1, checkpoint=cp,
           check_arms_first=False)
    # Simulate a kill mid-tuple: strip the last line (one arm of one tuple).
    lines = cp.read_text(encoding="utf-8").splitlines()
    cp.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
    _, done, _ = load_checkpoint(cp, arms=ROSTER4)
    assert len(done) == 2, "the broken tuple must not count as finished"
    # Judged against the classic trio it would wrongly pass: the roster
    # matters, which is why record() always passes its own.
    _, done_trio, _ = load_checkpoint(cp)
    assert len(done_trio) == 3
    prog = recording_progress(cp, iter_invocations(ids), 1, arms=ROSTER4)
    assert prog["remaining"] == 1
    rec = record(iter_invocations(ids), _arms(ROSTER4), k=1, checkpoint=cp,
                 check_arms_first=False)
    assert len({s.triple for s in rec.samples}) == 3
    _, done, session = load_checkpoint(cp, arms=ROSTER4)
    assert len(done) == 3 and session >= 2


def test_five_arm_lead_rotates_across_the_whole_roster(tmp_path):
    cp = tmp_path / "r5.jsonl"
    rec = record(iter_invocations(["i0"]), _arms(ROSTER5), k=5, checkpoint=cp,
                 check_arms_first=False)
    first_arm_per_tuple = {}
    for s in sorted(rec.samples, key=lambda x: x.order):
        first_arm_per_tuple.setdefault(s.sample_idx, s.arm)
    # k = roster size, so every arm leads exactly once.
    assert sorted(first_arm_per_tuple.values()) == sorted(ROSTER5)


def test_classic_trio_behaviour_is_byte_identical(tmp_path):
    cp = tmp_path / "trio.jsonl"
    ids = ["i0", "i1"]
    rec = record(iter_invocations(ids), _arms(ARMS), k=2, checkpoint=cp,
                 check_arms_first=False)
    # Rotation order for the trio is ARMS order, as it always was.
    first = min(rec.samples, key=lambda s: s.order)
    assert first.arm == "A"
    with_default = load_checkpoint(cp)
    with_roster = load_checkpoint(cp, arms=ARMS)
    assert with_default[1] == with_roster[1]
    assert [s.order for s in with_default[0]] == [s.order for s in with_roster[0]]


def test_the_decoy_pair_stays_mandatory():
    with pytest.raises(ValueError, match="A_prime is mandatory"):
        record(iter_invocations(["i0"]), _arms(("A", "B")), k=1,
               check_arms_first=False)


def test_a_two_arm_null_pair_records(tmp_path):
    """A null pair (A, A_prime) alone is a legitimate recording: the
    pre-registration's hard stop runs on exactly this shape."""
    cp = tmp_path / "null.jsonl"
    rec = record(iter_invocations(["i0", "i1"]), _arms(("A", "A_prime")), k=2,
                 checkpoint=cp, check_arms_first=False)
    assert len(rec.samples) == 2 * 2 * 2
    _, done, _ = load_checkpoint(cp, arms=("A", "A_prime"))
    assert len(done) == 4


def test_mislabelled_arm_is_still_refused():
    arms = {"A": _Sys("A"), "A_prime": _Sys("A_prime"), "B_prime": _Sys("B")}
    with pytest.raises(ValueError, match="labelled"):
        record(iter_invocations(["i0"]), arms, k=1, check_arms_first=False)


def test_checkpoint_stays_plain_jsonl_at_any_roster(tmp_path):
    cp = tmp_path / "r4.jsonl"
    record(iter_invocations(["i0"]), _arms(ROSTER4), k=1, checkpoint=cp,
           check_arms_first=False)
    rows = [json.loads(ln) for ln in cp.read_text(encoding="utf-8").splitlines()]
    assert {r["arm"] for r in rows} == set(ROSTER4)
    assert all("input_id" in r and "sample_idx" in r for r in rows)
