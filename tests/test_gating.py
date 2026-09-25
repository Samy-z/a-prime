"""Surface-drift gating, shape inference, and stratified selection."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime import fdr  # noqa: E402
from aprime.gating import (  # noqa: E402
    embedding_gate,
    infer_shape,
    shape_of_cloud,
    strata_from_baseline,
    surface_drift,
)


# ------------------------------------------------------------ surface drift ---


def test_identical_wording_has_no_drift():
    c = ["the claim was approved in march"] * 5
    assert surface_drift(c, list(c)) == 0.0


def test_reformatting_alone_has_no_drift():
    """Drift must measure wording, not presentation -- normalisation already
    handles presentation and double-counting it would gate the channel off for
    the wrong reason."""
    prose = ["The claim was approved. Payment follows."] * 4
    bullets = ["- The claim was approved.\n- Payment follows."] * 4
    assert surface_drift(prose, bullets) == pytest.approx(0.0, abs=1e-9)


def test_a_one_phrase_swap_drifts_less_than_a_full_rewrite():
    """This ordering is the whole basis of the gate: embeddings survive the
    first regime and fail in the second (MTH-012)."""
    base = ["the debt to income ratio sits within policy limits"] * 4
    synonym = ["the debt to income ratio falls within policy limits"] * 4
    rewrite = ["policy limits are respected by this applicant's leverage"] * 4
    assert surface_drift(base, synonym) < surface_drift(base, rewrite)


def test_disjoint_vocabulary_is_maximal_drift():
    assert surface_drift(["alpha beta"], ["gamma delta"]) == pytest.approx(1.0)


def test_gate_blocks_the_regime_where_the_channel_is_worse_than_chance():
    base = ["the claim was approved in march for forty two thousand"] * 4
    rewrite = ["authorisation granted; disbursement scheduled next quarter"] * 4
    v = embedding_gate(base, rewrite, threshold=0.25)
    assert not v.allowed
    assert "anti-correlated" in v.reason


def test_gate_allows_a_stable_surface():
    base = ["the claim was approved in march"] * 4
    near = ["the claim was approved in march"] * 3 + ["the claim was approved during march"]
    v = embedding_gate(base, near, threshold=0.25)
    assert v.allowed and v.drift <= 0.25


# -------------------------------------------------------------------- shape ---


def test_shapes_are_inferred_from_structure_alone():
    assert infer_shape(json.dumps({"a": 1})) == "json"
    assert infer_shape("- one\n- two\n- three") == "list"
    assert infer_shape("Approved.") == "short"
    assert infer_shape(" ".join(["word"] * 200)) == "prose"


def test_empty_output_does_not_crash_shape_inference():
    assert infer_shape("") == "short"
    assert shape_of_cloud([]) == "short"


def test_a_single_list_marker_is_not_a_list():
    """One hyphen in a sentence should not reshape the output."""
    assert infer_shape("The claim - which was late - was approved.") == "short"


def test_stratum_comes_from_the_baseline_not_the_candidate():
    """MTH-004: a candidate that changed shape must not select its own stratum,
    or the change hides inside a threshold chosen to accommodate it."""
    clouds_a = {"i1": ["Approved."] * 5, "i2": [" ".join(["w"] * 200)] * 5}
    strata = strata_from_baseline(clouds_a)
    assert strata == {"i1": "short", "i2": "prose"}


def test_shape_of_cloud_takes_the_mode_not_the_first():
    cloud = [json.dumps({"a": 1})] + ["Approved."] * 4
    assert shape_of_cloud(cloud) == "short"


# ------------------------------------------------------- stratified select ---


def test_stratified_selection_uses_a_threshold_per_stratum():
    """Two strata on different scales. A pooled threshold would over-flag the
    tight one and go blind in the wide one."""
    rng = np.random.default_rng(0)
    n = 200
    tight_d = rng.normal(0, 0.01, n)
    tight_t = np.concatenate([rng.normal(0, 0.01, n - 20), rng.normal(0.2, 0.01, 20)])
    wide_d = rng.normal(0, 1.0, n)
    wide_t = np.concatenate([rng.normal(0, 1.0, n - 20), rng.normal(20, 1.0, 20)])

    targets = np.concatenate([tight_t, wide_t])
    decoys = np.concatenate([tight_d, wide_d])
    strata = ["tight"] * n + ["wide"] * n

    s = fdr.select_stratified(targets, decoys, strata, q=0.10)
    assert set(s.per_stratum) == {"tight", "wide"}
    assert s.per_stratum["tight"].threshold < s.per_stratum["wide"].threshold
    assert s.per_stratum["tight"].n_discoveries > 0
    assert s.per_stratum["wide"].n_discoveries > 0

    pooled = fdr.select(targets, decoys, q=0.10)
    assert s.n_discoveries >= pooled.n_discoveries, (
        "stratifying should not lose discoveries when the strata differ in scale"
    )


def test_small_strata_are_pooled_rather_than_given_a_guessed_threshold():
    rng = np.random.default_rng(1)
    targets = rng.normal(size=100)
    decoys = rng.normal(size=100)
    strata = ["big"] * 90 + ["tiny"] * 10
    s = fdr.select_stratified(targets, decoys, strata, q=0.10, min_stratum=30)
    assert "tiny" not in s.per_stratum
    assert "__pooled__" in s.per_stratum


def test_mismatched_lengths_are_rejected():
    with pytest.raises(ValueError, match="same length"):
        fdr.select_stratified(np.zeros(3), np.zeros(3), ["a", "b"], q=0.1)
