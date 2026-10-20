"""What the candidate cross-system null designs do, measured on a synthetic cell.

The cross-system null proposal (`docs/methods/cross-system-null-proposal.md`)
compares three ways of using a candidate's own second run: pool its
within-system decoys with the baseline's and divide the count by the
decoy-to-target ratio, take the per-input maximum of the two decoys, or
select once per null. Claims about what each does to the estimator in
`src/aprime/fdr.py` are checkable without a model, because the estimator
only sees scores, and this script is that check. It is the instrument
behind every simulation figure the proposal quotes.

Model of a cell: `n` inputs, each with a mode distribution drawn from a
Dirichlet; a changed input's candidate distribution is a mixture of its
baseline distribution and a fresh draw, with `severity` the mixture weight;
every arm is a cloud of `k` samples; the score is the mode-share distance
(`stats.tv_distance`) on the true mode labels, so the judge is perfect and
only the estimator is under test. Grid-valued scores and value-compared
ties, as in the real detector.

    python scripts/simulate_null_designs.py            # the proposal's tables
    python scripts/simulate_null_designs.py --reps 200 # quicker, noisier
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from aprime.fdr import _scores, discoveries, select  # noqa: E402
from aprime.stats import tv_distance  # noqa: E402

Q = 0.10


def select_ratio(targets, decoys, r: int, q: float = Q):
    """`fdr.select` with the decoy count divided by the decoy-to-target ratio.

    The pooled design's estimator, (1 + d/r) / t, over the same candidate cuts
    and the same value comparison as `select`. With r = 1 and decoys of the
    same length as targets it is `select`.
    """
    t = _scores(targets)
    d = _scores(decoys)
    best_n, best_cut = 0, None
    for cut in np.unique(t)[::-1]:
        n_t = int((t >= cut).sum())
        n_d = int((d >= cut).sum())
        if (1 + n_d / r) / max(n_t, 1) <= q and n_t > best_n:
            best_n, best_cut = n_t, float(cut)
    if best_cut is None:
        return np.zeros(len(t), dtype=bool)
    return t >= best_cut


def cell(rng, n: int, k: int, n_changed: int, severity: float, modes: int = 4):
    """Scores for one synthetic cell: target, the two within decoys, truth."""
    labels = [str(i) for i in range(modes)]
    T = np.empty(n)
    DA = np.empty(n)
    DB = np.empty(n)
    truth = np.zeros(n, dtype=bool)
    for i in range(n):
        pa = rng.dirichlet(np.ones(modes))
        if i < n_changed:
            pb = (1 - severity) * pa + severity * rng.dirichlet(np.ones(modes))
            truth[i] = True
        else:
            pb = pa
        draw = lambda p: [labels[j] for j in rng.choice(modes, size=k, p=p)]  # noqa: E731
        a, a2, b, b2 = draw(pa), draw(pa), draw(pb), draw(pb)
        T[i] = tv_distance(a, b)
        DA[i] = tv_distance(a, a2)
        DB[i] = tv_distance(b, b2)
    return T, DA, DB, truth


def designs(T, DA, DB):
    """Flag masks under the three designs."""
    s1 = select(T, DA, Q)
    single = discoveries(T, s1) if not s1.empty else np.zeros(len(T), dtype=bool)
    pooled = select_ratio(T, np.concatenate([DA, DB]), r=2)
    s3 = select(T, np.maximum(DA, DB), Q)
    maxd = discoveries(T, s3) if not s3.empty else np.zeros(len(T), dtype=bool)
    return {"single": single, "pooled": pooled, "max": maxd}


def summarise(rng, n, k, n_changed, severity, reps, modes: int = 4):
    out = {name: {"fdp": [], "power": [], "any": 0} for name in ("single", "pooled", "max")}
    for _ in range(reps):
        T, DA, DB, truth = cell(rng, n, k, n_changed, severity, modes)
        for name, flagged in designs(T, DA, DB).items():
            m = int(flagged.sum())
            out[name]["any"] += m > 0
            out[name]["fdp"].append(float((flagged & ~truth).sum()) / m if m else 0.0)
            if truth.any():
                out[name]["power"].append(float((flagged & truth).sum()) / truth.sum())
    return {name: (np.mean(v["fdp"]), np.mean(v["power"]) if v["power"] else float("nan"),
                   v["any"] / reps) for name, v in out.items()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reps", type=int, default=600)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--modes", type=int, default=4,
                    help="true answers per input; fewer means coarser clouds")
    ap.add_argument("--changed", type=int, default=None,
                    help="changed inputs per cell (default: half)")
    ap.add_argument("--seed", type=int, default=20261020)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    changed = args.n // 2 if args.changed is None else args.changed

    print(f"n={args.n}, q={Q}, {changed} inputs changed, mode-share distance on "
          f"{args.modes} true modes, {args.reps} cells per row")
    print(f"{'k':>3} {'sev':>4} | {'single: FDR pow P(any)':24} | "
          f"{'pooled r=2: FDR pow P(any)':28} | {'max: FDR pow P(any)':22}")
    for k in (6, 20):
        for sev in (0.5, 0.6, 0.7, 0.8, 0.9):
            r = summarise(rng, args.n, k, changed, sev, args.reps, args.modes)
            cells = [f"{r[d][0]:.3f} {r[d][1]:.3f} {r[d][2]:.3f}" for d in ("single", "pooled", "max")]
            print(f"{k:3d} {sev:4.1f} | {cells[0]:24} | {cells[1]:28} | {cells[2]:22}")

    print()
    print("all-null cell (a null pair): probability that anything is flagged")
    for k in (6, 20):
        r = summarise(rng, args.n, k, 0, 0.0, args.reps, args.modes)
        print(f"  k={k}: single {r['single'][2]:.4f}  pooled {r['pooled'][2]:.4f}  max {r['max'][2]:.4f}")

    print()
    print("exchangeability statistic on an all-null cell: share of targets at or "
          "above the pooled decoy median (ties inflate it above 0.5 on a grid)")
    for k in (6, 20):
        shares = []
        for _ in range(args.reps):
            T, DA, DB, _ = cell(rng, args.n, k, 0, 0.0, args.modes)
            med = np.median(np.concatenate([DA, DB]))
            shares.append(float((T >= med).mean()))
        lo, hi = np.percentile(shares, [2.5, 97.5])
        print(f"  k={k}: mean {np.mean(shares):.3f}, central 95 percent {lo:.2f} to {hi:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
