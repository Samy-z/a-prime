"""The library's r > 1 selector against the instrument it must mirror.

The MTH-027 third append adopted the Emery max-method exactly as block 8 of
`scripts/simulate_null_designs.py` implements it, and every all-null figure
that row measured belongs to the LIBRARY selector only if the two never
disagree. These tests pin that equivalence, the tie rule, the floor, and the
non-conflation with the frozen r = 1 pooled rule.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.fdr import (  # noqa: E402
    competition_wins,
    select,
    select_competition,
    select_competition_stratified,
)


def _sim():
    spec = importlib.util.spec_from_file_location(
        "simulate_null_designs", ROOT / "scripts" / "simulate_null_designs.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_matches_block8_on_null_and_dependent_cells():
    mod = _sim()
    rng = np.random.default_rng(29)
    trials = 0
    for r in (1, 2, 3):
        for k in (6, 20):
            for rho in (0.0, 0.5):
                for _ in range(8):
                    T, D = mod.cell_rdecoys(rng, 40, k, r, rho=rho)
                    lib = select_competition(T, D, mod.Q)
                    want = mod.select_maxmethod(T, D, mod.Q)
                    assert (lib.flagged == want).all()
                    trials += 1
    assert trials == 96


def test_matches_block8_under_a_real_signal():
    mod = _sim()
    rng = np.random.default_rng(31)
    for _ in range(10):
        # A changed cell: reuse the shock construction's target against
        # hand-built star decoys so wins actually occur.
        T, DA, DB, _ = mod.cell_shock(rng, 40, 20, 20, 0.8)
        D = np.stack([DA, DB])
        lib = select_competition(T, D, mod.Q)
        want = mod.select_maxmethod(T, D, mod.Q)
        assert (lib.flagged == want).all()
        if lib.n_discoveries:
            assert lib.fdr_hat <= mod.Q


def test_rank_ties_go_to_the_decoy_as_values():
    T = np.array([0.8333333333333333] * 12)
    tied = np.array([[0.8333333333333334] * 12])
    sel = select_competition(T, tied)
    assert sel.empty and not sel.wins.any()
    below = np.array([[0.5] * 12])
    assert select_competition(T, below).flagged.all()


def test_r1_is_classical_tdc_not_the_frozen_pooled_rule():
    """Classical competition never counts a decoy against another input's
    target; the frozen pooled rule does. Pinned so the two are never
    silently conflated (MTH-027 third append)."""
    T = np.array([1.0] * 9 + [0.5])
    D = np.array([[0.6] * 9 + [0.3]])
    assert select(T, D[0], 0.10).empty
    assert select_competition(T, D, 0.10).flagged.all()


def test_floor_is_ceil_one_over_q_r():
    # r = 3, q = 0.10: four clean wins reach the floor, three cannot.
    T = np.array([1.0] * 4 + [0.1] * 8)
    D = np.full((3, 12), 0.5)
    D[:, :4] = 0.2
    sel = select_competition(T, D, 0.10)
    assert sel.floor == 4
    assert sel.n_discoveries == 4 and sel.flagged[:4].all()

    T3 = T.copy()
    T3[3] = 0.1  # the fourth win becomes a loss
    assert select_competition(T3, D, 0.10).empty


def test_shape_validation_names_a_transposed_matrix():
    T = np.zeros(5)
    with pytest.raises(ValueError, match="transposed"):
        competition_wins(T, np.zeros((5, 3)))
    with pytest.raises(ValueError, match="2-D"):
        competition_wins(T, np.zeros(5))


def test_stratified_competition_pools_small_strata():
    rng = np.random.default_rng(37)
    T = rng.random(40)
    D = rng.random((2, 40))
    strata = ["long"] * 35 + ["tiny"] * 5
    out = select_competition_stratified(T, D, strata, q=0.5, min_stratum=30)
    assert set(out.per_stratum) == {"long", "__pooled__"}
    assert out.flagged.shape == (40,)
    # Within each effective stratum the result is the plain selector's.
    eff = np.array(out.strata)
    for name, sel in out.per_stratum.items():
        m = eff == name
        want = select_competition(T[m], D[:, m], q=0.5)
        assert (out.flagged[m] == want.flagged).all()
        assert sel.n_discoveries == int(want.flagged.sum())
