"""Checkpointing and resumption.

A study run occupies the owner's only machine for hours. If it cannot be paused
it is not a long job, it is a lockout — so these tests cover the case that
actually happens: the process is killed at an arbitrary moment and restarted.

The property that must survive a kill is MTH-015's: A, A_prime and B for a given
sample are collected under the same conditions. A resume that restarted
mid-triple would split one sample across two load regimes, so a partial triple
is discarded and redone rather than completed.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime.adapter import ARMS  # noqa: E402
from aprime.recorder import iter_invocations, load_checkpoint, record  # noqa: E402
from aprime.stub import build_arms  # noqa: E402


def _arms(ids, affected=frozenset()):
    a, ap, b = build_arms(list(ids), set(affected))
    return {"A": a, "A_prime": ap, "B": b}


def test_checkpoint_round_trips(tmp_path):
    ids = [f"i{n}" for n in range(6)]
    cp = tmp_path / "run.jsonl"
    rec = record(iter_invocations(ids), _arms(ids), k=3, checkpoint=cp)
    assert cp.exists()
    kept, done, next_session = load_checkpoint(cp)
    assert len(done) == 6 * 3
    assert len(kept) == len(rec.samples) == 6 * 3 * 3
    assert next_session == 1


def test_resume_skips_completed_work(tmp_path):
    ids = [f"i{n}" for n in range(5)]
    cp = tmp_path / "run.jsonl"
    record(iter_invocations(ids), _arms(ids), k=2, checkpoint=cp)
    before = cp.read_text(encoding="utf-8").count("\n")

    # Second call over the same corpus should do nothing new.
    rec2 = record(iter_invocations(ids), _arms(ids), k=2, checkpoint=cp)
    after = cp.read_text(encoding="utf-8").count("\n")
    assert after == before, "resume re-recorded work that was already done"
    assert len(rec2.samples) == 5 * 2 * 3
    assert rec2.sessions == 1, "no new session should have been opened"


def test_extending_k_only_records_the_new_samples(tmp_path):
    ids = [f"i{n}" for n in range(4)]
    cp = tmp_path / "run.jsonl"
    record(iter_invocations(ids), _arms(ids), k=2, checkpoint=cp)
    rec = record(iter_invocations(ids), _arms(ids), k=5, checkpoint=cp)
    assert len(rec.samples) == 4 * 5 * 3
    assert rec.sessions == 2, "the added work should be marked as a new session"
    for iid in ids:
        for arm in ARMS:
            assert len(rec.cloud(iid, arm)) == 5


def test_a_partial_triple_is_discarded_and_redone(tmp_path):
    """The kill case. A triple missing an arm cannot be completed later without
    splitting one sample across two load regimes, so it is thrown away."""
    ids = [f"i{n}" for n in range(4)]
    cp = tmp_path / "run.jsonl"
    record(iter_invocations(ids), _arms(ids), k=2, checkpoint=cp)

    lines = cp.read_text(encoding="utf-8").splitlines()
    # Simulate a kill two calls into the final triple.
    cp.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")

    kept, done, _ = load_checkpoint(cp)
    assert len(done) == 4 * 2 - 1, "the partial triple should not count as done"
    assert all(s.triple in done for s in kept)

    rec = record(iter_invocations(ids), _arms(ids), k=2, checkpoint=cp)
    assert len(rec.samples) == 4 * 2 * 3, "the discarded triple was not redone"
    for iid in ids:
        for arm in ARMS:
            assert len(rec.cloud(iid, arm)) == 2


def test_a_truncated_final_line_does_not_break_resume(tmp_path):
    """A hard kill mid-write leaves half a JSON line. That is expected, not
    corruption, and must not take the whole checkpoint down with it."""
    ids = [f"i{n}" for n in range(3)]
    cp = tmp_path / "run.jsonl"
    record(iter_invocations(ids), _arms(ids), k=2, checkpoint=cp)
    with cp.open("a", encoding="utf-8") as fh:
        fh.write('{"input_id": "i2", "arm": "B", "sample_i')

    kept, done, _ = load_checkpoint(cp)
    assert len(done) == 3 * 2
    rec = record(iter_invocations(ids), _arms(ids), k=2, checkpoint=cp)
    assert len(rec.samples) == 3 * 2 * 3


def test_resumed_run_is_structurally_equivalent_to_an_uninterrupted_one(tmp_path):
    """Resumption must not lose or duplicate work.

    It deliberately does NOT assert byte-identical outputs. A real system under
    test is stochastic, so a resumed run cannot reproduce the exact samples an
    uninterrupted one drew, and a test demanding that would be pinning a
    property production can never have. What must hold is that the same amount
    of work was done, against the same system, over the same corpus.
    """
    ids = [f"i{n}" for n in range(6)]
    whole = record(iter_invocations(ids), _arms(ids), k=3)

    cp = tmp_path / "run.jsonl"
    record(iter_invocations(ids), _arms(ids), k=1, checkpoint=cp)
    resumed = record(iter_invocations(ids), _arms(ids), k=3, checkpoint=cp)

    assert len(resumed.samples) == len(whole.samples)
    for iid in ids:
        for arm in ARMS:
            assert len(resumed.cloud(iid, arm)) == len(whole.cloud(iid, arm)) == 3
            # Same behaviour table: every output the resumed run produced is one
            # the uninterrupted system could also have produced.
            assert set(resumed.cloud(iid, arm)) <= {f"{iid}::mode{j}" for j in range(3)}

    assert {(s.input_id, s.sample_idx, s.arm) for s in resumed.samples} == {
        (s.input_id, s.sample_idx, s.arm) for s in whole.samples
    }


def test_running_without_a_checkpoint_still_works(tmp_path):
    ids = ["a", "b"]
    rec = record(iter_invocations(ids), _arms(ids), k=2)
    assert len(rec.samples) == 2 * 2 * 3
    assert rec.sessions == 1
    assert not list(tmp_path.iterdir()), "no checkpoint should have been written"
