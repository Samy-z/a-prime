"""Design R's pairing layer over a synthetic four-arm roster recording.

Exact-match clustering, no models: enough to pin the relabelling, which
pairing selects in each regime, the orientation diagnostic, and that the
cross-pooled estimate is computed under its own name and never feeds a
selection.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.pairings import DesignRSuite, design_r, pair_recording  # noqa: E402
from aprime.recorder import Recording, Sample  # noqa: E402

Q = 0.5  # floor of 2, so a six-input cell can flag without 10 inputs


def _rec(changed=("i0", "i1", "i2", "i3"), quiet=("i4", "i5"), k=2):
    """Four arms over six inputs. Baseline says x everywhere; the candidate
    pair says y on the changed inputs. Exact-match clustering makes the
    mode-share target 1.0 there and every decoy 0.0."""
    ids = list(changed) + list(quiet)
    samples = []
    order = 0
    for iid in ids:
        for idx in range(k):
            for arm in ("A", "A_prime", "B", "B_prime"):
                out = "y" if (arm in ("B", "B_prime") and iid in changed) else "x"
                samples.append(Sample(input_id=iid, arm=arm, sample_idx=idx,
                                      order=order, output=out, latency_ms=1.0,
                                      ts=1000.0 + order))
                order += 1
    return Recording(samples=samples, k=k, input_ids=ids)


def test_pair_recording_relabels_and_drops():
    rec = _rec()
    pair = pair_recording(rec, "B", "B_prime", "A")
    assert {s.arm for s in pair.samples} == {"A", "A_prime", "B"}
    assert pair.clouds("A")["i0"] == ["y", "y"]      # B relabelled to A
    assert pair.clouds("B")["i0"] == ["x", "x"]      # A relabelled to B
    assert pair.input_ids == rec.input_ids


def test_interleaved_regime_selects_on_the_reference():
    suite = design_r(_rec(), q=Q)
    assert isinstance(suite, DesignRSuite)
    assert suite.selects_on == "reference"
    flagged = {f.input_id for f in suite.primary.findings}
    assert flagged == {"i0", "i1", "i2", "i3"}
    # The mirrored view agrees on this symmetric construction.
    assert suite.orientation == {"primary_only": [], "reverse_only": [],
                                 "both": ["i0", "i1", "i2", "i3"]}
    assert set(suite.replicates) == {"s(A,B') vs s(A,A')",
                                     "s(A',B) vs s(A',A)",
                                     "s(A',B') vs s(A',A)"}
    assert suite.primary.input_order, "reports must carry their input order"


def test_cross_pooled_reports_and_never_selects():
    suite = design_r(_rec(), q=Q)
    assert suite.cross_pooled is not None
    ms = suite.cross_pooled["mode_share"]
    assert ms["selects"] is False and ms["r"] == 2
    assert ms["would_flag"] == 4
    assert ms["estimate"] is not None and ms["estimate"] <= Q


def test_stored_baseline_regime_selects_on_the_candidate_pair():
    suite = design_r(_rec(), q=Q, stored_baseline=True)
    assert suite.selects_on == "candidate"
    assert {f.input_id for f in suite.primary.findings} == {"i0", "i1", "i2", "i3"}
    assert any("reported" in k for k in suite.replicates), \
        "s(A,A') must be reported alongside when the stored pair exists"
    assert suite.reverse is None


def test_missing_candidate_prime_degrades_loudly():
    rec = _rec()
    rec = Recording(samples=[s for s in rec.samples if s.arm != "B_prime"],
                    k=rec.k, input_ids=rec.input_ids)
    suite = design_r(rec, q=Q)
    assert suite.reverse is None and suite.cross_pooled is None
    assert not suite.replicates
    assert any("B_prime" in n for n in suite.notes)


def test_missing_required_arm_raises():
    rec = _rec()
    rec = Recording(samples=[s for s in rec.samples if s.arm != "A_prime"],
                    k=rec.k, input_ids=rec.input_ids)
    with pytest.raises(ValueError, match="needs arms"):
        design_r(rec, q=Q)


def test_suite_to_dict_is_json_shaped():
    import json

    suite = design_r(_rec(), q=Q)
    blob = json.dumps(suite.to_dict())
    assert "cross_pooled" in blob and "orientation" in blob
