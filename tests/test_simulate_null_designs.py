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
                   "sign statistic", "count ratios"):
        assert marker in out
