"""End-to-end checks on the three-arm pipeline.

The central one is `test_target_decoy_controls_fdr_on_ground_truth`. Everything
in the design rests on the claim that when the machinery reports a
false-discovery rate of q, the realised rate is q. That claim is unfalsifiable
on a real system, because a real system never tells you which inputs genuinely
changed. The stub exists so it can be checked at least once.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime import fdr, stats  # noqa: E402
from aprime.adapter import Invocation  # noqa: E402
from aprime.dedup import dedup, normalise  # noqa: E402
from aprime.recorder import iter_invocations, record  # noqa: E402
from aprime.stub import build_arms  # noqa: E402

Q = 0.10


def _run(n_inputs: int, n_affected: int, strength: float, seed: int, k: int = 10):
    ids = [f"in{i:04d}" for i in range(n_inputs)]
    rng = random.Random(seed)
    affected = set(rng.sample(ids, n_affected)) if n_affected else set()
    a, ap, b = build_arms(ids, affected, "mode_share", strength=strength, seed=seed)
    rec = record(iter_invocations(ids), {"A": a, "A_prime": ap, "B": b}, k=k)
    ca, cap, cb = rec.clouds("A"), rec.clouds("A_prime"), rec.clouds("B")
    targets = np.array([stats.tv_distance(ca[i], cb[i]) for i in ids])
    decoys = np.array([stats.tv_distance(ca[i], cap[i]) for i in ids])
    truth = np.array([i in affected for i in ids])
    return ids, targets, decoys, truth, rec


# ---------------------------------------------------------------- recorder ---


def test_all_three_arms_are_required():
    a, ap, b = build_arms(["x"], set())
    with pytest.raises(ValueError, match="A_prime"):
        record(iter_invocations(["x"]), {"A": a, "B": b}, k=2)


def test_arm_labels_must_match_their_slot():
    a, ap, b = build_arms(["x"], set())
    with pytest.raises(ValueError, match="labelled"):
        record(iter_invocations(["x"]), {"A": a, "A_prime": b, "B": ap}, k=2)


def test_arms_are_interleaved_not_batched():
    """MTH-015: a decoy arm collected in a different load regime measures a
    different noise floor. Batching would show as a long single-arm run."""
    _, _, _, _, rec = _run(20, 0, 0.0, seed=1, k=4)
    assert rec.interleaving_gap() <= 2, rec.interleaving_gap()


def test_every_arm_produces_k_samples_per_input():
    ids, _, _, _, rec = _run(10, 0, 0.0, seed=2, k=7)
    for arm in ("A", "A_prime", "B"):
        for iid in ids:
            assert len(rec.cloud(iid, arm)) == 7


# -------------------------------------------------------------------- dedup ---


def test_normalise_collapses_formatting_only():
    assert normalise("  Hello   WORLD! ") == normalise("hello world")
    assert normalise("café") == normalise("cafe")
    assert normalise("a b") != normalise("a c")


def test_dedup_keeps_one_per_group_and_counts_the_rest():
    invs = [
        Invocation("i1", "What is the refund policy?"),
        Invocation("i2", "what is the REFUND policy!!"),
        Invocation("i3", "How long is shipping?"),
    ]
    r = dedup(invs)
    assert [i.input_id for i in r.kept] == ["i1", "i3"]
    assert r.groups["i1"] == ["i1", "i2"]
    assert r.n_removed == 1
    assert r.duplication_rate == pytest.approx(1 / 3)


# -------------------------------------------------------------------- stats ---


def test_tv_distance_bounds():
    assert stats.tv_distance(["a"] * 10, ["a"] * 10) == 0.0
    assert stats.tv_distance(["a"] * 10, ["b"] * 10) == 1.0
    assert stats.tv_distance(["a"] * 5 + ["b"] * 5, ["a"] * 10) == pytest.approx(0.5)


def test_dispersion_is_zero_for_a_deterministic_arm():
    assert stats.dispersion(["a"] * 10) == 0.0
    assert stats.dispersion(["a", "b"]) == pytest.approx(0.5)


def test_mode_collapse_registers_in_dispersion_not_only_in_mix():
    """MTH-005: a reliability change with the same modal answer."""
    spread = ["a"] * 5 + ["b"] * 3 + ["c"] * 2
    collapsed = ["a"] * 10
    assert stats.dispersion_ratio(spread, collapsed) > 0.9
    assert stats.novel_mode_mass(spread, collapsed) == 0.0


def test_novel_mode_mass_is_asymmetric():
    assert stats.novel_mode_mass(["a"] * 10, ["a"] * 5 + ["z"] * 5) == pytest.approx(0.5)
    assert stats.novel_mode_mass(["a"] * 5 + ["z"] * 5, ["a"] * 10) == 0.0


# ---------------------------------------------------------------------- fdr ---


def test_selection_is_empty_rather_than_bad_when_nothing_qualifies():
    rng = np.random.default_rng(0)
    x = rng.normal(size=200)
    y = rng.normal(size=200)
    sel = fdr.select(x, y, q=0.01)
    assert sel.n_discoveries == 0 or sel.fdr_hat <= 0.01


def test_no_change_means_almost_no_discoveries():
    """The candidate is behaviourally identical to the baseline. Anything
    flagged here is a false alarm by construction."""
    _, targets, decoys, truth, _ = _run(300, 0, 0.0, seed=11)
    assert not truth.any()
    sel = fdr.select(targets, decoys, q=Q)
    assert sel.n_discoveries <= 3, f"{sel.n_discoveries} false alarms on an unchanged system"


def test_target_decoy_controls_fdr_on_ground_truth():
    """The claim the whole design rests on, checked against known truth.

    FDR control is a statement in expectation, so it is averaged over seeds. A
    per-run ceiling is asserted too, so a catastrophic single case cannot hide
    inside a good mean.

    Note what is deliberately NOT asserted here: power. Control and power are
    separate properties, and conflating them is how a detector ends up with its
    budget quietly widened to make a power target. Power has its own test, and
    its own measured envelope.
    """
    realised = []
    for seed in range(5):
        ids, targets, decoys, truth, _ = _run(400, 40, strength=0.9, seed=100 + seed)
        sel = fdr.select(targets, decoys, q=Q)
        flagged = fdr.discoveries(targets, sel)
        realised.append(fdr.realised_fdr(flagged, truth))

    mean_fdr = float(np.mean(realised))
    assert mean_fdr <= Q + 0.02, f"realised FDR {mean_fdr:.3f} over q={Q}: {realised}"
    assert max(realised) <= 0.35, f"a single run blew the budget: {realised}"


def test_power_envelope_k10_is_not_enough_for_a_moderate_shift():
    """Measured, not assumed: k=10 has essentially no power against a moderate
    mode-share shift, and k=20 does. MTH-006 predicted the shape of this from
    combinatorics; these are the numbers on our actual statistic.

    This test exists to fail loudly if someone lowers k for cost reasons without
    re-deriving the envelope. It asserts the *gap*, not absolute values, so it
    does not become a brittle pin on exact figures.
    """
    def power_at(k: int) -> float:
        out = []
        for seed in range(3):
            _, targets, decoys, truth, _ = _run(300, 30, strength=0.6, seed=300 + seed, k=k)
            sel = fdr.select(targets, decoys, q=Q)
            flagged = fdr.discoveries(targets, sel)
            out.append(float((flagged & truth).sum()) / int(truth.sum()))
        return float(np.mean(out))

    p10, p20 = power_at(10), power_at(20)
    assert p10 < 0.35, f"k=10 unexpectedly powerful ({p10:.2f}); re-derive the envelope"
    assert p20 > 0.50, f"k=20 lost its power ({p20:.2f}); the statistic regressed"
    assert p20 > p10 + 0.30, f"k=10 {p10:.2f} vs k=20 {p20:.2f}"


def test_power_rises_with_severity():
    """A detection rate that does not increase with the size of the injected
    change is a harness bug before it is a finding."""
    got = []
    for strength in (0.2, 0.5, 0.9):
        _, targets, decoys, truth, _ = _run(300, 30, strength=strength, seed=7)
        sel = fdr.select(targets, decoys, q=Q)
        flagged = fdr.discoveries(targets, sel)
        got.append(float((flagged & truth).sum()) / int(truth.sum()))
    assert got == sorted(got), f"detection not monotone in severity: {got}"


# ----------------------------------------------------------- sticky faults ---


def test_sticky_fault_concentrates_on_its_principals():
    """F8a: the request-level and user-level rates come apart because the same
    users keep landing on the bad path."""
    ids = [f"in{i:03d}" for i in range(120)]
    principals = {iid: f"user{i % 12}" for i, iid in enumerate(ids)}
    affected_users = frozenset({"user0", "user1"})
    a, ap, b = build_arms(
        ids, set(ids), "mode_share", strength=0.9, seed=5,
        sticky_principals=affected_users,
    )
    invs = iter_invocations(ids, principals=principals)
    rec = record(invs, {"A": a, "A_prime": ap, "B": b}, k=10)
    ca, cap, cb = rec.clouds("A"), rec.clouds("A_prime"), rec.clouds("B")

    # Calibrate against the decoy rather than a threshold picked by eye. An
    # earlier version of this test used a fixed cutoff of 0.3 and failed,
    # because unaffected users cross it 26% of the time from sampling noise
    # alone -- which is the exact mistake the decoy arm exists to prevent.
    targets = np.array([stats.tv_distance(ca[i], cb[i]) for i in ids])
    decoys = np.array([stats.tv_distance(ca[i], cap[i]) for i in ids])
    sel = fdr.select(targets, decoys, q=Q)
    flagged = fdr.discoveries(targets, sel)

    is_affected = np.array([principals[i] in affected_users for i in ids])
    rate_affected = float(flagged[is_affected].mean())
    rate_other = float(flagged[~is_affected].mean())
    assert rate_affected > 0.7, f"missed the sticky cohort: {rate_affected:.2f}"
    assert rate_other < 0.10, f"leaked onto unaffected users: {rate_other:.2f}"


def test_sticky_arm_rejects_invocations_without_a_principal():
    a, ap, b = build_arms(["x"], {"x"}, sticky_principals=frozenset({"u1"}))
    rec = record(iter_invocations(["x"]), {"A": a, "A_prime": ap, "B": b}, k=1)
    errs = [s for s in rec.samples if s.error]
    assert errs and "principal" in errs[0].error
