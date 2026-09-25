"""Normalisation and mode clustering.

Both are pure functions over text, so they are tested without any model. The
model-dependent part — where the equivalence threshold sits — is fitted against
the probe suite by `scripts/fit_clustering.py`, not asserted here.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime import stats  # noqa: E402
from aprime.clustering import (  # noqa: E402
    ExactEquivalence,
    cluster,
    cluster_jointly,
)
from aprime.normalize import (  # noqa: E402
    as_sentences,
    is_probably_json,
    normalise,
    normalise_json,
    normalise_text,
)


# -------------------------------------------------------------- normalise ---


def test_bullets_and_prose_normalise_to_the_same_thing():
    """The 19% false-alarm source on both NLI channels."""
    prose = "The claim was approved. Payment follows in March."
    bullets = "- The claim was approved.\n- Payment follows in March."
    numbered = "1. The claim was approved.\n2. Payment follows in March."
    assert normalise_text(prose).replace("\n", " ") == normalise_text(bullets).replace("\n", " ")
    assert normalise_text(bullets) == normalise_text(numbered)


def test_markdown_emphasis_and_headings_are_stripped():
    assert normalise_text("## Result\n**Approved** for _March_") == "Result\nApproved for March"


def test_curly_punctuation_is_unified():
    assert normalise_text("it’s “fine” — really") == normalise_text(
        'it\'s "fine" - really'
    )


def test_content_words_survive_normalisation():
    """The line that must hold: presentation goes, content stays."""
    t = "- Approved for 42,000 USD on 3 March 2026, not 47,000."
    out = normalise_text(t)
    for token in ("Approved", "42,000", "USD", "3 March 2026", "not", "47,000"):
        assert token in out, token


def test_json_key_order_and_whitespace_stop_mattering():
    a = '{"b": 2, "a": 1}'
    b = '{\n  "a": 1,\n  "b": 2\n}'
    assert normalise_json(a) == normalise_json(b)
    assert normalise(a) == normalise(b)


def test_broken_json_is_not_silently_repaired():
    """An output that stopped parsing is a real regression (F3). Falling back to
    text normalisation would hide it from the structural channel."""
    assert normalise_json('{"a": 1,}') is None
    assert not is_probably_json('{"a": 1,}')
    assert normalise('{"a": 1,}') == normalise_text('{"a": 1,}')


def test_sentence_split_survives_bullets():
    assert as_sentences("- One thing.\n- Two things. Three things.") == [
        "One thing.",
        "Two things.",
        "Three things.",
    ]


# --------------------------------------------------------------- clustering ---


def test_exact_clustering_collapses_presentation_variants():
    samples = [
        "The claim was approved.",
        "- The claim was approved.",
        "**The claim was approved.**",
        "The claim was declined.",
    ]
    r = cluster(samples)
    assert r.labels[:3] == [0, 0, 0]
    assert r.labels[3] != 0
    assert r.distinct_after_normalisation == 2
    assert r.collapse_ratio == 0.5


def test_partition_is_independent_of_sample_order():
    """The equivalence relation is not transitive, so order-dependence would be
    a genuine reproducibility problem. Deterministic ordering is the fix."""
    a = ["x", "y", "y", "z", "y", "x"]
    b = ["y", "x", "z", "y", "x", "y"]
    ra, rb = cluster(a), cluster(b)
    assert ra.representatives == rb.representatives


def test_most_frequent_mode_becomes_representative_zero():
    r = cluster(["b", "a", "a", "a", "b"])
    assert r.representatives[0] == "a"


def test_joint_clustering_shares_one_label_space():
    """Clustering clouds separately would give two unrelated label spaces and
    make mode-share distance meaningless."""
    a = ["yes"] * 7 + ["no"] * 3
    b = ["- yes"] * 2 + ["no"] * 8
    ma, mb, joint = cluster_jointly(a, b)
    assert set(ma) | set(mb) == set(joint.as_modes())
    assert stats.tv_distance(ma, mb) == pytest.approx(0.5)


def test_without_normalisation_presentation_looks_like_change():
    """The negative control: this is what the detector saw before D4."""
    a = ["The claim was approved."] * 10
    b = ["- The claim was approved."] * 10
    ma, mb, _ = cluster_jointly(a, b)
    assert stats.tv_distance(ma, mb) == 0.0
    raw = cluster(list(a) + list(b), normalise_first=False)
    modes = raw.as_modes()
    assert stats.tv_distance(modes[:10], modes[10:]) == 1.0


def test_predicate_calls_are_counted():
    """This number is the justification for distilling the predicate later, so
    it is measured rather than asserted."""
    samples = ["a", "b", "c", "a", "b"]
    r = cluster(samples, ExactEquivalence())
    assert r.distinct_after_normalisation == 3
    # First distinct seeds cluster 0 free; second compares to 1 rep; third to 2.
    assert r.predicate_calls == 3


def test_a_merging_predicate_reduces_mode_count():
    class MergeAll:
        def equivalent(self, pairs):
            return [True] * len(pairs)

    r = cluster(["a", "b", "c"], MergeAll())
    assert len(r.representatives) == 1
    assert set(r.labels) == {0}


def test_empty_cloud_is_handled():
    r = cluster([])
    assert r.labels == [] and r.shares() == {}
