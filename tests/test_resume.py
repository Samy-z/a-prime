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
import warnings
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime.adapter import ARMS, Invocation  # noqa: E402
from aprime.recorder import (  # noqa: E402
    PreflightFailed,
    RecordingFailed,
    RunPaused,
    checkpoint_health,
    decoy_independence_warnings,
    iter_invocations,
    load_checkpoint,
    preflight,
    record,
    recording_progress,
    stop_requested,
)
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


# ------------------------------------------------------------- scheduling ---


def _order_of_first_sample(rec, input_id):
    return min(s.order for s in rec.samples if s.input_id == input_id)


def test_grouping_by_input_keeps_an_inputs_samples_together():
    """All k*3 calls for one input share a prompt prefix, so grouping lets a
    caching server pay prefill once per input instead of once per call. Measured
    on this hardware that is worth roughly twenty days."""
    ids = [f"i{n}" for n in range(4)]
    rec = record(iter_invocations(ids), _arms(ids), k=3, group_by_input=True)
    for iid in ids:
        orders = sorted(s.order for s in rec.samples if s.input_id == iid)
        assert orders == list(range(orders[0], orders[0] + len(orders))), (
            f"{iid} samples were not contiguous"
        )


def test_ungrouped_spreads_each_input_across_the_run():
    ids = [f"i{n}" for n in range(4)]
    rec = record(iter_invocations(ids), _arms(ids), k=3, group_by_input=False)
    orders = sorted(s.order for s in rec.samples if s.input_id == "i0")
    assert orders != list(range(orders[0], orders[0] + len(orders)))


def test_the_triple_stays_atomic_under_both_schedules():
    """Grouping changes the order of triples, never the contents of one. A, B
    and the decoy for a given sample must remain adjacent."""
    ids = [f"i{n}" for n in range(3)]
    for grouped in (True, False):
        rec = record(iter_invocations(ids), _arms(ids), k=2, group_by_input=grouped)
        by_order = sorted(rec.samples, key=lambda s: s.order)
        for i in range(0, len(by_order), 3):
            chunk = by_order[i : i + 3]
            assert len({s.triple for s in chunk}) == 1, f"triple split, grouped={grouped}"
            assert {s.arm for s in chunk} == set(ARMS)


def test_both_schedules_collect_the_same_work():
    ids = [f"i{n}" for n in range(4)]
    g = record(iter_invocations(ids), _arms(ids), k=3, group_by_input=True)
    u = record(iter_invocations(ids), _arms(ids), k=3, group_by_input=False)
    assert len(g.samples) == len(u.samples)
    assert {(s.input_id, s.sample_idx, s.arm) for s in g.samples} == {
        (s.input_id, s.sample_idx, s.arm) for s in u.samples
    }


def test_samples_carry_wallclock_and_the_span_is_reported():
    """Grouping means an input's noise floor spans a short window while the run
    spans a long one. The span is what says how much room there is for drift the
    floor cannot see."""
    ids = ["a", "b"]
    rec = record(iter_invocations(ids), _arms(ids), k=2)
    assert all(s.ts > 0 for s in rec.samples)
    assert rec.wallclock_span_s() >= 0.0
    assert not rec.spans_utc_date_boundary()


def test_a_run_straddling_midnight_is_flagged():
    """A widely used chat template interpolates the current date into a hidden
    system prompt, so a run crossing midnight gets a prompt edit nobody made."""
    ids = ["a"]
    rec = record(iter_invocations(ids), _arms(ids), k=1)
    day = 86400
    base = (rec.samples[0].ts // day) * day
    shifted = [
        type(s)(**{**s.__dict__, "ts": base - 10 if i == 0 else base + 10})
        for i, s in enumerate(rec.samples)
    ]
    rec.samples = shifted
    assert rec.spans_utc_date_boundary()


# ------------------------------------------------- decoy independence (MTH-023)


class _Seeded:
    """A system that exposes a sampling seed, as the ones in this repo do."""

    def __init__(self, arm, seed):
        self.arm = arm
        self.seed = seed

    def invoke(self, inv):  # pragma: no cover - never called by these tests
        raise AssertionError("not invoked")


class _NestedSeed:
    """A system whose seed lives on a transport it holds, like Cell -> chat."""

    def __init__(self, arm, seed):
        self.arm = arm
        self.chat = type("T", (), {"seed": seed})()

    def invoke(self, inv):  # pragma: no cover
        raise AssertionError("not invoked")


def _trio(cls, a, ap, b=99):
    return {"A": cls("A", a), "A_prime": cls("A_prime", ap), "B": cls("B", b)}


def test_two_baseline_arms_sharing_a_pinned_seed_are_flagged():
    """A_prime IS the null. Eight repeats under a pinned seed gave 2 distinct
    outputs against 8 with it unset, and a null on two points calibrates a tail
    quantile no better than one on a single point (MTH-023). Nothing about that
    failure is loud on its own: every arm records cleanly."""
    warns = decoy_independence_warnings(_trio(_Seeded, 7, 7))
    assert len(warns) == 1
    assert "seed" in warns[0] and "MTH-023" in warns[0]


def test_differing_or_unset_seeds_are_not_flagged():
    assert decoy_independence_warnings(_trio(_Seeded, 7, 8)) == []
    assert decoy_independence_warnings(_trio(_Seeded, None, None)) == []


def test_a_seed_held_one_level_down_is_still_found():
    """Cell keeps its sampling on the chat transport it holds, not on itself."""
    assert len(decoy_independence_warnings(_trio(_NestedSeed, 7, 7))) == 1
    assert decoy_independence_warnings(_trio(_NestedSeed, 7, 8)) == []


def test_a_system_that_exposes_nothing_is_not_flagged():
    """The adapter Protocol carries no sampling configuration and must not start
    to, so this check is a courtesy for systems built here and silent for
    anything else. Silence must not read as approval, which is why it warns
    rather than certifying."""
    class Opaque:
        arm = "A"

        def invoke(self, inv):  # pragma: no cover
            raise AssertionError("not invoked")

    arms = {"A": Opaque(), "A_prime": Opaque(), "B": Opaque()}
    assert decoy_independence_warnings(arms) == []


def test_record_warns_rather_than_refusing_on_a_shared_seed():
    """Best-effort checks must not refuse runs they cannot actually judge."""
    ids = ["i0", "i1"]
    arms = _arms(ids)
    for system in arms.values():
        system.seed = 7
    with pytest.warns(RuntimeWarning, match="MTH-023"):
        rec = record(iter_invocations(ids), arms, k=2)
    assert len(rec.samples) == len(ids) * 2 * len(ARMS)


def test_an_ordinary_run_raises_no_such_warning():
    """The stub arms expose no seed, so the guard must stay quiet on them."""
    ids = ["i0", "i1"]
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        record(iter_invocations(ids), _arms(ids), k=2)


# ------------------------------------------------------------ pause and resume


def test_a_paused_run_raises_rather_than_returning_a_partial_recording(tmp_path):
    """A partial recording is indistinguishable from a complete one once it
    reaches the detector: shorter clouds, thresholds fitted to fewer decoys, and
    nothing in the report to say so. Raising is the only place to stop that."""
    ids = [f"i{n}" for n in range(6)]
    cp = tmp_path / "run.jsonl"
    stop = {"after": 2}
    calls = {"n": 0}

    def should_stop():
        calls["n"] += 1
        return calls["n"] > stop["after"]

    with pytest.raises(RunPaused) as caught:
        record(iter_invocations(ids), _arms(ids), k=1, checkpoint=cp,
               should_stop=should_stop)
    exc = caught.value
    assert exc.completed == 2
    assert exc.remaining == 4
    assert exc.checkpoint == cp
    assert "resumable" not in str(exc), "a checkpointed pause is not a data loss"


def test_a_pause_lands_on_a_triple_boundary(tmp_path):
    """Never mid-triple, so a stop costs at most one triple of work and never
    leaves a partial set behind."""
    ids = [f"i{n}" for n in range(6)]
    cp = tmp_path / "run.jsonl"
    n = {"c": 0}

    def should_stop():
        n["c"] += 1
        return n["c"] > 3

    with pytest.raises(RunPaused):
        record(iter_invocations(ids), _arms(ids), k=1, checkpoint=cp,
               should_stop=should_stop)
    kept, done, _ = load_checkpoint(cp)
    assert len(kept) % len(ARMS) == 0, "every saved triple must be complete"
    assert len(done) == len(kept) // len(ARMS)


def test_a_paused_run_resumes_and_completes(tmp_path):
    """The whole point. Stop overnight, start again, get a full recording."""
    ids = [f"i{n}" for n in range(6)]
    cp = tmp_path / "run.jsonl"
    n = {"c": 0}
    with pytest.raises(RunPaused):
        record(iter_invocations(ids), _arms(ids), k=2, checkpoint=cp,
               should_stop=lambda: (n.__setitem__("c", n["c"] + 1)
                                    or n["c"] > 4))
    part = recording_progress(cp, iter_invocations(ids), k=2)
    assert 0 < part["done"] < part["planned"]

    rec = record(iter_invocations(ids), _arms(ids), k=2, checkpoint=cp)
    assert len(rec.samples) == 6 * 2 * len(ARMS)
    full = recording_progress(cp, iter_invocations(ids), k=2)
    assert full["remaining"] == 0
    assert full["fraction"] == 1.0
    for iid in ids:
        for arm in ARMS:
            assert len(rec.cloud(iid, arm)) == 2


def test_pausing_without_a_checkpoint_says_the_work_is_lost(tmp_path):
    """Silence here would be the worst outcome: the run stops, nothing is on
    disk, and the message implies otherwise."""
    ids = ["i0", "i1"]
    with pytest.raises(RunPaused) as caught:
        record(iter_invocations(ids), _arms(ids), k=1, should_stop=lambda: True)
    assert "NOTHING WAS SAVED" in str(caught.value)
    assert caught.value.checkpoint is None


def test_a_stop_file_is_the_signal(tmp_path):
    """A file, not a signal handler, because whoever wants the run stopped is
    usually not at the terminal that started it."""
    flag = tmp_path / "STOP"
    check = stop_requested(flag)
    assert check() is False
    flag.write_text("", encoding="utf-8")
    assert check() is True


def test_progress_reads_the_checkpoint_without_running_anything(tmp_path):
    ids = [f"i{n}" for n in range(4)]
    cp = tmp_path / "run.jsonl"
    invs = iter_invocations(ids)
    empty = recording_progress(cp, invs, k=3)
    assert empty == {"planned": 12, "done": 0, "remaining": 12,
                     "fraction": 0.0, "sessions": 0}
    record(invs, _arms(ids), k=3, checkpoint=cp)
    after = recording_progress(cp, invs, k=3)
    assert after["done"] == 12 and after["remaining"] == 0
    assert after["stale_triples"] == 0


def test_progress_notices_triples_that_no_longer_belong(tmp_path):
    """A checkpoint keyed on a configuration that has since changed holds work
    for inputs the plan no longer contains. Counting those as progress would
    report a run as further along than it is."""
    cp = tmp_path / "run.jsonl"
    old_ids = [f"i{n}" for n in range(4)]
    record(iter_invocations(old_ids), _arms(old_ids), k=1, checkpoint=cp)
    new_ids = ["i0", "i1", "zz9"]
    prog = recording_progress(cp, iter_invocations(new_ids), k=1)
    assert prog["done"] == 2
    assert prog["remaining"] == 1
    assert prog["stale_triples"] == 2


# ------------------------------------------- a dead system under test (ENG-008)


class _Dead:
    """A system that cannot be reached, like a server that stopped listening."""

    def __init__(self, arm, fail_from=0):
        self.arm = arm
        self.fail_from = fail_from
        self.calls = 0

    def invoke(self, inv):
        self.calls += 1
        if self.calls > self.fail_from:
            raise OSError("[WinError 10061] target machine actively refused it")
        from aprime.adapter import Response, Trace
        return Response(output="fine", trace=Trace(latency_ms=1.0))


def _dead_arms(fail_from=0):
    return {a: _Dead(a, fail_from) for a in ARMS}


def test_a_run_where_nothing_answers_aborts_instead_of_filling_the_checkpoint():
    """A server stopped listening 90 seconds into a 50 minute run. The recorder
    wrote 698 connection failures as complete triples, reported steady progress
    throughout, and the checkpoint then called itself 100% recorded."""
    ids = [f"i{n}" for n in range(50)]
    with pytest.raises(RecordingFailed) as caught:
        record(iter_invocations(ids), _dead_arms(), k=1, abort_after_dead=3,
               check_arms_first=False)
    exc = caught.value
    assert exc.consecutive == 3
    assert "refused" in exc.last_error
    assert "not counted as done" in str(exc)


def test_one_failed_triple_is_noise_and_does_not_abort():
    """Transient failures happen. Only a run of them means nothing is answering."""
    ids = [f"i{n}" for n in range(6)]
    arms = _dead_arms(fail_from=1)   # first call each succeeds, rest fail
    with pytest.raises(RecordingFailed):
        record(iter_invocations(ids), arms, k=1, abort_after_dead=3,
               check_arms_first=False)
    # The first triple succeeded, so the abort counted from the second.
    assert all(a.calls >= 2 for a in arms.values())


def test_the_abort_can_be_switched_off(tmp_path):
    ids = ["i0", "i1"]
    cp = tmp_path / "run.jsonl"
    rec = record(iter_invocations(ids), _dead_arms(), k=1, checkpoint=cp,
                 abort_after_dead=0, check_arms_first=False)
    assert len(rec.samples) == len(ids) * len(ARMS)
    assert all(s.error for s in rec.samples)


def test_a_triple_where_every_arm_failed_is_not_counted_as_done(tmp_path):
    """Otherwise a resume skips it forever and the recording stays short."""
    cp = tmp_path / "run.jsonl"
    ids = ["i0", "i1"]
    record(iter_invocations(ids), _dead_arms(), k=1, checkpoint=cp,
           abort_after_dead=0, check_arms_first=False)
    kept, done, _ = load_checkpoint(cp)
    assert done == set(), "all-error triples must not count as finished"
    assert kept == []
    raw, raw_done, _ = load_checkpoint(cp, retry_dead_triples=False)
    assert len(raw_done) == 2, "the file itself still holds them"
    assert len(raw) == 2 * len(ARMS)


def test_a_dead_run_is_redone_on_the_next_attempt(tmp_path):
    """The recovery path: server dies, comes back, rerun completes."""
    cp = tmp_path / "run.jsonl"
    ids = ["i0", "i1", "i2"]
    record(iter_invocations(ids), _dead_arms(), k=1, checkpoint=cp,
           abort_after_dead=0, check_arms_first=False)
    assert recording_progress(cp, iter_invocations(ids), 1)["done"] == 0

    rec = record(iter_invocations(ids), _arms(ids), k=1, checkpoint=cp)
    assert len(rec.samples) == 3 * len(ARMS)
    prog = recording_progress(cp, iter_invocations(ids), 1)
    assert prog["done"] == 3 and prog["remaining"] == 0


def test_a_partly_failed_triple_is_kept_because_other_samples_cover_it(tmp_path):
    """Only an all-arms failure is pure waste. A triple with one bad arm still
    carries two real outputs, and at k>1 the input survives on its other
    samples, so retrying it risks looping on an arm that always fails."""
    cp = tmp_path / "run.jsonl"
    ids = ["i0"]
    arms = _arms(ids)
    arms["B"] = _Dead("B", fail_from=0)
    record(iter_invocations(ids), arms, k=1, checkpoint=cp, abort_after_dead=0,
           check_arms_first=False)
    _, done, _ = load_checkpoint(cp)
    assert done == {("i0", 0)}


def test_checkpoint_health_tells_a_failed_run_from_a_finished_one(tmp_path):
    good, bad = tmp_path / "good.jsonl", tmp_path / "bad.jsonl"
    ids = ["i0", "i1"]
    record(iter_invocations(ids), _arms(ids), k=2, checkpoint=good)
    record(iter_invocations(ids), _dead_arms(), k=2, checkpoint=bad,
           abort_after_dead=0, check_arms_first=False)

    g, b = checkpoint_health(good), checkpoint_health(bad)
    assert g["error_rate"] == 0.0 and g["dead_triples"] == 0
    assert b["error_rate"] == 1.0 and b["dead_triples"] == 4
    assert b["messages"] and "refused" in b["messages"][0]
    assert checkpoint_health(tmp_path / "nope.jsonl")["exists"] is False


def test_progress_surfaces_the_error_rate(tmp_path):
    """A caller reading only `fraction` could not tell the two apart, which is
    how a 97%-failed run was reported as complete."""
    cp = tmp_path / "run.jsonl"
    ids = ["i0", "i1"]
    record(iter_invocations(ids), _dead_arms(), k=1, checkpoint=cp,
           abort_after_dead=0, check_arms_first=False)
    p = recording_progress(cp, iter_invocations(ids), 1)
    assert p["error_rate"] == 1.0
    assert p["dead_triples"] == 2
    assert p["fraction"] == 0.0, "a failed run is not progress"


# ----------------------------------------------------- preflight (ENG-008 again)


def test_preflight_asks_every_arm_once_and_reports_each():
    ids = ["i0"]
    arms = _arms(ids)
    result = preflight(arms, next(iter(iter_invocations(ids))))
    assert result.ok
    assert {p.arm for p in result.probes} == set(ARMS)
    assert all(p.latency_ms >= 0 for p in result.probes)
    assert "ok" in result.summary()


def test_a_run_with_a_dead_arm_never_starts():
    """abort_after_dead catches this within three triples. The preflight catches
    it before the first one, in the time it takes to ask one question."""
    ids = [f"i{n}" for n in range(40)]
    with pytest.raises(PreflightFailed) as caught:
        record(iter_invocations(ids), _dead_arms(), k=6)
    msg = str(caught.value)
    assert "before recording anything" in msg
    assert "no checkpoint to resume" in msg


def test_a_failed_preflight_writes_nothing_to_disk(tmp_path):
    """The exception says nothing is on disk, so that had better be true."""
    cp = tmp_path / "run.jsonl"
    ids = ["i0", "i1"]
    with pytest.raises(PreflightFailed):
        record(iter_invocations(ids), _dead_arms(), k=2, checkpoint=cp)
    assert not cp.exists()


def test_preflight_names_only_the_arms_that_failed():
    ids = ["i0"]
    arms = _arms(ids)
    arms["B"] = _Dead("B")
    result = preflight(arms, next(iter(iter_invocations(ids))))
    assert not result.ok
    assert [p.arm for p in result.failed] == ["B"]
    assert "B FAILED" in result.summary()
    with pytest.raises(PreflightFailed, match="preflight failed on B"):
        record(iter_invocations(ids), arms, k=1)


def test_an_empty_output_is_reported_but_is_not_a_failure():
    """A cell that exhausts its step budget legitimately returns nothing.
    Refusing on that would refuse correct behaviour."""
    from aprime.adapter import Response, Trace

    class Silent:
        def __init__(self, arm):
            self.arm = arm

        def invoke(self, inv):
            return Response(output="", trace=Trace(latency_ms=1.0))

    arms = {a: Silent(a) for a in ARMS}
    result = preflight(arms, Invocation("i0", "q"))
    assert result.ok, "empty is not a failure"
    assert all(p.empty for p in result.probes)
    assert "ok but empty" in result.summary()


def test_an_errored_trace_counts_as_a_failure_even_without_an_exception():
    """A system that catches its own errors and reports them in the trace is
    still a system that cannot answer. Cells do exactly this."""
    from aprime.adapter import Response, Trace

    class Reports:
        def __init__(self, arm):
            self.arm = arm

        def invoke(self, inv):
            return Response(output="", trace=Trace(
                latency_ms=1.0, error="URLError: connection refused"))

    arms = {a: Reports(a) for a in ARMS}
    result = preflight(arms, Invocation("i0", "q"))
    assert not result.ok
    assert len(result.failed) == len(ARMS)
    assert "refused" in result.failed[0].error


def test_the_preflight_can_be_switched_off(tmp_path):
    """Only for an arm expected to fail on the probe input."""
    cp = tmp_path / "run.jsonl"
    ids = ["i0"]
    rec = record(iter_invocations(ids), _dead_arms(), k=1, checkpoint=cp,
                 abort_after_dead=0, check_arms_first=False)
    assert all(s.error for s in rec.samples)


def test_an_empty_corpus_is_refused_rather_than_probed():
    with pytest.raises(ValueError, match="no invocations"):
        record([], _arms(["i0"]), k=1)
