"""Semantic mode clustering.

Every statistic in `stats.py` treats an output cloud as a distribution over
modes. Until now a mode was an exact string, which is correct for structured
output and useless for prose: two paraphrases of the same answer count as two
modes, so a system that merely rewords looks like a system that changed.

This module turns k raw samples into semantic equivalence classes, so mode-share
and dispersion mean something on free text.

## The equivalence relation, and its honest defect

Two outputs are the same mode when each entails the other — the bidirectional
test used by the semantic-entropy literature. **That relation is not
transitive.** A may be equivalent to B and B to C while A and C are not, so the
resulting partition depends on the order strings are considered in.

Rather than pretend otherwise, two things are done. Strings are ordered
deterministically (most frequent first, ties broken lexically) so a given cloud
always produces the same partition. And each candidate is compared only to
cluster *representatives*, never to every member, which is the same choice the
semantic-entropy work makes and keeps the cost linear in cluster count instead
of quadratic in samples.

## Cost, which is the real constraint

The equivalence predicate is a cross-encoder forward pass, and it is the
dominant cost of the whole detector. Two things keep it affordable:

- **Normalisation first.** LLM outputs repeat heavily, and once presentation is
  stripped, k samples often collapse to a handful of distinct strings. Only the
  distinct ones are ever compared.
- **Representative comparison.** A new string is tested against one member per
  existing cluster, not against everything seen so far.

`ClusterResult.predicate_calls` records what was actually spent, because this
number is the justification for distilling the predicate later and it should be
measured rather than asserted.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Protocol, Sequence

from .normalize import normalise


class EquivalencePredicate(Protocol):
    """Decides whether two outputs mean the same thing.

    Batched, because the underlying model is far more efficient that way and a
    per-pair interface would quietly become the bottleneck.
    """

    def equivalent(self, pairs: Sequence[tuple[str, str]]) -> list[bool]: ...


@dataclass
class ClusterResult:
    labels: list[int]
    representatives: list[str]
    predicate_calls: int = 0
    distinct_after_normalisation: int = 0
    n_samples: int = 0
    meta: dict = field(default_factory=dict)

    def shares(self) -> dict[int, float]:
        if not self.labels:
            return {}
        n = len(self.labels)
        return {lab: c / n for lab, c in Counter(self.labels).items()}

    def as_modes(self) -> list[str]:
        """Sample-aligned mode identifiers, consumable by `stats`."""
        return [f"m{lab}" for lab in self.labels]

    @property
    def collapse_ratio(self) -> float:
        """How much normalisation alone did. 1.0 means it did nothing."""
        if not self.n_samples:
            return 1.0
        return self.distinct_after_normalisation / self.n_samples


class ExactEquivalence:
    """Baseline predicate: normalised string equality.

    Correct for structured output and the right default when no model is
    available. Also the control for measuring what semantic clustering adds —
    if a semantic predicate does not beat this, it is not paying for itself.
    """

    def equivalent(self, pairs: Sequence[tuple[str, str]]) -> list[bool]:
        return [a == b for a, b in pairs]


def cluster(
    samples: Sequence[str],
    predicate: EquivalencePredicate | None = None,
    *,
    normalise_first: bool = True,
) -> ClusterResult:
    """Partition samples into semantic equivalence classes.

    With no predicate this is exact-match clustering on normalised strings,
    which is both the structured-output path and a genuine baseline.
    """
    if not samples:
        return ClusterResult(labels=[], representatives=[])

    norm = [normalise(s) if normalise_first else s for s in samples]
    counts = Counter(norm)
    # Deterministic order: frequent first, ties lexical. Without this the
    # partition would depend on sample order, and the relation's
    # non-transitivity would make that a real reproducibility problem.
    distinct = sorted(counts, key=lambda s: (-counts[s], s))

    reps: list[str] = []
    assign: dict[str, int] = {}
    calls = 0

    if predicate is None:
        for s in distinct:
            assign[s] = len(reps)
            reps.append(s)
    else:
        for s in distinct:
            if not reps:
                assign[s] = 0
                reps.append(s)
                continue
            verdicts = predicate.equivalent([(r, s) for r in reps])
            calls += len(reps)
            match = next((i for i, v in enumerate(verdicts) if v), None)
            if match is None:
                assign[s] = len(reps)
                reps.append(s)
            else:
                assign[s] = match

    return ClusterResult(
        labels=[assign[s] for s in norm],
        representatives=reps,
        predicate_calls=calls,
        distinct_after_normalisation=len(distinct),
        n_samples=len(samples),
    )


def cluster_jointly(
    cloud_a: Sequence[str],
    cloud_b: Sequence[str],
    predicate: EquivalencePredicate | None = None,
) -> tuple[list[str], list[str], ClusterResult]:
    """Cluster two clouds in one pass so their mode labels are comparable.

    Clustering each cloud separately would produce two unrelated label spaces
    and make mode-share distance meaningless. They have to share a partition.

    Returns each cloud's modes plus the joint result, so the caller can read the
    cost off the same object that produced the labels.
    """
    joint = cluster(list(cloud_a) + list(cloud_b), predicate)
    modes = joint.as_modes()
    return modes[: len(cloud_a)], modes[len(cloud_a) :], joint


class NLIEquivalence:
    """Bidirectional entailment via a cross-encoder.

    Two outputs are the same mode when each entails the other above
    `threshold`. Requiring both directions is what distinguishes equivalence
    from mere consistency: a text with a condition removed is entailed by the
    original in one direction only, and treating that as the same mode would
    re-open exactly the omission blindness MTH-016 closed.

    The threshold is not a free parameter to be tuned by eye. It was fitted
    against the probe suite, where equivalence is known — see MTH-020 and
    `results/clustering_threshold.json`.

    **Why the default is 0.7 and not the fitted argmax of 0.05.** Pooled
    balanced accuracy is nearly flat from 0.05 to 0.65 (0.909 to 0.893), so the
    argmax is inside the noise, and it is driven by `verbosity` — a category
    whose "meaning-preserving" label is itself arguable, since adding a hedge
    does change what is claimed.

    More importantly the two error types cost different things. Wrongly
    *splitting* a preserving pair inflates the noise floor, but it inflates the
    decoy arm's floor identically, so the threshold compensates and validity
    survives; the cost is power. Wrongly *merging* a breaking pair is systematic
    blindness that applies to targets and decoys alike and nothing absorbs it.
    Validity outranks power here, so the threshold leans high: at 0.7 the
    omission merge rate is 9.4% against 40.6% at the argmax.

    This is an argument, not a measurement. Settle it by measuring end-to-end
    detection power across thresholds once a free-text system under test exists.
    """

    def __init__(self, nli_channel, threshold: float = 0.7):
        self.nli = nli_channel
        self.threshold = threshold

    def equivalent(self, pairs: Sequence[tuple[str, str]]) -> list[bool]:
        if not pairs:
            return []
        prem = [a for a, _ in pairs]
        hyp = [b for _, b in pairs]
        fwd = self.nli._probs(prem, hyp)[:, self.nli.entail_idx]
        rev = self.nli._probs(hyp, prem)[:, self.nli.entail_idx]
        return [bool(f >= self.threshold and r >= self.threshold) for f, r in zip(fwd, rev)]


def fit_threshold(
    nli_channel,
    equivalent_pairs: Sequence[tuple[str, str]],
    different_pairs: Sequence[tuple[str, str]],
    grid: Sequence[float] = tuple(i / 20 for i in range(1, 20)),
) -> tuple[float, dict]:
    """Choose the entailment threshold that best separates known cases.

    Scored by balanced accuracy so an imbalance between the two sets cannot be
    gamed by always answering one way. Returns the threshold and the full grid,
    so a flat optimum is visible rather than hidden behind a single number.
    """
    import numpy as np

    def both(ps):
        if not ps:
            return np.empty(0), np.empty(0)
        a = [x for x, _ in ps]
        b = [y for _, y in ps]
        f = nli_channel._probs(a, b)[:, nli_channel.entail_idx]
        r = nli_channel._probs(b, a)[:, nli_channel.entail_idx]
        return f, r

    fe, re_ = both(equivalent_pairs)
    fd, rd = both(different_pairs)
    scores: dict[float, float] = {}
    for t in grid:
        tpr = float(((fe >= t) & (re_ >= t)).mean()) if fe.size else 0.0
        fpr = float(((fd >= t) & (rd >= t)).mean()) if fd.size else 0.0
        scores[t] = 0.5 * (tpr + (1 - fpr))
    best = max(scores, key=lambda t: scores[t])
    return best, {"balanced_accuracy": scores, "n_equivalent": len(equivalent_pairs),
                  "n_different": len(different_pairs)}
