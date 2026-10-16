"""Scores that are equal as values must be equal to the estimator (ENG-010).

`stats.tv_distance` is `0.5 * sum(abs(...))` over a set of mode keys, and two
clouds whose distance is exactly 5/6 can come out as 0.8333333333333333 or as
0.8333333333333334 depending on which terms are summed in which order. Before
the fix, `np.unique` saw two cuts where there was one, and at the upper cut
every score on the lower float, target or decoy alike, was counted as below it.
On the committed hospitality-agent diagnosis that read as 8 targets above 2
decoys (0.375) where the value-consistent count is 13 above 9 (0.769) at that
cut, and the true best cut is 1.0 (STD-011 third append).

These tests build the two float forms from real clouds, through the real
statistic, and check that every entry point counts a tie as a tie.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime import fdr, stats  # noqa: E402

# Two cloud pairs at a mode-share distance of exactly 5/6. Each sums to its
# float in every order of its terms, so the forms below do not depend on set
# iteration order (and therefore not on hash randomisation).
UPPER_CLOUDS = (["d"] * 4, ["c"] * 5 + ["d"])
LOWER_CLOUDS = (["c", "d", "d", "d"], ["a", "b", "b", "b", "b", "c"])
UPPER = 0.8333333333333334
LOWER = 0.8333333333333333


def test_the_statistic_really_produces_both_float_forms():
    """The premise. If this fails, the floats moved and the fixtures below need
    re-deriving, not the estimator."""
    assert stats.tv_distance(*UPPER_CLOUDS) == UPPER
    assert stats.tv_distance(*LOWER_CLOUDS) == LOWER
    assert UPPER != LOWER
    assert UPPER == pytest.approx(5 / 6) and LOWER == pytest.approx(5 / 6)


def _hospitality_shaped() -> tuple[np.ndarray, np.ndarray]:
    """The committed hospitality-agent mode_share arrays, with the float split
    that produced the recorded 8/2: 8 targets at 5/6 (3 upper, 5 lower) and 5
    at 1.0; 8 decoys at 5/6 (1 upper, 7 lower), 1 at 1.0, 31 below."""
    up = stats.tv_distance(*UPPER_CLOUDS)
    lo = stats.tv_distance(*LOWER_CLOUDS)
    targets = np.array([up] * 3 + [lo] * 5 + [1.0] * 5 + [2 / 3] * 11 + [0.5] * 3
                       + [1 / 3] * 6 + [1 / 6] * 3 + [0.0] * 4)
    decoys = np.array([up] * 1 + [lo] * 7 + [1.0] + [2 / 3] * 3 + [0.5] * 13
                      + [1 / 3] * 8 + [1 / 6] * 6 + [0.0])
    assert len(targets) == 40 and len(decoys) == 40
    return targets, decoys


def test_estimate_counts_every_score_tying_the_cut_by_value():
    targets, decoys = _hospitality_shaped()
    # 13 targets and 9 decoys sit at or above 5/6 as values, whichever float
    # each arrived in. Asked at either float form, the answer is the same.
    assert fdr.estimate_fdr(targets, decoys, UPPER) == pytest.approx(10 / 13)
    assert fdr.estimate_fdr(targets, decoys, LOWER) == pytest.approx(10 / 13)
    assert fdr.estimate_fdr(targets, decoys, 5 / 6) == pytest.approx(10 / 13)


def test_best_achievable_sees_one_cut_at_five_sixths_with_all_tied_decoys():
    targets, decoys = _hospitality_shaped()
    best = fdr.best_achievable(targets, decoys)
    assert best is not None
    # The recorded artefact: 0.375 at 0.8333 with 8 targets above 2 decoys.
    assert (best.targets_above, best.decoys_above) != (8, 2)
    # Value-consistent: the lowest estimate is at the top value, 5 above 1.
    assert best.cut == 1.0
    assert (best.targets_above, best.decoys_above) == (5, 1)
    assert best.estimate == pytest.approx(0.4)


def test_select_does_not_admit_a_cut_that_a_tied_decoy_fails():
    """Ten targets at 1.0, ten at the upper 5/6; two decoys at the lower 5/6.

    Counted as floats the upper cut had 20 targets above 0 decoys (0.05 <= q)
    and `select` flagged 20. Counted as values it is 20 above 2 (0.15 > q), so
    the selection falls back to the top value and flags 10 at exactly q."""
    up = stats.tv_distance(*UPPER_CLOUDS)
    lo = stats.tv_distance(*LOWER_CLOUDS)
    targets = np.array([1.0] * 10 + [up] * 10 + [0.5] * 20)
    decoys = np.array([lo] * 2 + [0.5] * 38)
    sel = fdr.select(targets, decoys, q=0.10)
    assert sel.n_discoveries == 10
    assert sel.threshold == 1.0
    assert sel.fdr_hat == pytest.approx(0.10)
    assert int(fdr.discoveries(targets, sel).sum()) == sel.n_discoveries


def test_discoveries_admit_targets_on_the_lower_float_of_the_threshold():
    """When the cut is at 5/6, a target that arrived on the lower float is in."""
    up = stats.tv_distance(*UPPER_CLOUDS)
    lo = stats.tv_distance(*LOWER_CLOUDS)
    targets = np.array([up] * 10 + [lo] * 10 + [0.5] * 20)
    decoys = np.array([0.5] * 40)
    sel = fdr.select(targets, decoys, q=0.10)
    assert sel.n_discoveries == 20
    assert sel.threshold == round(5 / 6, fdr.SCORE_DECIMALS)
    flagged = fdr.discoveries(targets, sel)
    assert int(flagged.sum()) == 20 and flagged[:20].all() and not flagged[20:].any()


def test_stratified_flags_agree_with_each_stratum_selection_on_mixed_floats():
    up = stats.tv_distance(*UPPER_CLOUDS)
    lo = stats.tv_distance(*LOWER_CLOUDS)
    targets = np.array([up] * 15 + [lo] * 15 + [0.5] * 30 + [1.0] * 10 + [lo] * 10 + [0.5] * 20)
    decoys = np.array([0.5] * 60 + [lo] * 2 + [0.5] * 38)
    strata = ["prose"] * 60 + ["json"] * 40
    s = fdr.select_stratified(targets, decoys, strata, q=0.10, min_stratum=30)
    for name, sel in s.per_stratum.items():
        m = np.array(s.strata) == name
        assert int(s.flagged[m].sum()) == sel.n_discoveries, name
    assert s.per_stratum["prose"].n_discoveries == 30
    assert s.per_stratum["json"].n_discoveries == 10


def test_rounding_keeps_scores_that_differ_at_the_instrument_resolution():
    """Nine decimals merges float noise and nothing the channels can resolve:
    the NLI scores in the artifacts are stored at six."""
    x = np.array([0.240601, 0.240602, 0.2406010001])
    assert len(np.unique(fdr._scores(x))) == 2
    assert fdr.select(np.array([0.240602] * 12), np.array([0.240601] * 12), 0.10).n_discoveries == 12
