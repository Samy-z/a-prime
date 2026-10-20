"""What the candidate cross-system null designs do, measured on a synthetic cell.

The cross-system null proposal (`docs/methods/cross-system-null-proposal.md`)
compares ways of using a candidate's own second run, and the agent titration
(`docs/methods/agent-self-variance-titration-proposal.md`) a third baseline
run. Claims about what each does to the estimator in `src/aprime/fdr.py` are
checkable without a model, because the estimator only sees scores, and this
script is that check. It is the instrument behind every simulation figure the
two proposals and the pre-registration draft quote; nothing in them is a
session computation.

Model of a cell: `n` inputs, each with a mode distribution drawn from a
Dirichlet; a changed input's candidate distribution is a mixture of its
baseline distribution and a fresh draw, with `severity` the mixture weight;
every arm is a cloud of `k` samples; the score is the mode-share distance
(`stats.tv_distance`) on the true mode labels, so the judge is perfect and
only the estimator is under test. Scores are compared as values, rounded as
`fdr._scores` rounds them (ENG-010), in every block.

Blocks, in print order:

1. the three cross-system selectors (single reference decoy; pooled reference
   and candidate decoys with the ratio estimate; per-input maximum) across
   severities at k = 6 and 20, with realised FDR, power and P(any report),
   and the true fraction of the flags the single decoy makes that pooling
   does not;
2. the within-baseline designs of the titration's `b = 3` point: the two
   star pairs that share the reference cloud (r = 2) and all three pairs
   pooled at ratio 3 (the third pair shares no cloud with the target, so
   it is outside the proposals' `r`), against the single decoy, plus the
   share of all-null inputs on which each score is the strict maximum,
   which is the exchangeability check;
3. all-null cells: P(any report) under every design, and under a decoy arm
   correlated with the reference (`A'` copies a sample of `A` with
   probability rho), which is what a null pair's hard stop can see;
4. the sign statistic on all-null cells: among inputs whose target and
   reference decoy differ as values, the share with the target above, with
   its central 95 percent range and the binomial band it should match;
5. the decoy-to-target count ratios at the top of the grid for the maximum
   and the pooled designs on all-null cells.

    python scripts/simulate_null_designs.py --reps 400                        # the proposals' four-mode tables
    python scripts/simulate_null_designs.py --reps 400 --modes 3 --changed 20  # the three-mode check
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

    The estimator (1 + d/r) / t over the same candidate cuts and the same
    value comparison as `select`. With r = 1 and decoys of the same length as
    targets it is `select`.
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


def _clouds(rng, n, k, n_changed, severity, modes, rho=0.0, baselines=2):
    """Per-input mode distributions and clouds.

    Returns (A clouds list of `baselines` clouds per input, B, B', truth).
    With rho > 0 the second baseline cloud copies each sample of the first
    with probability rho, which models a seed or cache that ties the decoy
    arm to the reference (MTH-023).
    """
    labels = [str(i) for i in range(modes)]
    draw = lambda p: [labels[j] for j in rng.choice(modes, size=k, p=p)]  # noqa: E731
    A, B, B2 = [], [], []
    truth = np.zeros(n, dtype=bool)
    for i in range(n):
        pa = rng.dirichlet(np.ones(modes))
        if i < n_changed:
            pb = (1 - severity) * pa + severity * rng.dirichlet(np.ones(modes))
            truth[i] = True
        else:
            pb = pa
        a = [draw(pa) for _ in range(baselines)]
        if rho > 0:
            copy = rng.random(k) < rho
            a[1] = [a[0][j] if copy[j] else a[1][j] for j in range(k)]
        A.append(a)
        B.append(draw(pb))
        B2.append(draw(pb))
    return A, B, B2, truth


def cell(rng, n: int, k: int, n_changed: int, severity: float, modes: int = 4, rho: float = 0.0):
    """Scores for one synthetic cell: target, the two within decoys, truth."""
    A, B, B2, truth = _clouds(rng, n, k, n_changed, severity, modes, rho)
    T = np.array([tv_distance(A[i][0], B[i]) for i in range(n)])
    DA = np.array([tv_distance(A[i][0], A[i][1]) for i in range(n)])
    DB = np.array([tv_distance(B[i], B2[i]) for i in range(n)])
    return T, DA, DB, truth


def cell_b3(rng, n: int, k: int, n_changed: int, severity: float, modes: int = 4):
    """Scores for a cell with three baseline clouds: the titration's point 2.

    Returns (T, DA, DA2, DAA, truth): the target s(A, B), the two star pairs
    s(A, A') and s(A, A'') that share the reference cloud with the target,
    and the pair s(A', A'') that does not.
    """
    A, B, _, truth = _clouds(rng, n, k, n_changed, severity, modes, baselines=3)
    T = np.array([tv_distance(A[i][0], B[i]) for i in range(n)])
    DA = np.array([tv_distance(A[i][0], A[i][1]) for i in range(n)])
    DA2 = np.array([tv_distance(A[i][0], A[i][2]) for i in range(n)])
    DAA = np.array([tv_distance(A[i][1], A[i][2]) for i in range(n)])
    return T, DA, DA2, DAA, truth


def _mask(sel, T):
    return discoveries(T, sel) if not sel.empty else np.zeros(len(T), dtype=bool)


def designs(T, DA, DB):
    """Flag masks under the three cross-system designs."""
    single = _mask(select(T, DA, Q), T)
    pooled = select_ratio(T, np.concatenate([DA, DB]), r=2)
    maxd = _mask(select(T, np.maximum(DA, DB), Q), T)
    return {"single": single, "pooled": pooled, "max": maxd}


def star_designs(T, DA, DA2, DAA):
    """Flag masks under the within-baseline designs of the b = 3 point."""
    single = _mask(select(T, DA, Q), T)
    star = select_ratio(T, np.concatenate([DA, DA2]), r=2)
    allp = select_ratio(T, np.concatenate([DA, DA2, DAA]), r=3)
    return {"single": single, "star r=2": star, "all pairs ratio 3": allp}


def sign_statistic(T, DA):
    """Share of non-tied inputs whose target exceeds its reference decoy.

    Compared as values (ENG-010). Under pairwise exchangeability of
    (target, decoy) on every input the count is Binomial(m, 1/2) whatever
    the score distribution, so the band does not depend on the mode
    structure, the grid or k. Returns (share, m); share is nan at m = 0.
    """
    t = _scores(np.asarray(T, dtype=float))
    d = _scores(np.asarray(DA, dtype=float))
    tied = t == d
    m = int((~tied).sum())
    if m == 0:
        return float("nan"), 0
    return float((t[~tied] > d[~tied]).mean()), m


def _summ(flagged_by_design, truth, out):
    for name, flagged in flagged_by_design.items():
        m = int(flagged.sum())
        out[name]["any"] += m > 0
        out[name]["fdp"].append(float((flagged & ~truth).sum()) / m if m else 0.0)
        if truth.any():
            out[name]["power"].append(float((flagged & truth).sum()) / truth.sum())


def summarise(rng, n, k, n_changed, severity, reps, modes: int = 4):
    names = ("single", "pooled", "max")
    out = {name: {"fdp": [], "power": [], "any": 0} for name in names}
    extra_flags = extra_true = 0
    for _ in range(reps):
        T, DA, DB, truth = cell(rng, n, k, n_changed, severity, modes)
        d = designs(T, DA, DB)
        _summ(d, truth, out)
        extra = d["single"] & ~d["pooled"]
        extra_flags += int(extra.sum())
        extra_true += int((extra & truth).sum())
    res = {name: (np.mean(v["fdp"]), np.mean(v["power"]) if v["power"] else float("nan"),
                  v["any"] / reps) for name, v in out.items()}
    res["extra"] = (extra_true, extra_flags)
    return res


def summarise_b3(rng, n, k, n_changed, severity, reps, modes: int = 4):
    names = ("single", "star r=2", "all pairs ratio 3")
    out = {name: {"fdp": [], "power": [], "any": 0} for name in names}
    for _ in range(reps):
        T, DA, DA2, DAA, truth = cell_b3(rng, n, k, n_changed, severity, modes)
        _summ(star_designs(T, DA, DA2, DAA), truth, out)
    return {name: (np.mean(v["fdp"]), np.mean(v["power"]) if v["power"] else float("nan"),
                   v["any"] / reps) for name, v in out.items()}


def _fmt(r, names):
    return [f"{r[d][0]:.3f} {r[d][1]:.3f} {r[d][2]:.3f}" for d in names]


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
    null_reps = max(args.reps, 2) * 5

    print(f"n={args.n}, q={Q}, {changed} inputs changed, mode-share distance on "
          f"{args.modes} true modes, {args.reps} cells per row, seed {args.seed}")
    print("1. cross-system designs")
    print(f"{'k':>3} {'sev':>4} | {'single: FDR pow P(any)':24} | "
          f"{'pooled ratio 2: FDR pow P(any)':28} | {'max: FDR pow P(any)':22} | single-not-pooled flags: true")
    for k in (6, 20):
        for sev in (0.5, 0.6, 0.7, 0.8, 0.9):
            r = summarise(rng, args.n, k, changed, sev, args.reps, args.modes)
            cells = _fmt(r, ("single", "pooled", "max"))
            et, ef = r["extra"]
            frac = f"{et}/{ef} = {et / ef:.3f}" if ef else "no such flags"
            print(f"{k:3d} {sev:4.1f} | {cells[0]:24} | {cells[1]:28} | {cells[2]:22} | {frac}")

    print()
    print("2. within-baseline designs (b = 3): star pairs share the reference cloud, all pairs add s(A', A'')")
    print(f"{'k':>3} {'sev':>4} | {'single: FDR pow P(any)':24} | {'star r=2: FDR pow P(any)':26} | {'all pairs ratio 3: FDR pow P(any)':34}")
    for k, sev in ((6, 0.9), (20, 0.7), (20, 0.8), (20, 0.9)):
        r = summarise_b3(rng, args.n, k, changed, sev, args.reps, args.modes)
        cells = _fmt(r, ("single", "star r=2", "all pairs ratio 3"))
        print(f"{k:3d} {sev:4.1f} | {cells[0]:24} | {cells[1]:26} | {cells[2]:30}")
    print("   share of all-null inputs on which each score is the strict maximum (exchangeable scores give equal shares):")
    for k in (6, 20):
        star = np.zeros(3)
        allp = np.zeros(4)
        tot = 0
        for _ in range(null_reps):
            T, DA, DA2, DAA, _ = cell_b3(rng, args.n, k, 0, 0.0, args.modes)
            s = np.stack([_scores(x) for x in (T, DA, DA2, DAA)])
            for j in range(3):
                star[j] += int((s[j] > np.delete(s[:3], j, axis=0).max(axis=0)).sum())
            for j in range(4):
                allp[j] += int((s[j] > np.delete(s, j, axis=0).max(axis=0)).sum())
            tot += len(T)
        star /= tot
        allp /= tot
        print(f"   k={k}: among (T, AA', AA'') {star[0]:.3f} {star[1]:.3f} {star[2]:.3f}; "
              f"among (T, AA', AA'', A'A'') {allp[0]:.3f} {allp[1]:.3f} {allp[2]:.3f} {allp[3]:.3f}; {tot} inputs")

    print()
    print("3. all-null cell (a null pair): probability that anything is flagged")
    for k in (6, 20):
        r = summarise(rng, args.n, k, 0, 0.0, null_reps, args.modes)
        print(f"   k={k}: single {r['single'][2]:.4f}  pooled {r['pooled'][2]:.4f}  max {r['max'][2]:.4f}  ({null_reps} cells)")
    print("   with the decoy arm tied to the reference (A' copies a sample of A with probability rho), single decoy:")
    for k in (6, 20):
        parts = []
        for rho in (0.5, 0.7, 0.9, 1.0):
            hits = 0
            for _ in range(args.reps):
                T, DA, DB, _ = cell(rng, args.n, k, 0, 0.0, args.modes, rho=rho)
                hits += bool(_mask(select(T, DA, Q), T).any())
            parts.append(f"rho {rho:.1f}: {hits / args.reps:.3f}")
        print(f"   k={k}: " + "  ".join(parts))

    print()
    print("4. sign statistic on all-null cells: share of non-tied inputs with target above reference decoy")
    for k in (6, 20):
        shares, ms = [], []
        for _ in range(null_reps):
            T, DA, _, _ = cell(rng, args.n, k, 0, 0.0, args.modes)
            s, m = sign_statistic(T, DA)
            if m:
                shares.append(s)
                ms.append(m)
        lo, hi = np.percentile(shares, [2.5, 97.5])
        mbar = float(np.mean(ms))
        half = 1.96 * np.sqrt(0.25 / mbar)
        print(f"   k={k}: mean {np.mean(shares):.3f}, central 95 percent {lo:.2f} to {hi:.2f}; "
              f"non-tied inputs u mean {mbar:.1f} of {args.n}; binomial band at that u {0.5 - half:.2f} to {0.5 + half:.2f}")

    print()
    print("5. decoy-to-target count ratios at the top of the grid on all-null cells (expectation: max at most 2, pooled/2 exactly 1)")
    for k in (6, 20):
        acc = {}
        for _ in range(null_reps):
            T, DA, DB, _ = cell(rng, args.n, k, 0, 0.0, args.modes)
            t, mx, pl = _scores(T), _scores(np.maximum(DA, DB)), _scores(np.concatenate([DA, DB]))
            for cut in np.unique(np.concatenate([t, mx])):
                a = acc.setdefault(float(cut), [0, 0, 0])
                a[0] += int((t >= cut).sum())
                a[1] += int((mx >= cut).sum())
                a[2] += int((pl >= cut).sum())
        cuts = sorted(acc)[::-1][:3]
        parts = []
        for c in cuts:
            nt, nm, npl = acc[c]
            parts.append(f"cut {c:.3f}: max {nm / max(nt, 1):.2f}, pooled/2 {npl / 2 / max(nt, 1):.2f} ({nt} null targets)")
        print(f"   k={k}: " + "; ".join(parts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
