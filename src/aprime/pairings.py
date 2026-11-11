"""Design R's pairings over a roster recording.

MTH-027 froze the cross-system null: every system contributes two clouds, all
arms interleave in one tuple per (input, sample index), A is the declared
reference, and selection runs targets s(A,B) against decoys s(A,A') at r = 1
through the frozen selector, unchanged. Everything else the design names —
the three replicate target sets, the reverse orientation, the stored-baseline
regime that selects on s(B,B'), the cross-pooled estimate — is REPORTED,
never selecting. This module builds those pairings from one roster recording
by relabelling it into three-arm views and running the unchanged detector on
each: the drift control's pattern, run live first in the comparator's
pairwise campaign (CMP-004), now behind one API instead of five hand-rolled
relabelings.

**Only `DesignRSuite.primary` selects.** Every other report exists so a
reader can judge the primary against the design's own diagnostics: replicate
stability, the reverse orientation's mirrored view, and the orientation
disagreement that MTH-027 first append (decision 2) adopted as a reported
in-run diagnostic — never an auto-gate, because benign asymmetry exists on
healthy pairs (one side noisier against itself than the other, CMP-004).

The r > 1 star-pair selection (the titration's b > 1 points) does not live
here: `fdr.select_competition` is its selector, and the titration runner
composes it with per-star-pair scores because each star pair costs its own
NLI pass. See `docs/knowledge/decoy-fdr.md`.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field

import numpy as np

from . import fdr
from .detect import Report, detect
from .recorder import Recording


def pair_recording(rec: Recording, left: str, left_prime: str,
                   right: str) -> Recording:
    """A three-arm view of a roster recording: left as A, left_prime as
    A_prime, right as B, everything else dropped. The detector downstream
    then computes targets s(left, right) against decoys s(left, left_prime),
    which is how one roster yields every pairing Design R names."""
    relabel = {left: "A", left_prime: "A_prime", right: "B"}
    samples = [dataclasses.replace(s, arm=relabel[s.arm])
               for s in rec.samples if s.arm in relabel]
    return Recording(samples=samples, k=rec.k, input_ids=list(rec.input_ids))


def _common_positions(a: Report, b: Report) -> tuple[list[int], list[int]]:
    """Positions of the input ids both reports kept, in a's order."""
    pb = {iid: j for j, iid in enumerate(b.input_order)}
    pa_idx, pb_idx = [], []
    for i, iid in enumerate(a.input_order):
        j = pb.get(iid)
        if j is not None:
            pa_idx.append(i)
            pb_idx.append(j)
    return pa_idx, pb_idx


def _ratio_report(targets, decoys, r: int, q: float) -> dict:
    """What the ratio estimate (1 + d/r) / t would admit — reported, never
    selecting. The cross-pooled quantity Design R names (CMP-003's pending
    item), computed over strata pooled together and saying so: a reported
    scalar diagnostic, while the selecting path stays stratified."""
    t = fdr._scores(targets)
    d = fdr._scores(np.asarray(decoys, dtype=float))
    best_n, best_cut, best_est = 0, None, None
    for cut in np.unique(t)[::-1]:
        n_t = int((t >= cut).sum())
        n_d = int((d >= cut).sum())
        est = (1 + n_d / r) / max(n_t, 1)
        if est <= q and n_t > best_n:
            best_n, best_cut, best_est = n_t, float(cut), float(est)
    return {"would_flag": best_n, "cut": best_cut, "estimate": best_est,
            "r": r, "selects": False,
            "strata": "pooled for this reported diagnostic"}


@dataclass
class DesignRSuite:
    """One roster recording, read the way Design R prescribes.

    `primary` is the only selection. `reverse` and `replicates` are the
    design's reported diagnostics (their Report objects carry findings
    because the detector always reports what its null admits, but nothing
    downstream may treat them as selections). `cross_pooled` is the named
    never-selecting estimate; `orientation` the decision-2 diagnostic.
    """

    primary: Report
    selects_on: str
    reverse: Report | None = None
    replicates: dict[str, Report] = field(default_factory=dict)
    cross_pooled: dict[str, dict] | None = None
    orientation: dict | None = None
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "selects_on": self.selects_on,
            "primary": self.primary.to_dict(),
            "reverse": self.reverse.to_dict() if self.reverse else None,
            "replicates": {k: v.to_dict() for k, v in self.replicates.items()},
            "cross_pooled": self.cross_pooled,
            "orientation": self.orientation,
            "notes": list(self.notes),
        }


def design_r(
    recording: Recording,
    *,
    predicate=None,
    nli_channel=None,
    embedder=None,
    q: float = 0.10,
    reference: str = "A",
    reference_prime: str = "A_prime",
    candidate: str = "B",
    candidate_prime: str = "B_prime",
    stored_baseline: bool = False,
) -> DesignRSuite:
    """Every pairing Design R names, from one four-arm roster recording.

    Interleaved regime (`stored_baseline=False`): the primary selection runs
    targets s(reference, candidate) against the reference's own pair, r = 1,
    through the frozen selector. With the candidate's second cloud present,
    the suite adds the reverse orientation (the candidate's own pair as its
    null), the three replicate target sets, the cross-pooled estimate under
    its own name, and the orientation-disagreement diagnostic.

    Stored-baseline regime (`stored_baseline=True`, the version-bump case
    where the reference was recorded weeks earlier and cannot interleave):
    the selection runs on the candidate's own pair — detect sees the
    candidate as its baseline — and s(reference, reference_prime) is
    reported alongside when the stored pair exists, exactly as MTH-027
    prescribes. The drift negative control (STD-014) is the measured
    no-change case of this regime.

    Asymmetric channels (the directional tail) read in the frame of
    whichever side plays the baseline; the suite's notes say which.
    """
    present = {s.arm for s in recording.samples}
    kw = dict(predicate=predicate, nli_channel=nli_channel,
              embedder=embedder, q=q)
    notes: list[str] = []

    if stored_baseline:
        need = {candidate, candidate_prime, reference}
        if need - present:
            raise ValueError(
                f"stored-baseline regime needs arms {sorted(need)}; the "
                f"recording carries {sorted(present)}")
        primary = detect(pair_recording(recording, candidate,
                                        candidate_prime, reference), **kw)
        notes.append(
            "stored-baseline regime: the candidate's own pair is the null "
            "(MTH-027); directional signs read in the candidate's frame.")
        suite = DesignRSuite(primary=primary, selects_on="candidate",
                             notes=notes)
        if reference_prime in present:
            suite.replicates["forward s(A,B) vs s(A,A'), reported"] = detect(
                pair_recording(recording, reference, reference_prime,
                               candidate), **kw)
            notes.append("s(A,A') reported alongside, as the design requires.")
        return suite

    need = {reference, reference_prime, candidate}
    if need - present:
        raise ValueError(
            f"Design R's interleaved regime needs arms {sorted(need)}; the "
            f"recording carries {sorted(present)}")
    primary = detect(pair_recording(recording, reference, reference_prime,
                                    candidate), **kw)
    suite = DesignRSuite(primary=primary, selects_on="reference", notes=notes)
    notes.append("only the primary selects; every other report is a "
                 "diagnostic (MTH-027).")

    if candidate_prime not in present:
        notes.append(
            f"no {candidate_prime!r} arm: reverse orientation, replicate "
            "sets and the cross-pooled estimate need the candidate's own "
            "second cloud and are not computed.")
        return suite

    suite.reverse = detect(pair_recording(recording, candidate,
                                          candidate_prime, reference), **kw)
    suite.replicates = {
        "s(A,B') vs s(A,A')": detect(
            pair_recording(recording, reference, reference_prime,
                           candidate_prime), **kw),
        "s(A',B) vs s(A',A)": detect(
            pair_recording(recording, reference_prime, reference,
                           candidate), **kw),
        "s(A',B') vs s(A',A)": detect(
            pair_recording(recording, reference_prime, reference,
                           candidate_prime), **kw),
    }

    p_ids = {f.input_id for f in primary.findings}
    r_ids = {f.input_id for f in suite.reverse.findings}
    suite.orientation = {
        "primary_only": sorted(p_ids - r_ids),
        "reverse_only": sorted(r_ids - p_ids),
        "both": sorted(p_ids & r_ids),
    }
    notes.append(
        "orientation disagreement is a reported diagnostic, never a gate "
        "(MTH-027 first append, decision 2): benign asymmetry exists on "
        "healthy pairs.")

    cross: dict[str, dict] = {}
    for name, ch in primary.channels.items():
        rch = suite.reverse.channels.get(name)
        if (ch.skipped or rch is None or rch.skipped
                or ch.targets.size == 0 or rch.decoys.size == 0):
            continue
        pi, ri = _common_positions(primary, suite.reverse)
        if not pi:
            continue
        # Mirror the selection's handling of the two-tailed channel.
        fold = np.abs if name == "nli_directional" else np.asarray
        t = fold(ch.targets)[pi]
        d_near = fold(ch.decoys)[pi]
        d_far = fold(rch.decoys)[ri]
        cross[name] = _ratio_report(t, np.concatenate([d_near, d_far]),
                                    r=2, q=q)
    suite.cross_pooled = cross or None
    if cross:
        notes.append(
            "cross-pooled (1 + d/2)/t computed under its own name and never "
            "selecting (the quantity CMP-003 left pending).")
    return suite
