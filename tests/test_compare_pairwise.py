"""The pairwise runner's pure logic: rotation, tuple-atomic resume, and the
Design R pairings. No model, no network — the recording loop itself is
exercised live, these pin the parts a resume or a relabel depends on."""

from __future__ import annotations

import importlib.util
from pathlib import Path

COMPARE = Path(__file__).resolve().parents[1] / "compare"

spec = importlib.util.spec_from_file_location(
    "pairwise_ventes", COMPARE / "pairwise_ventes.py")
pv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pv)


def _row(iid, arm, s_idx, output="texte", error=None):
    return {"input_id": iid, "arm": arm, "sample_idx": s_idx,
            "output": output, "error": error}


def test_arm_order_rotates_over_the_roster():
    assert pv.arm_order(0) == ["m1a", "m1b", "m2a", "m2b"]
    assert pv.arm_order(1) == ["m1b", "m2a", "m2b", "m1a"]
    assert pv.arm_order(4) == pv.arm_order(0)
    for g in range(8):
        assert sorted(pv.arm_order(g)) == sorted(pv.ROSTER)


def test_resume_is_tuple_atomic():
    rows = (
        # complete tuple: survives
        [_row("i1", a, 0) for a in pv.ROSTER]
        # partial tuple (one arm missing): re-recorded whole
        + [_row("i1", a, 1) for a in pv.ROSTER[:3]]
        # complete but one arm errored: not complete
        + [_row("i2", a, 0) for a in pv.ROSTER[:3]]
        + [_row("i2", "m2b", 0, error="boom")]
        # complete but one arm empty: not complete
        + [_row("i2", a, 1) for a in pv.ROSTER[:3]]
        + [_row("i2", "m2b", 1, output="")]
    )
    assert pv.complete_tuples(rows) == {("i1", 0)}
    todo = pv.plan_remaining(rows, ["i1", "i2"], k=2)
    assert todo == [(1, "i1", 1), (2, "i2", 0), (3, "i2", 1)]
    # the global index is positional, so rotation never depends on when a
    # tuple was recorded
    assert pv.plan_remaining([], ["i1", "i2"], k=2)[0] == (0, "i1", 0)
    assert pv.compact(rows) == rows[:4]


def test_pairings_are_design_r_shaped():
    for name, mapping in pv.PAIRINGS.items():
        # exactly the three roles the engine's detect() reads
        assert sorted(mapping.values()) == ["A", "A_prime", "B"]
        roles = {v: k for k, v in mapping.items()}
        # the decoy pair is within one model (s(A, A') is a self pair)...
        assert roles["A"][:2] == roles["A_prime"][:2]
        # ...and the target pair crosses models
        assert roles["A"][:2] != roles["B"][:2]
    # the declared reference anchors the selection
    assert pv.PAIRINGS["primary"]["m1a"] == "A"
    assert pv.REFERENCE[1] == "llama3.2:3b"
    # the primary + three replicates cover the four cross pairs exactly once
    cross = {(r["A"], r["B"]) for r in
             ({v: k for k, v in pv.PAIRINGS[n].items()}
              for n in ("primary", "rep-AB2", "rep-A2B", "rep-A2B2"))}
    assert cross == {("m1a", "m2a"), ("m1a", "m2b"),
                     ("m1b", "m2a"), ("m1b", "m2b")}
