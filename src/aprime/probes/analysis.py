"""Turning probe scores into the blind-spot map.

The headline quantity is not accuracy. It is:

    at the threshold where this channel raises a false alarm on 5% of
    meaning-preserving rewordings, what fraction of each kind of meaning-
    breaking change does it catch?

That framing matters because a detector is deployed at a false-alarm budget,
not at an operating point chosen after seeing the answers. A channel with a
high AUC and a useless 5%-FPR detection rate is a channel that cannot be
fielded.

Thresholds are computed per shape as well as globally. The gap between the two
says how much of a channel's apparent performance is really the channel sorting
outputs by length and format rather than by meaning.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval. Reported on every rate, per the study conventions."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


def auc(pos: np.ndarray, neg: np.ndarray) -> float:
    """Probability a random positive outscores a random negative.

    Rank-based (Mann-Whitney), so ties are handled at 0.5 rather than silently
    counted as wins.
    """
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    allv = np.concatenate([pos, neg])
    order = allv.argsort()
    ranks = np.empty(len(allv), dtype=float)
    ranks[order] = np.arange(1, len(allv) + 1, dtype=float)
    # average ranks within ties
    _, inv, counts = np.unique(allv, return_inverse=True, return_counts=True)
    sums = np.zeros(len(counts))
    np.add.at(sums, inv, ranks)
    ranks = (sums / counts)[inv]
    n_pos = len(pos)
    r_pos = ranks[:n_pos].sum()
    return (r_pos - n_pos * (n_pos + 1) / 2) / (n_pos * len(neg))


def threshold_at_fpr(preserving: np.ndarray, fpr: float = 0.05) -> float:
    """Score above which at most `fpr` of preserving pairs land.

    Uses the upper quantile directly. With a few hundred preserving pairs this
    is itself an estimate with real uncertainty; the detection rates below
    inherit that uncertainty and their intervals understate it.
    """
    if len(preserving) == 0:
        return float("nan")
    return float(np.quantile(preserving, 1.0 - fpr))


@dataclass
class CategoryResult:
    category: str
    shape: str | None
    n: int
    detected: int
    rate: float
    lo: float
    hi: float
    auc: float
    median_score: float


def evaluate(
    scores: np.ndarray,
    relations: list[str],
    categories: list[str],
    shapes: list[str],
    fpr: float = 0.05,
    per_shape_threshold: bool = False,
) -> tuple[list[CategoryResult], dict]:
    scores = np.asarray(scores, dtype=float)
    rel = np.array(relations)
    cat = np.array(categories)
    shp = np.array(shapes)

    results: list[CategoryResult] = []
    thresholds: dict = {}

    shape_groups = sorted(set(shapes)) if per_shape_threshold else [None]
    for s in shape_groups:
        mask = np.ones(len(scores), dtype=bool) if s is None else (shp == s)
        pres = scores[mask & (rel == "PRESERVING")]
        thr = threshold_at_fpr(pres, fpr)
        thresholds[s or "__global__"] = thr

        for c in sorted(set(cat[rel == "BREAKING"])):
            sel = mask & (cat == c)
            vals = scores[sel]
            if len(vals) == 0:
                continue
            det = int((vals > thr).sum())
            lo, hi = wilson(det, len(vals))
            results.append(
                CategoryResult(
                    category=c,
                    shape=s,
                    n=len(vals),
                    detected=det,
                    rate=det / len(vals),
                    lo=lo,
                    hi=hi,
                    auc=auc(vals, pres),
                    median_score=float(np.median(vals)),
                )
            )

        # Preserving categories are reported too: a preserving category that
        # trips the threshold far more often than the others is not noise, it
        # is a specific rewriting the channel mistakes for a change.
        for c in sorted(set(cat[rel == "PRESERVING"])):
            sel = mask & (cat == c)
            vals = scores[sel]
            if len(vals) == 0:
                continue
            det = int((vals > thr).sum())
            lo, hi = wilson(det, len(vals))
            results.append(
                CategoryResult(
                    category=f"[fp] {c}",
                    shape=s,
                    n=len(vals),
                    detected=det,
                    rate=det / len(vals),
                    lo=lo,
                    hi=hi,
                    auc=float("nan"),
                    median_score=float(np.median(vals)),
                )
            )

    return results, thresholds


def separability(scores: np.ndarray, relations: list[str]) -> float:
    """One number for 'can this channel tell the two populations apart at all'."""
    s = np.asarray(scores, dtype=float)
    r = np.array(relations)
    return auc(s[r == "BREAKING"], s[r == "PRESERVING"])
