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

from dataclasses import dataclass

import numpy as np


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
    """
    n_t = int((targets >= t).sum())
    n_d = int((decoys >= t).sum())
    return (1 + n_d) / max(n_t, 1)


def select(targets: np.ndarray, decoys: np.ndarray, q: float = 0.10) -> Selection:
    """Most permissive threshold whose estimated FDR stays within `q`.

    Returns an empty selection rather than a bad one when no threshold
    qualifies. A detector that reports nothing is telling the truth; a detector
    that lowers its bar until it finds something is not.
    """
    targets = np.asarray(targets, dtype=float)
    decoys = np.asarray(decoys, dtype=float)
    if targets.size == 0:
        return Selection(float("inf"), 0, float("nan"), q)

    best: Selection | None = None
    # Descending: each candidate admits one more target than the last.
    for t in np.unique(targets)[::-1]:
        fdr = estimate_fdr(targets, decoys, t)
        if fdr <= q:
            n = int((targets >= t).sum())
            if best is None or n > best.n_discoveries:
                best = Selection(float(t), n, float(fdr), q)
    if best is None:
        return Selection(float("inf"), 0, float("nan"), q)
    return best


def discoveries(targets: np.ndarray, sel: Selection) -> np.ndarray:
    return np.asarray(targets, dtype=float) >= sel.threshold


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
