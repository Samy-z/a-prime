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

Blocks 6 to 9 are the MTH-027 first append's decision-4 commission (each on
its own `[seed, block]` rng stream, so their figures do not depend on which
blocks run; blocks 1 to 5 keep sharing one stream, so the proposals'
committed figures are unchanged at the default seed):

6. the (a') hole: all-null cells whose CANDIDATE cloud is within-cloud
   dependent (rho dial, chain and anchor variants), false-certification rate
   of the primary selection, against the audit's k=20 figures;
7. its stored-baseline mirror: dependence on the stored A, selection on
   s(B,B') — the audit's symmetry refutation, expected to match block 6;
8. the all-null r-decoy row of the decision-5 read: realised FDR of the
   within-input competition max-method against the parked naive
   C' = (1+d)/(rt), r in {1,2,3} by k by rho, with the top-tie share that
   prices the deterministic tie rule;
9. the shock alternative: eps of mass moved to one novel mode, so the dial
   is exactly the population mode-share distance, for power curves over the
   cross-system designs.

    python scripts/simulate_null_designs.py --reps 400                        # the proposals' four-mode tables
    python scripts/simulate_null_designs.py --reps 400 --modes 3 --changed 20  # the three-mode check
    python scripts/simulate_null_designs.py --only 6 --null-cells 2000         # the (a') acceptance row
    python scripts/simulate_null_designs.py --only 8 --null-cells 2000         # the max-method vs C' grid
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


# --------------------------------------------------------------------------
# MTH-027 first append, decision 4: the four commissioned blocks (6 to 9).
# Each uses its own rng, seeded as [seed, block number], so its figures do
# not depend on which other blocks ran. Blocks 1 to 5 keep sharing one
# stream, so the proposals' committed figures are unchanged at the default
# seed.
# --------------------------------------------------------------------------


def _dep_cloud(rng, p, k, rho, labels, variant="chain"):
    """One cloud with WITHIN-cloud dependence: sample j copies an earlier
    sample with probability rho — the previous one ("chain", giving runs) or
    the first one ("anchor") — else draws fresh from p. Models a pinned seed,
    a response cache or a sticky route on one arm's own calls: the dependence
    of MTH-027 first append, finding (a'). rho = 0 is iid."""
    out = []
    for j in range(k):
        if j and rng.random() < rho:
            out.append(out[-1] if variant == "chain" else out[0])
        else:
            out.append(labels[int(rng.choice(len(p), p=p))])
    return out


def cell_dependent(rng, n, k, rho, modes=4, variant="chain", side="candidate"):
    """All-null cell with within-cloud dependence on exactly one arm.

    side "candidate": targets s(A, B_dep) against decoys s(A, A') — Design R's
    primary orientation with the (a') hole: the dependence sits on the arm the
    selecting decoy never sees.
    side "stored": targets s(A_dep, B) against decoys s(B, B') — the
    stored-baseline regime with the dependence on the un-re-recordable stored
    arm, the audit's symmetry refutation.
    Every input is null: one distribution per input, every cloud drawn from it.
    """
    labels = [str(i) for i in range(modes)]
    T, D = np.empty(n), np.empty(n)
    for i in range(n):
        p = rng.dirichlet(np.ones(modes))
        fresh = lambda: [labels[j] for j in rng.choice(modes, size=k, p=p)]  # noqa: E731
        dep = _dep_cloud(rng, p, k, rho, labels, variant)
        if side == "candidate":
            a, a2 = fresh(), fresh()
            T[i], D[i] = tv_distance(a, dep), tv_distance(a, a2)
        else:
            b, b2 = fresh(), fresh()
            T[i], D[i] = tv_distance(dep, b), tv_distance(b, b2)
    return T, D


def false_cert_rate(rng, n, k, rho, cells, modes=4, variant="chain", side="candidate"):
    """Share of all-null cells on which the primary selection flags anything."""
    hits = 0
    for _ in range(cells):
        T, D = cell_dependent(rng, n, k, rho, modes, variant, side)
        hits += bool(_mask(select(T, D, Q), T).any())
    return hits / cells


def cell_rdecoys(rng, n, k, r, modes=4, rho=0.0, variant="chain"):
    """All-null cell with b = r + 1 baseline clouds: targets s(A, B), decoy
    sets s(A, A^(j)) for j = 1..r. With rho > 0 the CANDIDATE cloud B is
    within-cloud dependent (`_dep_cloud`), crossing the (a') sweep into this
    row as the literature read's item 2 asks; every other cloud is iid from
    the input's own distribution."""
    labels = [str(i) for i in range(modes)]
    T, D = np.empty(n), np.empty((r, n))
    for i in range(n):
        p = rng.dirichlet(np.ones(modes))
        fresh = lambda: [labels[j] for j in rng.choice(modes, size=k, p=p)]  # noqa: E731
        a = fresh()
        b = _dep_cloud(rng, p, k, rho, labels, variant) if rho > 0 else fresh()
        T[i] = tv_distance(a, b)
        for j in range(r):
            D[j, i] = tv_distance(a, fresh())
    return T, D


def maxmethod_wins(targets, decoys_matrix):
    """Within-input competition, max-method reduction (the decision-5 read,
    Emery et al.): W_i is the maximum of the input's r + 1 scores; the input
    is an ORIGINAL win iff the target strictly exceeds every one of its own
    decoys as values (`_scores`), else a DECOY win. A rank tie at the top
    counts as a decoy win: the deterministic, conservative member of the
    family on our coarse grids, declared alongside `best_achievable`'s tie
    settlement (MTH-027 first append, decision 4)."""
    t = _scores(targets)
    d = _scores(decoys_matrix)
    dmax = d.max(axis=0)
    return np.maximum(t, dmax), t > dmax


def select_maxmethod(targets, decoys_matrix, q: float = Q):
    """Emery et al.'s competition family at the max-method instantiation
    (c = lambda = 1/(r+1)): estimate (1 + decoy_wins) / (r * original_wins)
    among inputs whose W sits at or above the cut, flag the original wins
    there. Factor 1/r divides a count of WITHIN-INPUT COMPETITION OUTCOMES,
    never a pooled above-threshold count — the one legitimate division the
    read found. At r = 1 this is classical TDC and NOT byte-identical to the
    frozen paper-one rule (`select`), which nothing here replaces: this
    selector exists for the cross-system r > 1 measurement only."""
    r = int(decoys_matrix.shape[0])
    W, orig = maxmethod_wins(targets, decoys_matrix)
    best_n, best_cut = 0, None
    for cut in np.unique(W)[::-1]:
        at = W >= cut
        n_t = int((at & orig).sum())
        n_d = int((at & ~orig).sum())
        if (1 + n_d) / (r * max(n_t, 1)) <= q and n_t > best_n:
            best_n, best_cut = n_t, float(cut)
    if best_cut is None:
        return np.zeros(len(W), dtype=bool)
    return orig & (W >= best_cut)


def select_cprime(targets, decoys, r: int, q: float = Q):
    """The PARKED estimator (1 + d) / (r t): one +1 shared across r decoy
    sets, so at zero decoys it admits ceil(1/(r q)) targets where the frozen
    per-set form (1 + d/r)/t (`select_ratio`) still needs 1/q. Blocked by
    MTH-027 first append pending the multi-decoy literature read; it exists
    here only so the all-null row can measure it, and nothing in the library
    imports it."""
    t = _scores(targets)
    d = _scores(decoys)
    best_n, best_cut = 0, None
    for cut in np.unique(t)[::-1]:
        n_t = int((t >= cut).sum())
        n_d = int((d >= cut).sum())
        if (1 + n_d) / (r * max(n_t, 1)) <= q and n_t > best_n:
            best_n, best_cut = n_t, float(cut)
    if best_cut is None:
        return np.zeros(len(t), dtype=bool)
    return t >= best_cut


def _shock(p, eps):
    """The controlled alternative: the candidate distribution is (1 - eps) * p
    on the old modes plus eps on one novel mode. The population mode-share
    distance between baseline and candidate is exactly eps for every p, so
    the dial IS the effect size; the mixture alternative in `cell` has a
    per-input realised effect its dial only bounds."""
    return np.append((1.0 - eps) * np.asarray(p, dtype=float), eps)


def cell_shock(rng, n, k, n_changed, eps, modes=4):
    """Scores for one cell under the shock alternative, same return shape as
    `cell`: target, the two within decoys, truth."""
    labels = [str(i) for i in range(modes)] + ["novel"]
    T, DA, DB = np.empty(n), np.empty(n), np.empty(n)
    truth = np.zeros(n, dtype=bool)
    for i in range(n):
        pa = np.append(rng.dirichlet(np.ones(modes)), 0.0)
        pb = _shock(pa[:-1], eps) if i < n_changed else pa
        truth[i] = i < n_changed
        draw = lambda p: [labels[j] for j in rng.choice(modes + 1, size=k, p=p)]  # noqa: E731
        a, a2 = draw(pa), draw(pa)
        b, b2 = draw(pb), draw(pb)
        T[i], DA[i], DB[i] = tv_distance(a, b), tv_distance(a, a2), tv_distance(b, b2)
    return T, DA, DB, truth


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


def _mth027_blocks(args, blocks) -> None:
    """Blocks 6 to 9, commissioned by MTH-027 first append, decision 4.

    Each block runs on `default_rng([seed, block_number])`, so its figures do
    not depend on which other blocks ran; on an all-null cell the realised
    FDR equals P(any flag), which is what the rate columns report."""
    n, modes = args.n, args.modes
    cells = args.null_cells or max(args.reps, 2) * 5
    rhos = (0.0, 0.3, 0.5, 0.7)

    if 6 in blocks:
        rng = np.random.default_rng([args.seed, 6])
        print()
        print("6. (a') candidate-side within-cloud dependence, all-null cells: "
              "primary selection s(A,B) vs s(A,A')")
        print(f"   false-certification rate = P(any flag); {cells} cells per "
              f"entry, rng [{args.seed}, 6]; audit figures to reproduce at "
              f"k=20: 0.090 / 0.652 / 0.983 at rho 0.3 / 0.5 / 0.7")
        for k in (20, 6):
            for variant in ("chain", "anchor"):
                rates = [false_cert_rate(rng, n, k, rho, cells, modes, variant)
                         for rho in rhos]
                row = "  ".join(f"rho {rho:.1f}: {r:.3f}" for rho, r in zip(rhos, rates))
                print(f"   k={k:2d} {variant:6}: {row}")

    if 7 in blocks:
        rng = np.random.default_rng([args.seed, 7])
        print()
        print("7. stored-baseline mirror, all-null cells: selection s(A,B) vs "
              "s(B,B'), dependence on the stored, un-re-recordable A")
        print(f"   {cells} cells per entry, rng [{args.seed}, 7]; symmetry "
              f"expectation: rates match block 6")
        for k in (20, 6):
            for variant in ("chain", "anchor"):
                rates = [false_cert_rate(rng, n, k, rho, cells, modes, variant,
                                         side="stored") for rho in rhos]
                row = "  ".join(f"rho {rho:.1f}: {r:.3f}" for rho, r in zip(rhos, rates))
                print(f"   k={k:2d} {variant:6}: {row}")

    if 8 in blocks:
        rng = np.random.default_rng([args.seed, 8])
        print()
        print("8. all-null r-decoy row (the decision-5 read, item 2): realised "
              "FDR = P(any flag) of the max-method against the parked naive "
              "C' = (1+d)/(rt), star pairs, candidate-side rho crossed in")
        print(f"   {cells} cells per entry, rng [{args.seed}, 8]; floors at "
              f"zero decoy wins / decoys: max-method and C' admit "
              f"ceil(1/(q r)) targets, the frozen (1+d/r)/t form needs "
              f"ceil(1/q); r=1 is classical TDC, NOT the frozen paper-one "
              f"rule; expectation on record: max-method controls at rho 0, "
              f"naive C' exceeds the budget somewhere in the grid")
        for r_ in (1, 2, 3):
            for k in (20, 6):
                parts = []
                for rho in rhos:
                    mm = cp = 0
                    tie = 0.0
                    for _ in range(cells):
                        T, D = cell_rdecoys(rng, n, k, r_, modes, rho)
                        mm += bool(select_maxmethod(T, D).any())
                        cp += bool(select_cprime(T, np.concatenate(D), r_).any())
                        t, dmax = _scores(T), _scores(D).max(axis=0)
                        tie += float((t == dmax).mean())
                    parts.append(f"rho {rho:.1f}: mm {mm / cells:.3f} C' {cp / cells:.3f}")
                print(f"   r={r_} k={k:2d}: " + "  ".join(parts)
                      + f"  (top-tie share {tie / (cells * len(rhos)):.2f})")

    if 9 in blocks:
        rng = np.random.default_rng([args.seed, 9])
        changed = args.n // 2 if args.changed is None else args.changed
        print()
        print("9. shock alternative: eps of mass moves to one novel mode, so "
              "eps IS the population mode-share distance (exact effect size)")
        print(f"   {args.reps} cells per row, {changed} of {n} inputs shocked, "
              f"rng [{args.seed}, 9]")
        print(f"   {'k':>4} {'eps':>4} | {'single: FDR pow P(any)':24} | "
              f"{'pooled ratio 2: FDR pow P(any)':30} | {'max: FDR pow P(any)':22}")
        for k in (6, 20):
            for eps in (0.2, 0.4, 0.6, 0.8):
                out = {name: {"fdp": [], "power": [], "any": 0}
                       for name in ("single", "pooled", "max")}
                for _ in range(args.reps):
                    T, DA, DB, truth = cell_shock(rng, n, k, changed, eps, modes)
                    _summ(designs(T, DA, DB), truth, out)
                res = {name: (np.mean(v["fdp"]),
                              np.mean(v["power"]) if v["power"] else float("nan"),
                              v["any"] / args.reps) for name, v in out.items()}
                c = _fmt(res, ("single", "pooled", "max"))
                print(f"   {k:4d} {eps:4.1f} | {c[0]:24} | {c[1]:30} | {c[2]:22}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--reps", type=int, default=600)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--modes", type=int, default=4,
                    help="true answers per input; fewer means coarser clouds")
    ap.add_argument("--changed", type=int, default=None,
                    help="changed inputs per cell (default: half)")
    ap.add_argument("--seed", type=int, default=20261020)
    ap.add_argument("--only", type=int, nargs="+", choices=(6, 7, 8, 9),
                    default=None,
                    help="run only these MTH-027 decision-4 blocks; they use "
                         "their own [seed, block] rng streams, so their "
                         "figures match the full run, while blocks 1-5 share "
                         "one stream and only run together")
    ap.add_argument("--null-cells", type=int, default=None,
                    help="cells per all-null entry in blocks 6-8 "
                         "(default: 5x --reps; the committed acceptance "
                         "figures use 2000)")
    args = ap.parse_args()
    if args.only:
        print(f"n={args.n}, q={Q}, {args.modes} true modes, seed {args.seed}: "
              f"MTH-027 blocks {sorted(set(args.only))} only")
        _mth027_blocks(args, sorted(set(args.only)))
        return 0
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

    _mth027_blocks(args, (6, 7, 8, 9))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
