"""Induced structural conformance.

The two things that must work are the two mechanisms that answer Daikon's
over-generation problem: the decoy arm must knock down rules that held by
coincidence, and the middle band must catch rules the data cannot settle.
Everything else is a check that a rule kind fires on the fault class it was
written for.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime.conformance import (  # noqa: E402
    Rule,
    candidate_rules,
    check,
    induce,
    script_families,
)


def _json_outputs(n=20, status="approved", extra=None):
    out = []
    for i in range(n):
        obj = {"status": status, "amount": 100 + i, "note": "fine"}
        if extra:
            obj.update(extra)
        out.append(json.dumps(obj))
    return out


# ------------------------------------------------------------ the mechanisms ---


def test_decoy_arm_knocks_down_a_coincidental_rule():
    """The central claim. A rule fitted tightly to one sample of a system must
    not survive an independent re-run of the same system."""
    baseline = [f"answer number {i}." for i in range(10)]          # 3 words each
    decoy = [f"answer number {i}." for i in range(10)] + ["a considerably longer answer than any of the others seen so far."]

    alone = induce(baseline, None)
    with_decoy = induce(baseline, decoy)

    wc = [r for r in alone.hard if r.kind == "word_count_range"]
    assert wc, "a tight word-count range should be induced from the baseline alone"
    assert not [r for r in with_decoy.hard if r.kind == "word_count_range"], (
        "the decoy arm should have demoted the coincidental range"
    )
    assert any(r.kind == "word_count_range" for r, _ in with_decoy.pruned_by_decoy)


def test_a_genuine_invariant_survives_the_decoy():
    baseline = _json_outputs(15)
    decoy = _json_outputs(15)
    c = induce(baseline, decoy)
    kinds = {r.kind for r in c.hard}
    assert "parses_json" in kinds
    assert Rule("json_key_present", ("status",), "F3") in c.hard
    assert not c.pruned_by_decoy


def test_the_middle_band_catches_what_the_data_cannot_settle():
    """A rule true most of the time is neither an invariant nor noise. It is a
    question, and the band is where questions go."""
    baseline = ["ok."] * 17 + ["ok"] * 3          # 85% end with a terminator
    c = induce(baseline, baseline, hard_min=0.99, band_lo=0.60)
    banded = {r.kind for r, _, _ in c.band}
    assert "ends_with_terminator" in banded
    assert "ends_with_terminator" not in {r.kind for r in c.hard}


def test_rules_below_the_band_are_discarded_silently():
    baseline = ["ok."] * 5 + ["ok"] * 15          # 25% terminated
    c = induce(baseline, baseline)
    assert "ends_with_terminator" in {r.kind for r, _ in c.discarded}
    assert "ends_with_terminator" not in {r.kind for r, _, _ in c.band}


def test_only_hard_invariants_are_enforced():
    """Firing on band rules would reintroduce the over-generation the band
    exists to prevent."""
    baseline = ["ok."] * 17 + ["ok"] * 3
    c = induce(baseline, baseline)
    violations = check(c, ["ok"] * 10)
    assert not any(v.rule.kind == "ends_with_terminator" for v in violations)


# ------------------------------------------------------ rule kinds vs faults ---


def test_f3_json_becoming_unparseable_is_caught():
    c = induce(_json_outputs(15), _json_outputs(15))
    v = check(c, ['{"status": "approved",}'] * 10)
    assert any(x.rule.kind == "parses_json" for x in v)
    assert all(x.rate == 1.0 for x in v if x.rule.kind == "parses_json")


def test_f3_a_dropped_key_is_caught():
    c = induce(_json_outputs(15), _json_outputs(15))
    dropped = [json.dumps({"amount": 5, "note": "fine"}) for _ in range(10)]
    v = check(c, dropped)
    assert any(x.rule.kind == "json_key_present" and x.rule.params == ("status",) for x in v)


def test_f3_an_enum_leaving_its_domain_is_caught():
    base = _json_outputs(10, status="approved") + _json_outputs(10, status="declined")
    c = induce(base, list(base))
    assert Rule("json_enum", ("status", ("approved", "declined")), "F3") in c.hard
    v = check(c, _json_outputs(10, status="escalated"))
    assert any(x.rule.kind == "json_enum" for x in v)


def test_f7_script_corruption_is_caught_without_reading_the_text():
    """Thai characters in an English response -- the Anthropic TPU signature."""
    baseline = ["The request was approved on time."] * 15
    c = induce(baseline, list(baseline))
    assert any(r.kind == "script_subset" for r in c.hard)
    v = check(c, ["The request was สวัสดี approved."] * 10)
    assert any(x.rule.kind == "script_subset" for x in v)


def test_f7_literal_unicode_escapes_are_caught():
    """The OpenRouter FP4 signature: raw escapes instead of decoded glyphs."""
    baseline = ["Approved."] * 15
    c = induce(baseline, list(baseline))
    v = check(c, ["Approved \\uC548\\uB155."] * 10)
    assert any(x.rule.kind == "no_unicode_escape" for x in v)


def test_f12_mid_sentence_stop_is_caught():
    baseline = ["The claim was approved in full."] * 15
    c = induce(baseline, list(baseline))
    v = check(c, ["The claim was approved in"] * 10)
    assert any(x.rule.kind == "ends_with_terminator" for x in v)


def test_f13_refusal_drift_is_caught():
    baseline = ["The claim was approved."] * 15
    c = induce(baseline, list(baseline))
    v = check(c, ["I'm sorry, but I can't help with that."] * 10)
    assert any(x.rule.kind == "no_refusal_marker" for x in v)


def test_refusal_marker_does_not_fire_on_ordinary_hedging():
    """A broad refusal list would turn F13 into noise. This one is narrow."""
    hedged = "Based on the information available at the time of review, the claim was approved."
    assert Rule("no_refusal_marker").holds(hedged)
    assert Rule("no_refusal_marker").holds("I cannot confirm the amount without the invoice.")


# --------------------------------------------------------------- mechanics ---


def test_script_families_ignores_punctuation_and_digits():
    assert script_families("abc, 123!") == frozenset({"LATIN"})
    assert "THAI" in script_families("hello สวัส")


def test_only_keys_present_in_every_object_become_candidates():
    mixed = [json.dumps({"a": 1, "b": 2}), json.dumps({"a": 1})]
    kinds = {(r.kind, r.params) for r in candidate_rules(mixed)}
    assert ("json_key_present", ("a",)) in kinds
    assert ("json_key_present", ("b",)) not in kinds


def test_empty_baseline_induces_nothing():
    assert candidate_rules([]) == []
    assert induce([], []).n_candidates == 0


def test_summary_accounts_for_every_candidate():
    c = induce(_json_outputs(12), _json_outputs(12))
    assert c.n_candidates == len(c.hard) + len(c.band) + len(c.discarded)
    assert "hard" in c.summary()
