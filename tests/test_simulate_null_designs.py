"""The null-design simulation is the instrument behind the cross-system proposal.

Its ratio estimator must reduce to `fdr.select` at r = 1, its synthetic cells
must respect the truth they claim, its sign statistic must compare values as
the detector does (ENG-010), and the whole script must run end to end on a
small configuration without a model.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "simulate_null_designs", ROOT / "scripts" / "simulate_null_designs.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_ratio_one_is_select():
    mod = _load()
    sys.path.insert(0, str(ROOT / "src"))
    from aprime.fdr import discoveries, select

    rng = np.random.default_rng(3)
    for _ in range(20):
        T, DA, DB, _ = mod.cell(rng, 40, 6, 20, 0.9)
        s = select(T, DA, mod.Q)
        want = discoveries(T, s) if not s.empty else np.zeros(40, dtype=bool)
        got = mod.select_ratio(T, DA, r=1)
        assert (want == got).all()


def test_cell_truth_and_shapes():
    mod = _load()
    rng = np.random.default_rng(5)
    T, DA, DB, truth = mod.cell(rng, 12, 6, 5, 1.0, modes=3)
    assert T.shape == DA.shape == DB.shape == truth.shape == (12,)
    assert truth[:5].all() and not truth[5:].any()
    # unchanged inputs: the candidate shares the baseline's distribution, so the
    # target is a within-system score and bounded like the decoys
    assert 0.0 <= T.min() and T.max() <= 1.0


def test_cell_b3_shapes_and_rho():
    mod = _load()
    rng = np.random.default_rng(7)
    T, DA, DA2, DAA, truth = mod.cell_b3(rng, 10, 6, 4, 0.8)
    for arr in (T, DA, DA2, DAA):
        assert arr.shape == (10,) and 0.0 <= arr.min() and arr.max() <= 1.0
    assert truth[:4].all() and not truth[4:].any()
    # a decoy arm that copies the reference exactly scores zero on every input
    _, DA, _, _ = mod.cell(rng, 10, 6, 0, 0.0, rho=1.0)
    assert (DA == 0).all()


def test_sign_statistic_compares_values():
    mod = _load()
    T = np.array([0.5, 0.2, 0.7, 0.1])
    DA = np.array([0.5 + 1e-12, 0.3, 0.6, 0.1 - 1e-12])
    share, m = mod.sign_statistic(T, DA)
    # the two near-ties are ties as values, so two inputs count, one above
    assert m == 2 and share == 0.5
    share_perturbed, m_perturbed = mod.sign_statistic(T + 1e-12, DA)
    assert (share_perturbed, m_perturbed) == (share, m)
    assert mod.sign_statistic(T, T) == (float("nan"), 0) or mod.sign_statistic(T, T)[1] == 0


def test_script_runs_small(capsys):
    mod = _load()
    sys.argv = ["simulate_null_designs.py", "--reps", "2", "--n", "8"]
    assert mod.main() == 0
    out = capsys.readouterr().out
    for marker in ("cross-system designs", "within-baseline designs", "all-null cell",
                   "sign statistic", "count ratios", "(a')", "stored-baseline mirror",
                   "r-decoy row", "shock alternative"):
        assert marker in out


# ------------------- the MTH-027 decision-4 blocks (first append, 2026-11-11)


def test_dep_cloud_rho_one_collapses_under_both_variants():
    mod = _load()
    rng = np.random.default_rng(11)
    p = np.array([0.4, 0.3, 0.2, 0.1])
    for variant in ("chain", "anchor"):
        cloud = mod._dep_cloud(rng, p, 12, 1.0, ["a", "b", "c", "d"], variant)
        assert len(cloud) == 12 and len(set(cloud)) == 1


def test_cell_dependent_shapes_on_both_sides():
    mod = _load()
    rng = np.random.default_rng(13)
    for side in ("candidate", "stored"):
        T, D = mod.cell_dependent(rng, 10, 6, 0.4, side=side)
        assert T.shape == D.shape == (10,)
        assert 0.0 <= T.min() and T.max() <= 1.0
        assert 0.0 <= D.min() and D.max() <= 1.0


def test_select_cprime_at_r1_is_select():
    """(1 + d) / (1 * t) is the frozen estimate itself, so the parked form at
    r = 1 must flag exactly what `select` flags."""
    mod = _load()
    sys.path.insert(0, str(ROOT / "src"))
    from aprime.fdr import discoveries, select

    rng = np.random.default_rng(17)
    for _ in range(20):
        T, DA, _, _ = mod.cell(rng, 40, 6, 20, 0.9)
        s = select(T, DA, mod.Q)
        want = discoveries(T, s) if not s.empty else np.zeros(40, dtype=bool)
        assert (want == mod.select_cprime(T, DA, r=1)).all()


def test_maxmethod_rank_ties_go_to_the_decoy_as_values():
    """The within-input rank tie rule declared with the best_achievable
    settlement: a target tying its top decoy AS A VALUE (ENG-010 rounding)
    is a decoy win, the conservative deterministic member of the family."""
    mod = _load()
    T = np.array([0.8333333333333333] * 12)
    tied = np.array([[0.8333333333333334] * 12])
    assert not mod.select_maxmethod(T, tied).any()
    below = np.array([[0.5] * 12])
    assert mod.select_maxmethod(T, below).all()


def test_maxmethod_at_r1_is_classical_tdc_not_the_frozen_rule():
    """Classical TDC never counts a decoy against another input's target; the
    frozen pooled rule does. The two must stay distinct estimators: here the
    frozen rule reports nothing while competition flags all ten."""
    mod = _load()
    sys.path.insert(0, str(ROOT / "src"))
    from aprime.fdr import select

    T = np.array([1.0] * 9 + [0.5])
    D = np.array([[0.6] * 9 + [0.3]])
    assert select(T, D[0], mod.Q).empty
    assert mod.select_maxmethod(T, D).all()


def test_shock_dial_is_the_exact_population_distance():
    mod = _load()
    rng = np.random.default_rng(19)
    for eps in (0.2, 0.5, 0.8):
        p = rng.dirichlet(np.ones(4))
        pb = mod._shock(p, eps)
        pa_full = np.append(p, 0.0)
        assert pb.shape == (5,)
        assert abs(pb.sum() - 1.0) < 1e-12
        assert abs(0.5 * np.abs(pa_full - pb).sum() - eps) < 1e-12


def test_cell_shock_shapes_and_truth():
    mod = _load()
    rng = np.random.default_rng(23)
    T, DA, DB, truth = mod.cell_shock(rng, 12, 6, 5, 0.6)
    assert T.shape == DA.shape == DB.shape == truth.shape == (12,)
    assert truth[:5].all() and not truth[5:].any()


def test_only_runs_just_the_named_blocks(capsys):
    mod = _load()
    sys.argv = ["simulate_null_designs.py", "--only", "6", "8",
                "--reps", "2", "--n", "8", "--null-cells", "2"]
    assert mod.main() == 0
    out = capsys.readouterr().out
    assert "(a')" in out and "r-decoy row" in out
    assert "cross-system designs" not in out and "shock alternative" not in out
