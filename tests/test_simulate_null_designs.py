"""The null-design simulation is the instrument behind the cross-system proposal.

Its ratio estimator must reduce to `fdr.select` at r = 1, its synthetic cell
must respect the truth it claims, and the whole script must run end to end
on a small configuration without a model.
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


def test_script_runs_small(capsys):
    mod = _load()
    sys.argv = ["simulate_null_designs.py", "--reps", "2", "--n", "8"]
    assert mod.main() == 0
    out = capsys.readouterr().out
    assert "all-null cell" in out and "exchangeability statistic" in out
