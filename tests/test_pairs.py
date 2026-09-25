"""Construction tests for the probe suite.

These guard the suite against the failure mode that would quietly invalidate
every downstream number: a pair that does not actually contain the difference
it claims to contain. A blind channel and a broken probe look identical in the
results table, so the probes have to be checked independently.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime.probes import analysis, pairs, seeds  # noqa: E402


def test_every_seed_satisfies_the_field_contract():
    for s in seeds.SEEDS:
        missing = set(seeds.REQUIRED_FIELDS) - set(s.fields)
        assert not missing, f"{s.id} missing {missing}"


def test_alt_fields_actually_differ():
    for s in seeds.SEEDS:
        for key in ("subject", "number", "unit", "verdict", "quantifier", "date", "detail1"):
            assert s.fields[key] != s.fields[f"{key}_alt"], f"{s.id}.{key}"


def test_no_degenerate_pairs():
    """A pair whose arms are byte-identical measures nothing."""
    bad = pairs.degenerate(pairs.build_pairs())
    assert not bad, [f"{p.seed_id}/{p.shape}/{p.category}" for p in bad[:10]]


def test_factorial_is_complete():
    ps = pairs.build_pairs()
    n_cat = len(pairs.ALL_BUILDERS)
    assert len(ps) == len(seeds.SEEDS) * len(pairs.SHAPES) * n_cat
    counts = {}
    for p in ps:
        counts[(p.shape, p.category)] = counts.get((p.shape, p.category), 0) + 1
    assert set(counts.values()) == {len(seeds.SEEDS)}


def test_breaking_pairs_change_substance_not_only_surface():
    """Every breaking pair must differ in a content token, not just wording.

    `omission` is exempt in the sense that it removes rather than substitutes;
    it is checked separately below.
    """
    for p in pairs.build_pairs():
        if p.relation != "BREAKING" or p.category == "omission":
            continue
        assert p.text_a != p.text_b, f"{p.seed_id}/{p.shape}/{p.category}"


def test_omission_strictly_removes_the_caveat():
    for seed in seeds.SEEDS:
        for shape in pairs.SHAPES:
            a, b = pairs.BREAKING["omission"](shape, seed.fields)
            caveat = seed.fields["caveat"]
            assert caveat in a, f"{seed.id}/{shape}: caveat absent from arm A"
            assert caveat not in b, f"{seed.id}/{shape}: caveat survived omission"
            assert len(b) < len(a)


def test_preserving_and_register_pairs_keep_every_content_field():
    """A preserving perturbation that drops or alters a fact is mislabelled, and
    would show up in the results as the channel being oversensitive.

    REGISTER is checked by the same rule: its whole definition is that the facts
    are identical and only stance moved. A register pair that lost a fact would
    be a breaking pair wearing the wrong label.
    """
    builders = {**pairs.PRESERVING, **pairs.REGISTER}
    for seed in seeds.SEEDS:
        for shape in pairs.SHAPES:
            for name in builders:
                a, b = builders[name](shape, seed.fields)
                for key in ("subject", "number", "verdict", "date"):
                    val = seed.fields[key]
                    if val not in a:
                        continue  # shape may not surface that field
                    if name == "synonym" and val in pairs.SYNONYMS:
                        continue
                    assert val in b, f"{seed.id}/{shape}/{name}: lost {key}"


def test_synonym_actually_substitutes_something():
    for seed in seeds.SEEDS:
        for shape in pairs.SHAPES:
            a, b = pairs.PRESERVING["synonym"](shape, seed.fields)
            assert a != b, f"{seed.id}/{shape}: synonym pass was a no-op"


def test_register_is_its_own_relation_and_is_not_counted_as_either():
    """F9 (persona/sycophancy drift) is a real fault class, so calling stance
    change 'preserving' would label a documented fault a non-event. But the
    facts are identical, so calling it 'breaking' makes that bucket
    inhomogeneous. It is measured separately instead."""
    ps = pairs.build_pairs()
    rels = {p.relation for p in ps}
    assert rels == {"PRESERVING", "BREAKING", "REGISTER"}
    reg = [p for p in ps if p.relation == "REGISTER"]
    assert {p.category for p in reg} == {"hedging", "overconfidence"}
    assert len(reg) == len(seeds.SEEDS) * len(pairs.SHAPES) * 2
    assert not (set(pairs.REGISTER) & set(pairs.PRESERVING))
    assert not (set(pairs.REGISTER) & set(pairs.BREAKING))


def test_the_two_register_directions_differ_from_each_other():
    """Hedging and overconfidence are opposite stance moves, not one
    perturbation applied twice."""
    for seed in seeds.SEEDS[:4]:
        for shape in pairs.SHAPES:
            _, hedged = pairs.REGISTER["hedging"](shape, seed.fields)
            _, boosted = pairs.REGISTER["overconfidence"](shape, seed.fields)
            assert hedged != boosted, f"{seed.id}/{shape}"


def test_shapes_span_a_real_length_range():
    """Length is a factor in the design; if the shapes are all the same size
    the suite cannot separate 'blind to meaning' from 'diluted by length'."""
    ps = pairs.build_pairs()
    med = {}
    for shape in pairs.SHAPES:
        wc = [p.words_a for p in ps if p.shape == shape]
        med[shape] = float(np.median(wc))
    assert max(med.values()) / min(med.values()) >= 2.0, med


# --------------------------------------------------------------- analysis ---


def test_wilson_matches_known_values():
    lo, hi = analysis.wilson(24, 30)
    assert lo == pytest.approx(0.634, abs=0.01)
    assert hi == pytest.approx(0.896, abs=0.01)


def test_auc_is_half_for_identical_populations():
    x = np.arange(50, dtype=float)
    assert analysis.auc(x, x.copy()) == pytest.approx(0.5, abs=1e-9)


def test_auc_is_one_for_separated_populations():
    assert analysis.auc(np.arange(10, 20.0), np.arange(0, 10.0)) == pytest.approx(1.0)


def test_threshold_respects_the_fpr_budget():
    rng = np.random.default_rng(0)
    pres = rng.normal(size=2000)
    thr = analysis.threshold_at_fpr(pres, 0.05)
    assert (pres > thr).mean() == pytest.approx(0.05, abs=0.01)
