"""End-to-end detector.

Every other test exercises one piece. This is the first place the whole thing
runs as one machine, which is where composition bugs live: label spaces that do
not line up, strata computed from the wrong arm, a channel scored against the
wrong decoys.

Runs model-free throughout. The NLI and embedding channels are optional by
design, and the structured-output path — mode-share, dispersion, conformance —
needs no models at all, so the integration can be tested in milliseconds.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime import fdr  # noqa: E402
from aprime.detect import detect  # noqa: E402
from aprime.recorder import iter_invocations, record  # noqa: E402
from aprime.stub import build_arms  # noqa: E402

Q = 0.10


def _rec(n_inputs=120, n_affected=20, strength=0.9, seed=0, k=12):
    ids = [f"in{i:03d}" for i in range(n_inputs)]
    affected = set(random.Random(seed).sample(ids, n_affected)) if n_affected else set()
    a, ap, b = build_arms(ids, affected, "mode_share", strength=strength, seed=seed)
    rec = record(iter_invocations(ids), {"A": a, "A_prime": ap, "B": b}, k=k)
    return rec, affected


# --------------------------------------------------------------- happy path ---


def test_detector_finds_injected_changes():
    rec, affected = _rec()
    rep = detect(rec, q=Q)
    assert rep.n_inputs == 120
    found = {f.input_id for f in rep.findings}
    assert found, "nothing flagged on a system with 20 genuinely changed inputs"
    hit = len(found & affected) / len(affected)
    assert hit > 0.4, f"recall {hit:.2f}"


def test_detector_stays_quiet_on_an_unchanged_system():
    """B is behaviourally identical to A. Anything flagged is a false alarm."""
    rec, _ = _rec(n_inputs=120, n_affected=0, strength=0.0, seed=3)
    rep = detect(rec, q=Q)
    assert rep.n_flagged <= 8, rep.text()


def test_end_to_end_fdr_is_controlled():
    realised = []
    for seed in range(3):
        rec, affected = _rec(n_inputs=200, n_affected=30, strength=0.9, seed=10 + seed)
        rep = detect(rec, q=Q)
        flagged = {f.input_id for f in rep.findings}
        if flagged:
            realised.append(len(flagged - affected) / len(flagged))
    assert realised, "no run produced any discovery"
    assert float(np.mean(realised)) <= 0.35, realised


# ------------------------------------------------------------- composition ---


def test_channels_report_separately_and_do_not_vote():
    """Combining channels would need weights, weights would be fitted, and
    fitting them outside a LOSO fold is what MTH-009 forbids."""
    rec, _ = _rec()
    rep = detect(rec, q=Q)
    assert {"mode_share", "dispersion", "novel_mode"} <= set(rep.channels)
    for f in rep.findings:
        assert f.channels, "a finding must name the channel that produced it"
        assert set(f.channels) <= set(rep.channels)


def test_model_backed_channels_are_skipped_with_a_reason_not_silently():
    rec, _ = _rec(n_inputs=30, n_affected=5)
    rep = detect(rec, q=Q)
    for name in ("nli_contradiction", "nli_directional", "embedding"):
        assert rep.channels[name].skipped
        assert rep.channels[name].n_flagged == 0
    assert "skipped" in rep.text()


def test_strata_come_from_the_baseline_and_appear_in_findings():
    rec, _ = _rec()
    rep = detect(rec, q=Q)
    for f in rep.findings:
        assert f.stratum in {"json", "list", "short", "prose"}


def test_conformance_runs_over_the_pooled_corpus():
    rec, _ = _rec(n_inputs=40, n_affected=0, strength=0.0, seed=5)
    rep = detect(rec, q=Q)
    assert rep.contract is not None
    assert rep.contract.n_candidates > 0
    assert "conformance" in rep.text()


def test_a_structural_break_in_the_candidate_is_caught():
    """The conformance channel has to see what the semantic channels cannot."""
    ids = [f"i{n}" for n in range(30)]
    a, ap, b = build_arms(ids, set())
    rec = record(iter_invocations(ids), {"A": a, "A_prime": ap, "B": b}, k=6)
    # Corrupt every B output with a wrong-script insertion: the F7 signature.
    rec.samples = [
        type(s)(**{**s.__dict__,
                   "output": s.output + " สวัส" if s.arm == "B" else s.output})
        for s in rec.samples
    ]
    rep = detect(rec, q=Q)
    assert any(v.rule.kind == "script_subset" for v in rep.violations), rep.text()


def test_a_run_crossing_midnight_is_called_out_in_the_report():
    rec, _ = _rec(n_inputs=10, n_affected=0)
    day = 86400
    base = (rec.samples[0].ts // day) * day
    rec.samples = [
        type(s)(**{**s.__dict__, "ts": base - 5 if i % 2 else base + 5})
        for i, s in enumerate(rec.samples)
    ]
    rep = detect(rec, q=Q)
    assert any("midnight" in n for n in rep.notes), rep.notes


def test_inputs_missing_an_arm_are_dropped_not_imputed():
    """A missing arm has no decoy and therefore no calibrated threshold."""
    rec, _ = _rec(n_inputs=40, n_affected=0)
    rec.samples = [s for s in rec.samples if not (s.input_id == "in000" and s.arm == "A_prime")]
    rep = detect(rec, q=Q)
    assert rep.n_inputs == 39
    assert any("dropped" in n for n in rep.notes)
    assert "in000" not in {f.input_id for f in rep.findings}


def test_report_renders_without_findings():
    rec, _ = _rec(n_inputs=20, n_affected=0, strength=0.0, seed=9)
    rep = detect(rec, q=Q)
    txt = rep.text()
    assert "a-prime report" in txt and "channels:" in txt


def test_a_tighter_budget_never_yields_more_findings():
    rec, _ = _rec()
    loose = detect(rec, q=0.20).n_flagged
    tight = detect(rec, q=0.02).n_flagged
    assert tight <= loose, f"q=0.02 gave {tight}, q=0.20 gave {loose}"
