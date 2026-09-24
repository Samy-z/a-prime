"""Cloud-level statistics.

An output cloud is the k samples one arm produced for one input. The design
rule from MTH-005 is that a cloud is a **distribution over semantic modes**, not
a point with a radius: a baseline emitting P 70% of the time moving to B
emitting Q always is a total behaviour change that a centroid-and-spread summary
scores at 0.65 and does not flag.

Two statistics, deliberately separate:

- **mode-share distance** — did the mix of answers change?
- **dispersion ratio** — did the *spread* change, holding the mix aside?

They catch different things. A system collapsing from three answers to one has a
large mode-share distance; a system that keeps the same modal answer but becomes
much more or less reliable shows up in dispersion. Reporting one number for both
loses the distinction that tells you which happened.

Modes here are exact-match strings, which is correct for structured output and
for the stub. Free text needs semantic equivalence classes before these apply —
that is `mode-clustering`, and it is not built yet.
"""

from __future__ import annotations

from collections import Counter
from typing import Sequence


def mode_shares(cloud: Sequence[str]) -> dict[str, float]:
    if not cloud:
        return {}
    n = len(cloud)
    return {m: c / n for m, c in Counter(cloud).items()}


def tv_distance(a: Sequence[str], b: Sequence[str]) -> float:
    """Total variation distance between two clouds' mode-share vectors.

    0 when the two arms produce the same mix, 1 when they share no output at
    all. Bounded, scale-free and interpretable as "the fraction of probability
    mass that moved", which makes it readable in a report without a calibration
    table.
    """
    pa, pb = mode_shares(a), mode_shares(b)
    if not pa and not pb:
        return 0.0
    keys = set(pa) | set(pb)
    return 0.5 * sum(abs(pa.get(k, 0.0) - pb.get(k, 0.0)) for k in keys)


def dispersion(cloud: Sequence[str]) -> float:
    """Probability that two independent draws from this cloud differ.

    Gini-Simpson. 0 for a deterministic arm, approaching 1 as the arm spreads
    over many equally likely outputs. This is the noise floor for this input,
    measured rather than assumed — and note MTH-003: observing 0 here at k=10 is
    weak evidence of determinism, which is why it feeds the decoy comparison
    rather than a hard exact-match branch.
    """
    p = mode_shares(cloud)
    return 1.0 - sum(v * v for v in p.values())


def dispersion_ratio(a: Sequence[str], b: Sequence[str], eps: float = 1e-9) -> float:
    """How much wider or narrower B is than A, as a symmetric log-free ratio.

    Returns a value >= 0 where 0 means identical spread. Collapse and explosion
    both register, because both are behaviour changes and the detector should
    not privilege one direction.
    """
    da, db = dispersion(a), dispersion(b)
    hi, lo = max(da, db), min(da, db)
    return (hi - lo) / (hi + eps)


def novel_mode_mass(baseline: Sequence[str], candidate: Sequence[str]) -> float:
    """Share of the candidate cloud made of outputs the baseline never produced.

    Kept separate from tv_distance because it is asymmetric and answers a
    different question: not "did the mix move" but "is this system saying things
    it never used to say". With k samples the baseline's unseen tail is real, so
    a small value here is uninformative — treat it as a flag for review, not a
    measurement.
    """
    if not candidate:
        return 0.0
    seen = set(baseline)
    return sum(1 for c in candidate if c not in seen) / len(candidate)
