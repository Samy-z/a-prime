"""Target-decoy false discovery rate.

The trick, borrowed from proteomics: run the baseline twice. Any difference
between A and A_prime is noise by construction, so the decoy scores *are* the
null distribution — measured on the same corpus, the same models and the same
day as the real comparison, and inheriting the same dependence structure between
inputs.

That last clause is why this is preferred to Benjamini-Hochberg here (MTH-007).
BH controls FDR under positive dependence, which is plausible but unproven
across inputs sharing one model, and production corpora are full of near
duplicates that make the dependence lumpy. Benjamini-Yekutieli is valid under
arbitrary dependence but its correction factor is ~9.8 at m=10,000, which throws
away nearly all power. The decoys do not need the dependence to be characterised
because they are subject to it too.

It also needs no null model, no distributional assumption and no p-values. Any
statistic works as long as larger means more different.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Sequence

import numpy as np

# Scores are compared as values, not as floats. A mode-share distance of 5/6
# comes out as 0.8333333333333333 from one pair of clouds and as
# 0.8333333333333334 from another, because the summation order differs, and an
# exact comparison then sees two cuts where there is one: at the upper one every
# score sitting on the lower float, target or decoy alike, counts as below the
# cut. That understates the decoys at a tie and overstates the separation; it
# moved a committed diagnosis from 0.4 to 0.375 (ENG-010). So every function
# below rounds its scores to this many decimals before any comparison or
# `np.unique`. Nine is three orders below what the artifacts store (six) and
# seven above the noise that caused it (about 1e-16). Thresholds are reported
# at the same precision.
SCORE_DECIMALS = 9


def _scores(x) -> np.ndarray:
    """Scores as values: rounded to `SCORE_DECIMALS` so that ties compare equal."""
    return np.round(np.asarray(x, dtype=float), SCORE_DECIMALS)


def _estimate(targets: np.ndarray, decoys: np.ndarray, t: float) -> float:
    """`estimate_fdr` on arrays already passed through `_scores`."""
    n_t = int((targets >= t).sum())
    n_d = int((decoys >= t).sum())
    return (1 + n_d) / max(n_t, 1)


@dataclass(frozen=True)
class Selection:
    threshold: float
    n_discoveries: int
    fdr_hat: float
    q: float

    @property
    def empty(self) -> bool:
        return self.n_discoveries == 0


def estimate_fdr(targets: np.ndarray, decoys: np.ndarray, t: float) -> float:
    """Estimated FDR among targets scoring at or above `t`.

    The +1 in the numerator is the Barber-Candes conservative correction. It
    matters most in exactly the regime we care about — few discoveries — where
    omitting it lets a single lucky threshold report an FDR of zero off no
    evidence at all.

    Ties count: a score equal to `t` as a value is at or above it whichever
    float form it arrived in (`SCORE_DECIMALS`).
    """
    return _estimate(_scores(targets), _scores(decoys), float(_scores(t)))


def select(targets: np.ndarray, decoys: np.ndarray, q: float = 0.10) -> Selection:
    """Most permissive threshold whose estimated FDR stays within `q`.

    Returns an empty selection rather than a bad one when no threshold
    qualifies. A detector that reports nothing is telling the truth; a detector
    that lowers its bar until it finds something is not.

    Candidate cuts are the distinct target scores as values (`SCORE_DECIMALS`),
    so a decoy tying a cut by value is counted at that cut. Test membership
    against the result with `discoveries`, never with a raw `>=`.
    """
    targets = _scores(targets)
    decoys = _scores(decoys)
    if targets.size == 0:
        return Selection(float("inf"), 0, float("nan"), q)

    best: Selection | None = None
    # Descending: each candidate admits one more target than the last.
    for t in np.unique(targets)[::-1]:
        fdr = _estimate(targets, decoys, t)
        if fdr <= q:
            n = int((targets >= t).sum())
            if best is None or n > best.n_discoveries:
                best = Selection(float(t), n, float(fdr), q)
    if best is None:
        return Selection(float("inf"), 0, float("nan"), q)
    return best


def discoveries(targets: np.ndarray, sel: Selection) -> np.ndarray:
    """Which targets the selection admits, compared as values like `select`."""
    return _scores(targets) >= float(_scores(sel.threshold))


@dataclass(frozen=True)
class BestCut:
    """The closest a channel came to reporting, whether or not it did.

    `select` returns nothing when no cut satisfies q, and nothing is the same
    answer for a channel that separated the arms cleanly but fell short of the
    1/q floor (MTH-024) and for a channel that cannot see the change at all
    (ENG-007). This is the number that tells them apart: the lowest estimated
    FDR any cut achieves, with the counts behind it.
    """

    estimate: float
    cut: float
    targets_above: int
    decoys_above: int

    @property
    def separated(self) -> bool:
        """Some targets sit above every decoy."""
        return self.decoys_above == 0 and self.targets_above > 0


def best_achievable(targets: np.ndarray, decoys: np.ndarray) -> BestCut | None:
    """The cut with the lowest estimated FDR, or None with no targets.

    Ties in the estimate keep the first cut found, which is the highest score
    (the scan descends). Of two cuts estimating alike, the higher one
    describes the top of the ranking, and when the higher cut is separated
    (no decoy at or above it) while the lower tied cut is not, reporting the
    lower would erase the one fact MTH-025 reads this number for. `select`
    breaks its ties the other way, toward more discoveries, because its job
    is power under a budget; this function's job is diagnosis, and the two
    are deliberately different. Settled 2026-11-11 (MTH-027 first append,
    decision 4); every committed diagnosis artifact was produced under this
    rule, so the settlement changes no number. Ties in score are compared as
    values (`SCORE_DECIMALS`): one cut per distinct value, with every target
    and decoy at that value counted.
    """
    targets = _scores(targets)
    decoys = _scores(decoys)
    if targets.size == 0:
        return None
    best: BestCut | None = None
    for t in np.unique(targets)[::-1]:
        est = _estimate(targets, decoys, t)
        n_t = int((targets >= t).sum())
        n_d = int((decoys >= t).sum())
        if best is None or est < best.estimate:
            best = BestCut(float(est), float(t), n_t, n_d)
    return best


def realised_fdr(flagged: np.ndarray, truly_changed: np.ndarray) -> float:
    """Actual FDR, computable only when ground truth is known.

    Available for a stub or a fault-injection harness, never for a real
    deployment — which is the entire reason the decoy machinery has to exist.
    Use it to check that `select` delivers what it promises, not as a metric.
    """
    flagged = np.asarray(flagged, dtype=bool)
    truly_changed = np.asarray(truly_changed, dtype=bool)
    n = int(flagged.sum())
    if n == 0:
        return 0.0
    return float((flagged & ~truly_changed).sum()) / n


@dataclass(frozen=True)
class StratifiedSelection:
    per_stratum: dict[str, Selection]
    flagged: np.ndarray
    strata: tuple[str, ...]

    @property
    def n_discoveries(self) -> int:
        return int(self.flagged.sum())

    def summary(self) -> str:
        parts = [
            f"{s}: n={sum(1 for x in self.strata if x == s)} "
            f"thr={sel.threshold:.3f} found={sel.n_discoveries}"
            for s, sel in sorted(self.per_stratum.items())
        ]
        return f"{self.n_discoveries} discoveries | " + " | ".join(parts)


def select_stratified(
    targets: np.ndarray,
    decoys: np.ndarray,
    strata: Sequence[str],
    q: float = 0.10,
    min_stratum: int = 30,
) -> StratifiedSelection:
    """Select within each stratum, with its own threshold and its own decoys.

    A single global threshold is wrong when strata differ in scale: the measured
    5%-FPR threshold for the NLI channel spanned a factor of eighty across four
    output shapes. Pooling them means over-flagging the tight strata and going
    blind in the wide ones.

    Each stratum carries its own decoys, so FDR is controlled within it. Strata
    smaller than `min_stratum` are pooled into one remainder group rather than
    given a threshold estimated from too little data — a threshold fitted to
    fifteen decoys is a guess wearing a number's clothes.
    """
    targets = np.asarray(targets, dtype=float)
    decoys = np.asarray(decoys, dtype=float)
    strata = list(strata)
    if not (len(targets) == len(decoys) == len(strata)):
        raise ValueError("targets, decoys and strata must be the same length")

    counts = Counter(strata)
    effective = [s if counts[s] >= min_stratum else "__pooled__" for s in strata]

    flagged = np.zeros(len(targets), dtype=bool)
    per: dict[str, Selection] = {}
    for name in sorted(set(effective)):
        m = np.array([e == name for e in effective])
        sel = select(targets[m], decoys[m], q)
        per[name] = sel
        flagged[m] = discoveries(targets[m], sel)
    return StratifiedSelection(per_stratum=per, flagged=flagged,
                               strata=tuple(effective))


# ---------------------------------------------------------------------------
# within-input competition at r > 1  (MTH-027 third append, 2026-11-11)
# ---------------------------------------------------------------------------
#
# The adopted multi-decoy estimator: Emery, Hasam, Noble, Keich
# (arXiv:1907.01458), the within-input competition family at its max-method
# instantiation, c = lambda = 1/(r+1). Per input, the target score competes
# against that input's OWN r decoy scores and wins only by strictly beating
# every one of them as a value; the estimate divides a count of competition
# OUTCOMES by r, never a pooled above-threshold count — the one legitimate
# division the decision-5 literature read found. Floor: ceil(1/(q*r))
# discoveries, which is the resolution the parked naive C' was meant to buy.
#
# r = 1 is classical target-decoy competition and is NOT byte-identical to
# the frozen pooled rule above (`select`): classical competition never counts
# a decoy against another input's target, the pooled rule does. Nothing here
# replaces `select`; paper one's path is untouched, and a committed test pins
# a case where the two disagree so they are never silently conflated. This
# selector exists for the cross-system r > 1 measurements: the titration's
# b > 1 points (r = b - 1 star pairs) and pooled rosters.


@dataclass(frozen=True, eq=False)
class CompetitionSelection:
    """What the max-method competition selected, with its evidence.

    `flagged` marks the admitted inputs; `wins` the original-win indicator
    (target strictly above every one of its own decoys, as values); `w` the
    competition score per input, the maximum of its r + 1 scores. On an
    estimate tie between cuts the most permissive qualifying cut wins, as in
    `select`, because this object's job is power under a budget.
    """

    threshold: float
    n_discoveries: int
    fdr_hat: float
    q: float
    r: int
    flagged: np.ndarray
    wins: np.ndarray
    w: np.ndarray

    @property
    def empty(self) -> bool:
        return self.n_discoveries == 0

    @property
    def floor(self) -> int:
        """The fewest discoveries this estimator can report: ceil(1/(q*r))."""
        return int(np.ceil(1.0 / (self.q * self.r) - 1e-9))


def competition_wins(targets, decoy_matrix) -> tuple[np.ndarray, np.ndarray]:
    """Per-input competition scores and original-win indicators.

    `decoy_matrix` has shape (r, n): row j holds the j-th decoy score of
    every input — s(A, A'_j) for the titration's star pairs. A rank tie at
    the top counts as a decoy win: the target must STRICTLY exceed its top
    decoy as a value (`SCORE_DECIMALS`). Emery et al. break ties at random;
    this pipeline is deterministic given recordings, and on our coarse
    grids the conservative direction only raises the estimate, with the
    power price measured by the simulator's top-tie share (block 8).
    Declared with the `best_achievable` tie settlement (MTH-027 first
    append, decision 4).
    """
    t = _scores(targets)
    d = _scores(np.asarray(decoy_matrix, dtype=float))
    if d.ndim != 2 or d.shape[0] < 1:
        raise ValueError(
            f"decoy_matrix must be 2-D with shape (r, n_inputs); got "
            f"{d.shape if hasattr(d, 'shape') else type(decoy_matrix)}")
    if d.shape[1] != t.shape[0]:
        hint = (" (it looks transposed: rows must be decoy sets, columns "
                "inputs)" if d.shape[0] == t.shape[0] else "")
        raise ValueError(
            f"decoy_matrix has {d.shape[1]} inputs per row against "
            f"{t.shape[0]} targets{hint}")
    dmax = d.max(axis=0)
    return np.maximum(t, dmax), t > dmax


def select_competition(targets, decoy_matrix, q: float = 0.10) -> CompetitionSelection:
    """The adopted r > 1 selection: most permissive cut over the competition
    scores whose estimate (1 + decoy wins) / (r * original wins) stays
    within `q`, flagging the original wins at or above it.

    Mirrors `select_maxmethod` in `scripts/simulate_null_designs.py` (block
    8) exactly — the equivalence is pinned by test — so every figure the
    all-null row measured applies to this selector verbatim.
    """
    W, orig = competition_wins(targets, decoy_matrix)
    r = int(np.asarray(decoy_matrix).shape[0])
    best: tuple[int, float, float] | None = None
    for cut in np.unique(W)[::-1]:
        at = W >= cut
        n_t = int((at & orig).sum())
        n_d = int((at & ~orig).sum())
        fdr = (1 + n_d) / (r * max(n_t, 1))
        if fdr <= q and (best is None or n_t > best[0]):
            best = (n_t, float(cut), float(fdr))
    if best is None:
        return CompetitionSelection(float("inf"), 0, float("nan"), q, r,
                                    np.zeros(len(W), dtype=bool), orig, W)
    n, cut, fdr = best
    return CompetitionSelection(cut, n, fdr, q, r,
                                orig & (W >= cut), orig, W)


@dataclass(frozen=True, eq=False)
class StratifiedCompetition:
    per_stratum: dict[str, CompetitionSelection]
    flagged: np.ndarray
    strata: tuple[str, ...]

    @property
    def n_discoveries(self) -> int:
        return int(self.flagged.sum())


def select_competition_stratified(
    targets,
    decoy_matrix,
    strata: Sequence[str],
    q: float = 0.10,
    min_stratum: int = 30,
) -> StratifiedCompetition:
    """`select_competition` within each stratum, as `select_stratified` does
    for the pooled rule and for the same reason: the measured 5%-FPR
    threshold spans a factor of eighty across output shapes, and each
    stratum carries its own decoys. Strata smaller than `min_stratum` pool
    into one remainder group.
    """
    t = np.asarray(targets, dtype=float)
    d = np.asarray(decoy_matrix, dtype=float)
    strata = list(strata)
    if d.ndim != 2 or len(t) != d.shape[1] or len(t) != len(strata):
        raise ValueError(
            "targets, decoy_matrix columns and strata must be the same length")

    counts = Counter(strata)
    effective = [s if counts[s] >= min_stratum else "__pooled__" for s in strata]
    flagged = np.zeros(len(t), dtype=bool)
    per: dict[str, CompetitionSelection] = {}
    for name in sorted(set(effective)):
        m = np.array([e == name for e in effective])
        sel = select_competition(t[m], d[:, m], q)
        per[name] = sel
        flagged[m] = sel.flagged
    return StratifiedCompetition(per_stratum=per, flagged=flagged,
                                 strata=tuple(effective))
