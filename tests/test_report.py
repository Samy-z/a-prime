"""The report, read by someone who did not write the detector.

`0 flagged` is one sentence for three situations: nothing changed, the change
separated cleanly but fewer than 1/q inputs cleared the bar (MTH-024), or a
check cannot see this kind of change (ENG-007). The report has to say which,
in words, next to every check. Model-free throughout.
"""

from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime import fdr  # noqa: E402
from aprime.detect import (  # noqa: E402
    CHANNEL_LABELS,
    Finding,
    _floor,
    _read_stratum,
    detect,
)
from aprime.recorder import iter_invocations, record  # noqa: E402
from aprime.stub import build_arms  # noqa: E402

Q = 0.10


def _rec(n_inputs: int, n_affected: int, k: int = 12, strength: float = 0.9,
         seed: int = 7):
    ids = [f"in{i:03d}" for i in range(n_inputs)]
    affected = set(ids[:n_affected])
    a, ap, b = build_arms(ids, affected, "mode_share", strength=strength, seed=seed)
    rec = record(iter_invocations(ids), {"A": a, "A_prime": ap, "B": b}, k=k)
    return rec, affected


# --- the three readings, on synthetic numbers -------------------------------

def _sel(n: int, thr: float = 0.5, fdr_hat: float = 0.05) -> fdr.Selection:
    return fdr.Selection(threshold=thr, n_discoveries=n, fdr_hat=fdr_hat, q=Q)


def test_floor_is_one_over_q():
    assert _floor(0.10) == 10
    assert _floor(0.05) == 20
    assert _floor(0.20) == 5


def test_reading_under_the_floor_says_how_many_more_were_needed():
    """ENG-007: nine above zero decoys, one short of ten."""
    best = fdr.BestCut(estimate=1 / 9, cut=1.0, targets_above=9, decoys_above=0)
    txt = _read_stratum(_sel(0, float("inf"), float("nan")), best, Q)
    assert "9 input(s) sit above every baseline" in txt
    assert "floor of 10" in txt and "1 more" in txt


def test_reading_with_no_separation_says_it_cannot_tell_blind_from_unchanged():
    """ENG-007: dispersion, 15 targets against 12 decoys, estimate 0.867."""
    best = fdr.BestCut(estimate=13 / 15, cut=0.1, targets_above=15, decoys_above=12)
    txt = _read_stratum(_sel(0, float("inf"), float("nan")), best, Q)
    assert txt.startswith("no separation")
    assert "cannot tell those apart" in txt


def test_reading_partly_separated_names_the_counts():
    best = fdr.BestCut(estimate=0.3, cut=0.4, targets_above=10, decoys_above=2)
    txt = _read_stratum(_sel(0, float("inf"), float("nan")), best, Q)
    assert txt.startswith("partly separated")
    assert "10 input(s) above against 2 baseline" in txt


def test_reading_with_findings_gives_threshold_and_estimate():
    best = fdr.BestCut(estimate=0.05, cut=0.6, targets_above=20, decoys_above=0)
    txt = _read_stratum(_sel(20, 0.583, 0.07), best, Q)
    assert "20 flagged above 0.583" in txt and "0.07" in txt


# --- best_achievable agrees with the selection -------------------------------

def test_best_achievable_matches_select_when_a_cut_qualifies():
    rng = np.random.default_rng(1)
    decoys = rng.uniform(0, 0.3, 50)
    targets = np.concatenate([rng.uniform(0, 0.3, 30), rng.uniform(0.6, 1.0, 20)])
    best = fdr.best_achievable(targets, decoys)
    sel = fdr.select(targets, decoys, Q)
    assert best is not None and best.separated
    assert best.estimate <= sel.fdr_hat <= Q


def test_best_achievable_is_none_without_targets():
    assert fdr.best_achievable(np.empty(0), np.empty(0)) is None


# --- the report on a real (stub) run ------------------------------------------

def test_a_run_under_the_floor_reports_nothing_and_explains_why():
    """Five genuinely changed inputs at q=0.10: separated, and unreportable."""
    rec, affected = _rec(n_inputs=60, n_affected=5)
    rep = detect(rec, q=Q)
    txt = rep.text()
    assert rep.n_flagged == 0
    assert "0 of 60 inputs flagged" in txt
    assert "at least 10 inputs (1/q)" in txt
    assert "Closest:" in txt
    # The closest check saw the change: some targets above every decoy.
    name, best = rep.closest_check()
    assert best.separated and best.targets_above >= 1
    assert "under the floor of 10" in rep.channels[name].reading(Q)


def test_a_run_over_the_floor_lists_findings_with_plain_labels():
    rec, affected = _rec(n_inputs=300, n_affected=30)
    rep = detect(rec, q=Q)
    txt = rep.text()
    assert rep.n_flagged >= 10
    assert "flagged inputs" in txt
    assert "answer mix" in txt  # the plain label for mode_share
    assert "mode_share (answer mix)" in txt  # and the key, for grepping
    assert "estimated false-discovery rate" in txt


def test_checks_that_could_not_run_say_skipped_with_the_reason():
    rec, _ = _rec(n_inputs=40, n_affected=0)
    txt = detect(rec, q=Q).text()
    assert "skipped: no NLI model supplied" in txt
    assert "skipped: no embedder supplied" in txt


def test_checks_are_listed_in_a_fixed_order_not_alphabetically():
    rec, _ = _rec(n_inputs=40, n_affected=0)
    txt = detect(rec, q=Q).text()
    order = [txt.index(f"  {name} (") for name in CHANNEL_LABELS]
    assert order == sorted(order)


def test_header_states_inputs_samples_and_budget():
    rec, _ = _rec(n_inputs=40, n_affected=0, k=8)
    rep = detect(rec, q=Q)
    txt = rep.text()
    assert rep.k == 8
    assert "40 inputs compared, 8 samples per input" in txt
    assert "q=0.1" in txt and "10%" in txt


def test_short_clouds_are_counted_and_stated():
    rec, _ = _rec(n_inputs=40, n_affected=0, k=8)
    # One failed call on one arm of one input: that cloud has 7, not 8.
    i = next(j for j, s in enumerate(rec.samples)
             if s.input_id == "in003" and s.arm == "A_prime")
    rec.samples[i] = dataclasses.replace(rec.samples[i], error="boom", output="")
    rep = detect(rec, q=Q)
    assert rep.short_clouds == 1
    assert "1 of 40 inputs had fewer than 8 usable samples" in rep.text()


def test_provenance_is_printed_when_set_and_absent_otherwise():
    rec, _ = _rec(n_inputs=40, n_affected=0)
    rep = detect(rec, q=Q)
    assert "run " not in rep.text().splitlines()[1]
    rep.provenance = {"run_id": "20261004T120000Z", "config_hash": "abcd1234abcd1234",
                      "git_commit": "0123456789abcdef", "git_dirty": True}
    line = rep.text().splitlines()[1]
    assert "run 20261004T120000Z" in line and "git 01234567" in line
    assert "uncommitted" in line


def test_rules_section_is_marked_as_outside_the_floor():
    rec, _ = _rec(n_inputs=40, n_affected=0)
    txt = detect(rec, q=Q).text()
    assert "rules inferred from the old system" in txt
    assert "not subject to the floor" in txt


def test_directional_finding_names_the_direction():
    less = str(Finding("in001", "short", {"nli_directional": 0.4}))
    more = str(Finding("in001", "short", {"nli_directional": -0.4}))
    assert "new output says less" in less
    assert "new output says more" in more


def test_to_dict_is_json_safe_and_carries_the_readings():
    rec, _ = _rec(n_inputs=60, n_affected=5)
    rep = detect(rec, q=Q)
    rep.provenance = {"run_id": "r", "config_hash": "c", "git_commit": "g",
                      "git_dirty": False}
    d = rep.to_dict()
    json.dumps(d)  # must not raise
    assert d["floor"] == 10 and d["k"] == 12 and d["n_inputs"] == 60
    assert d["provenance"]["run_id"] == "r"
    assert set(d["channels"]) == set(rep.channels)
    ms = d["channels"]["mode_share"]
    assert "reading" in ms and "best" in ms and "thresholds" in ms
    assert d["rules"]["candidates"] == rep.contract.n_candidates
    assert d["channels"]["embedding"]["skipped"]
