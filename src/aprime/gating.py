"""Surface-drift gating and output-shape inference.

Two things the detector needs to know about a comparison before it scores it,
both derived from the outputs alone.

## The embedding gate (MTH-012)

Embedding displacement is not merely weak. Measured across three model families
it is **anti-correlated** with meaning change: a paraphrase moves the vector
roughly twenty times further than a changed number, date or negation, and pooled
separability sits at or below chance (MTH-011).

It recovers — to AUC 0.54/0.61/0.82 — when the comparison baseline is a minimal
surface change rather than a full rewrite (MTH-012). So the channel is usable
exactly when the candidate's surface style is stable, and worse than useless
when it is not. A channel below chance is worse than an absent one, because it
will be trusted.

That precondition is measurable without knowing anything about the domain, which
is what this module does. Gate the channel on it; do not run it ungated.

## Shape inference and stratification

The measured 5%-FPR threshold for the NLI channel ranged from 0.011 to 0.888
across four output shapes — a factor of eighty. One global threshold is badly
wrong for at least two of them.

A domain-agnostic detector is not told what shape its outputs are, so it infers
them from structure alone. **Shape is taken from the baseline arm, never the
candidate.** MTH-004 forbids stratifying on something derived from the quantity
being measured, and if the candidate's shape set the stratum then a candidate
that changed shape would move itself into a different bucket — hiding the change
that mattered inside a threshold chosen to accommodate it.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Sequence

from .normalize import is_probably_json, normalise_text

_WORD = re.compile(r"\w+")
_LIST_LINE = re.compile(r"^\s*(?:[-*+•]|\d+[.)])\s+", re.MULTILINE)


def _tokens(text: str) -> Counter:
    return Counter(_WORD.findall(normalise_text(text).casefold()))


def surface_drift(cloud_a: Sequence[str], cloud_b: Sequence[str]) -> float:
    """How much the wording moved, ignoring what it means.

    Bag-of-words Jaccard distance between the two clouds pooled. 0 means the
    same vocabulary, 1 means no shared words at all. Deliberately crude: it must
    be blind to meaning, because its job is to measure the confound rather than
    the signal.

    Pooled across the cloud rather than computed per sample pair, since a cloud
    is a distribution and there is no correspondence between the k-th sample of
    one arm and the k-th of another.
    """
    ta, tb = Counter(), Counter()
    for o in cloud_a:
        ta += _tokens(o)
    for o in cloud_b:
        tb += _tokens(o)
    if not ta and not tb:
        return 0.0
    inter = sum((ta & tb).values())
    union = sum((ta | tb).values())
    return 1.0 - (inter / union if union else 0.0)


@dataclass(frozen=True)
class GateVerdict:
    allowed: bool
    drift: float
    threshold: float

    @property
    def reason(self) -> str:
        if self.allowed:
            return f"surface drift {self.drift:.3f} within {self.threshold:.3f}"
        return (
            f"surface drift {self.drift:.3f} exceeds {self.threshold:.3f}; "
            "the embedding channel is anti-correlated with meaning change in "
            "this regime (MTH-011) and is excluded rather than trusted"
        )


def embedding_gate(
    cloud_a: Sequence[str],
    cloud_b: Sequence[str],
    threshold: float = 0.25,
) -> GateVerdict:
    """Decide whether embedding displacement may contribute to this comparison.

    The default threshold is provisional and should be refitted with
    `scripts/fit_gate.py`, which measures where the probe suite's synonym-level
    pairs (the regime the channel survives) separate from paraphrase-level pairs
    (the regime it fails in).
    """
    d = surface_drift(cloud_a, cloud_b)
    return GateVerdict(allowed=d <= threshold, drift=d, threshold=threshold)


# --------------------------------------------------------------------------
# shape
# --------------------------------------------------------------------------

SHAPES = ("json", "list", "short", "prose")


def infer_shape(output: str, short_words: int = 45) -> str:
    """Structural shape of one output, from structure alone.

    Checked in order, because the categories overlap: a JSON document has lines
    and words too. JSON first because it is the only one with an unambiguous
    test.
    """
    s = output.strip()
    if not s:
        return "short"
    if is_probably_json(s):
        return "json"
    if len(_LIST_LINE.findall(s)) >= 2:
        return "list"
    if len(s.split()) <= short_words:
        return "short"
    return "prose"


def shape_of_cloud(cloud: Sequence[str]) -> str:
    """Modal shape of a baseline cloud.

    Taken from the baseline arm only. A candidate that changed shape must not be
    allowed to select its own stratum — see the module docstring.
    """
    if not cloud:
        return "short"
    return Counter(infer_shape(o) for o in cloud).most_common(1)[0][0]


def strata_from_baseline(clouds_a: dict[str, list[str]]) -> dict[str, str]:
    """Map each input id to the stratum its baseline output shape puts it in."""
    return {iid: shape_of_cloud(cloud) for iid, cloud in clouds_a.items()}
