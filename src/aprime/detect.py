"""The detector: everything composed into one comparison.

Given a three-arm recording, report which inputs changed behaviour, at a
calibrated false-alarm rate, without knowing what the outputs mean.

    record three arms
      -> dedup
      -> normalise
      -> cluster jointly (A with B, and A with A_prime)
      -> score: mode-share, dispersion, and where models are available
         NLI contradiction and NLI directional in both tails
      -> gate the embedding channel on measured surface drift
      -> select per channel, stratified by baseline output shape
      -> check induced structural conformance
      -> assemble

Two properties of this composition matter more than any individual channel.

**Every channel is scored against its own decoys.** The A-vs-A_prime comparison
goes through exactly the same clustering, normalisation and statistic as
A-vs-B. A channel that is noisy, mis-calibrated or outright broken produces
noisy decoys too, so its threshold rises and it reports nothing — rather than
reporting nonsense. That is what makes it safe to add a channel whose behaviour
is not fully understood.

**No channel votes.** Findings are reported per channel, never summed into a
score. Combining them would require weights, weights would be fitted, and
fitting them outside a leave-one-system-out fold is precisely what MTH-009
forbids. A reader sees which channel fired and decides.

The model-backed channels are optional. With no NLI model and no embedder this
still runs on mode-share, dispersion and conformance alone, which is the whole
structured-output path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np

from . import conformance, fdr, stats
from .clustering import EquivalencePredicate, cluster_jointly
from .gating import GateVerdict, embedding_gate, strata_from_baseline
from .normalize import normalise
from .recorder import Recording


# What each check measures, in the words the report uses. The key is what the
# code and the ledgers call it and stays in the report so a reader can grep
# for it; the label is for a reader who has not opened the code.
CHANNEL_LABELS: dict[str, tuple[str, str]] = {
    "mode_share": ("answer mix",
                   "the share of outputs that moved from one answer to another"),
    "dispersion": ("spread",
                   "how much wider or narrower the new system's answers are"),
    "novel_mode": ("new answers",
                   "the share of new outputs the old system never produced"),
    "nli_contradiction": ("contradiction",
                          "how strongly the new output contradicts the old one"),
    "nli_directional": ("information direction",
                        "positive when the new output says less, negative when "
                        "it says more"),
    "embedding": ("embedding distance",
                  "distance between the two systems' outputs as vectors; "
                  "switched off when wording drifts, where it is worse than chance"),
}


def _label(name: str) -> str:
    plain = CHANNEL_LABELS.get(name)
    return f"{name} ({plain[0]})" if plain else name


def _ordered(channels: dict) -> list[tuple[str, "ChannelResult"]]:
    """Checks in the inventory's order, so the report reads the same every run."""
    known = [n for n in CHANNEL_LABELS if n in channels]
    rest = sorted(n for n in channels if n not in CHANNEL_LABELS)
    return [(n, channels[n]) for n in known + rest]


def _floor(q: float) -> int:
    """Smallest number of flagged inputs the estimator can report at q."""
    return int(np.ceil(1.0 / q - 1e-9))


@dataclass
class ChannelResult:
    name: str
    targets: np.ndarray
    decoys: np.ndarray
    selection: fdr.StratifiedSelection | None = None
    skipped: str | None = None
    # The closest each stratum came to reporting, flagged or not. This is what
    # separates "separated but under the floor" from "cannot see it", which the
    # flagged count alone cannot (ENG-007).
    best: dict[str, fdr.BestCut] = field(default_factory=dict)

    @property
    def n_flagged(self) -> int:
        return 0 if self.selection is None else self.selection.n_discoveries

    def reading(self, q: float) -> str:
        """One sentence a reader can act on, per stratum."""
        if self.skipped:
            return "skipped: " + self.skipped
        if self.selection is None:
            return "skipped"
        parts = []
        for stratum, sel in sorted(self.selection.per_stratum.items()):
            where = ("all inputs pooled" if stratum == "__pooled__"
                     else f"{stratum} outputs")
            best = self.best.get(stratum)
            parts.append(f"{where}: " + _read_stratum(sel, best, q))
        return "; ".join(parts)


def _read_stratum(sel: fdr.Selection, best: fdr.BestCut | None, q: float) -> str:
    if sel.n_discoveries:
        return (f"{sel.n_discoveries} flagged above {sel.threshold:.3f}, "
                f"estimated false-discovery rate {sel.fdr_hat:.2f}")
    if best is None:
        return "no inputs"
    floor = _floor(q)
    if best.separated:
        short = floor - best.targets_above
        return (f"{best.targets_above} input(s) sit above every baseline-vs-"
                f"baseline score, under the floor of {floor}: {short} more "
                f"would have cleared it")
    if best.estimate < 0.5:
        return (f"partly separated: at the best cut {best.targets_above} input(s) "
                f"above against {best.decoys_above} baseline score(s), estimate "
                f"{best.estimate:.2f} against q={q:g}. More samples per input "
                f"or more inputs would sharpen this")
    return ("no separation: the new system's scores sit inside the old system's "
            "own run-to-run variation. Either nothing changed that this check can "
            "see, or it cannot see this kind of change; the report cannot tell "
            "those apart")


@dataclass
class Finding:
    input_id: str
    stratum: str
    channels: dict[str, float] = field(default_factory=dict)

    def __str__(self) -> str:
        parts = []
        for k, v in sorted(self.channels.items()):
            plain = CHANNEL_LABELS.get(k, (k,))[0]
            if k == "nli_directional":
                sense = "new output says less" if v > 0 else "new output says more"
                parts.append(f"{plain} {v:+.3f} ({sense})")
            else:
                parts.append(f"{plain} {v:.3f}")
        return f"{self.input_id} [{self.stratum}]  " + " · ".join(parts)


@dataclass
class Report:
    """What a comparison found, written so a reader can act on it.

    The flagged count is the headline and it is the least informative line
    here. A detector that reports nothing is telling the truth, but the truth
    has three different shapes: nothing changed, the change was separated but
    fewer than 1/q inputs cleared the bar (MTH-024), or a check cannot see this
    kind of change (ENG-007). The per-check readings name which.
    """

    findings: list[Finding]
    channels: dict[str, ChannelResult]
    violations: list[conformance.Violation]
    contract: conformance.InducedContract | None
    gate: dict[str, GateVerdict]
    n_inputs: int
    q: float
    notes: list[str] = field(default_factory=list)
    cost: dict = field(default_factory=dict)
    k: int = 0
    # Inputs where at least one arm had fewer than k usable samples. Their
    # thresholds rest on fewer decoys and their statistics on fewer draws, and
    # nothing else in the numbers says so.
    short_clouds: int = 0
    # Set by the caller from provenance.row_provenance(). The report prints
    # it when present, because a report without a run id cannot be traced.
    provenance: dict | None = None

    @property
    def n_flagged(self) -> int:
        return len(self.findings)

    def closest_check(self) -> tuple[str, fdr.BestCut] | None:
        """The check that came nearest to reporting, when none did."""
        best: tuple[str, fdr.BestCut] | None = None
        for name, ch in self.channels.items():
            for b in ch.best.values():
                if best is None or b.estimate < best[1].estimate:
                    best = (name, b)
        return best

    def text(self) -> str:
        q, floor = self.q, _floor(self.q)
        lines = ["a-prime report"]
        if self.provenance:
            p = self.provenance
            git = str(p.get("git_commit") or "?")[:8]
            dirty = "  (uncommitted changes in the tree)" if p.get("git_dirty") else ""
            lines.append(f"  run {p.get('run_id', '?')}  config "
                         f"{p.get('config_hash', '?')}  git {git}{dirty}")
        lines += [
            f"  {self.n_inputs} inputs compared, {self.k} samples per input from "
            "each of three runs: the old system, the old system again, and the "
            "new one.",
            f"  False-discovery budget q={q:g}: of the inputs flagged, at most "
            f"about {q:.0%} are expected to be false alarms. The second run of "
            "the old system sets every threshold.",
        ]
        if self.short_clouds:
            lines.append(
                f"  {self.short_clouds} of {self.n_inputs} inputs had fewer than "
                f"{self.k} usable samples on at least one arm (failed calls), so "
                "their thresholds rest on fewer baseline scores."
            )

        lines += ["", f"{self.n_flagged} of {self.n_inputs} inputs flagged."]
        if not self.findings:
            lines.append(
                f"  Nothing can be reported until at least {floor} inputs (1/q) "
                "clear one check's threshold, however clean the separation "
                "(MTH-024). An empty report means fewer than that changed, not "
                "that nothing did."
            )
            closest = self.closest_check()
            if closest:
                name, b = closest
                lines.append(
                    f"  Closest: {_label(name)}, best estimate {b.estimate:.3f} "
                    f"with {b.targets_above} input(s) above {b.decoys_above} "
                    "baseline score(s)."
                )

        lines += ["", "checks  (each judged against its own baseline-vs-baseline "
                      "scores; none votes)"]
        width = max(len(_label(n)) for n in self.channels) + 2
        for name, ch in _ordered(self.channels):
            head = f"  {_label(name):<{width}}"
            if ch.skipped:
                lines.append(f"{head}skipped: {ch.skipped}")
                continue
            lines.append(f"{head}{ch.n_flagged:>3} flagged   {ch.reading(q)}")

        if self.contract is not None:
            c = self.contract
            lines += [
                "",
                "rules inferred from the old system  (describe the system as a "
                "whole, so not subject to the floor above)",
                f"  {c.n_candidates} candidate rules: {len(c.hard)} held on both "
                f"old-system runs and are enforced, {len(c.band)} held often but "
                f"not always and are listed for a person, {len(c.discarded)} "
                f"discarded ({len(c.pruned_by_decoy)} of those knocked down by "
                "the second run).",
            ]
            if self.violations:
                lines.append("  broken by the new system:")
                for v in self.violations:
                    ex = f"   e.g. {v.examples[0][:70]!r}" if v.examples else ""
                    lines.append(f"    {v.rule}   {v.n_violating} of {v.n_total} "
                                 f"outputs ({v.rate:.0%}){ex}")
            else:
                lines.append("  none of the enforced rules was broken by the new "
                             "system.")
            for rule, s_base, s_decoy in c.band[:10]:
                lines.append(f"  for review: {rule}   held {s_base:.0%} of the time "
                             f"on the old system, {s_decoy:.0%} on its second run. "
                             "Rule, or usual variation?")
            if len(c.band) > 10:
                lines.append(f"  ... and {len(c.band) - 10} more rules for review")

        if self.findings:
            lines += ["", "flagged inputs  (which checks fired, and their scores)"]
            lines += [f"  {f}" for f in self.findings[:25]]
            if len(self.findings) > 25:
                lines.append(f"  ... and {len(self.findings) - 25} more")

        if self.notes:
            lines += ["", "notes"] + [f"  {n}" for n in self.notes]

        if self.cost and self.cost.get("clusterings"):
            c = self.cost
            per = c["predicate_calls"] / max(c["clusterings"], 1)
            collapse = (
                c["distinct_after_normalisation"] / c["samples_clustered"]
                if c["samples_clustered"] else 1.0
            )
            judged = (f"{c['predicate_calls']} model judgements of equivalence "
                      f"over {c['clusterings']} clusterings ({per:.1f} each)"
                      if c["predicate_calls"] else
                      f"exact-match clustering, no model judgements, over "
                      f"{c['clusterings']} clusterings")
            lines += [
                "",
                f"cost  {judged}; normalisation collapsed "
                f"{c['samples_clustered']} samples to "
                f"{c['distinct_after_normalisation']} distinct ({collapse:.0%})",
            ]
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """The same report as JSON-safe data, for a results file."""
        channels = {}
        for name, ch in self.channels.items():
            entry: dict = {"flagged": ch.n_flagged, "skipped": ch.skipped,
                           "reading": ch.reading(self.q)}
            if ch.selection is not None:
                entry["thresholds"] = {
                    s: {"threshold": sel.threshold, "flagged": sel.n_discoveries,
                        "fdr_hat": sel.fdr_hat}
                    for s, sel in ch.selection.per_stratum.items()
                }
            entry["best"] = {
                s: {"estimate": b.estimate, "cut": b.cut,
                    "targets_above": b.targets_above,
                    "decoys_above": b.decoys_above}
                for s, b in ch.best.items()
            }
            channels[name] = entry
        rules = None
        if self.contract is not None:
            c = self.contract
            rules = {
                "candidates": c.n_candidates, "hard": len(c.hard),
                "band": len(c.band), "discarded": len(c.discarded),
                "pruned_by_decoy": len(c.pruned_by_decoy),
                "violations": [
                    {"rule": str(v.rule), "n_violating": v.n_violating,
                     "n_total": v.n_total, "rate": v.rate,
                     "example": v.examples[0] if v.examples else None}
                    for v in self.violations
                ],
                "for_review": [str(r) for r, _, _ in c.band],
            }
        return {
            "n_inputs": self.n_inputs, "n_flagged": self.n_flagged,
            "k": self.k, "q": self.q, "floor": _floor(self.q),
            "short_clouds": self.short_clouds,
            "provenance": self.provenance,
            "findings": [{"input_id": f.input_id, "stratum": f.stratum,
                          "channels": dict(f.channels)} for f in self.findings],
            "channels": channels,
            "rules": rules,
            "notes": list(self.notes),
            "cost": dict(self.cost),
        }


PARTITION_STATS = ("mode_share", "dispersion", "novel_mode")


def _pairwise(
    clouds_a: dict[str, list[str]],
    clouds_other: dict[str, list[str]],
    ids: Sequence[str],
    predicate: EquivalencePredicate | None,
    cost: dict,
) -> dict[str, np.ndarray]:
    """All three partition statistics for every input, from one clustering each.

    The three statistics read the same partition, so it is derived once per
    (input, arm pair) and shared. An earlier version re-clustered once per
    statistic and counted only the first pass, which under-reported the
    dominant cost of the detector by a factor of three (ENG-003). The cost
    recorded here is what was spent.
    """
    out: dict[str, list[float]] = {s: [] for s in PARTITION_STATS}
    for iid in ids:
        a, b = clouds_a[iid], clouds_other[iid]
        ma, mb, joint = cluster_jointly(a, b, predicate)
        cost["predicate_calls"] += joint.predicate_calls
        cost["clusterings"] += 1
        cost["samples_clustered"] += joint.n_samples
        cost["distinct_after_normalisation"] += joint.distinct_after_normalisation
        out["mode_share"].append(stats.tv_distance(ma, mb))
        out["dispersion"].append(stats.dispersion_ratio(ma, mb))
        out["novel_mode"].append(stats.novel_mode_mass(ma, mb))
    return {s: np.asarray(v, dtype=float) for s, v in out.items()}


def detect(
    recording: Recording,
    predicate: EquivalencePredicate | None = None,
    nli_channel=None,
    embedder=None,
    q: float = 0.10,
    gate_threshold: float = 0.25,
) -> Report:
    """Run every available channel over a three-arm recording."""
    ids = list(dict.fromkeys(recording.input_ids))
    ca = recording.clouds("A")
    cp = recording.clouds("A_prime")
    cb = recording.clouds("B")

    usable = [i for i in ids if ca.get(i) and cp.get(i) and cb.get(i)]
    notes: list[str] = []
    if len(usable) < len(ids):
        notes.append(
            f"{len(ids) - len(usable)} of {len(ids)} inputs dropped: an arm "
            "returned nothing usable. Dropped, not imputed — a missing arm has "
            "no decoy and therefore no calibrated threshold."
        )
    ids = usable

    strata_map = strata_from_baseline({i: ca[i] for i in ids})
    strata = [strata_map[i] for i in ids]

    channels: dict[str, ChannelResult] = {}

    # The equivalence predicate is the dominant cost of the whole detector, so
    # it is counted rather than estimated, and every clustering is counted
    # because every one is now real work: one per input per arm pair, shared
    # by the three partition statistics (ENG-003). This number is the evidence
    # for or against distilling the predicate later.
    cost = {
        "predicate_calls": 0,
        "clusterings": 0,
        "samples_clustered": 0,
        "distinct_after_normalisation": 0,
    }
    targets = _pairwise(ca, cb, ids, predicate, cost)
    decoys = _pairwise(ca, cp, ids, predicate, cost)
    for stat in PARTITION_STATS:
        channels[stat] = ChannelResult(stat, targets[stat], decoys[stat])

    # Embedding displacement, gated. Ungated it is anti-correlated with meaning
    # change (MTH-011), so a blocked gate is the channel working, not failing.
    gate: dict[str, GateVerdict] = {
        i: embedding_gate(ca[i], cb[i], gate_threshold) for i in ids
    }
    blocked = sum(1 for v in gate.values() if not v.allowed)
    if embedder is None:
        channels["embedding"] = ChannelResult(
            "embedding", np.empty(0), np.empty(0), skipped="no embedder supplied"
        )
    elif blocked > len(ids) / 2:
        channels["embedding"] = ChannelResult(
            "embedding",
            np.empty(0),
            np.empty(0),
            skipped=(
                f"surface drift exceeded {gate_threshold} on {blocked}/{len(ids)} "
                "inputs; the channel is anti-correlated with meaning change in "
                "this regime (MTH-011)"
            ),
        )
    else:
        t, d = [], []
        for i in ids:
            if gate[i].allowed:
                t.append(_embed_dist(embedder, ca[i], cb[i]))
                d.append(_embed_dist(embedder, ca[i], cp[i]))
            else:
                t.append(0.0)
                d.append(0.0)
        channels["embedding"] = ChannelResult(
            "embedding", np.asarray(t), np.asarray(d)
        )
        if blocked:
            notes.append(
                f"embedding channel suppressed on {blocked}/{len(ids)} inputs "
                "whose surface drifted past the gate"
            )

    if nli_channel is not None:
        for name, idx in (("nli_contradiction", "contradiction"),
                          ("nli_directional", "directional")):
            t = _nli_score(nli_channel, ca, cb, ids, idx)
            d = _nli_score(nli_channel, ca, cp, ids, idx)
            channels[name] = ChannelResult(name, t, d)
    else:
        for name in ("nli_contradiction", "nli_directional"):
            channels[name] = ChannelResult(
                name, np.empty(0), np.empty(0), skipped="no NLI model supplied"
            )

    # Select per channel. The directional channel is two-tailed: the sign names
    # the fault, so folding it to one tail would discard that (MTH-022).
    flagged_by: dict[str, set[str]] = {}
    for name, ch in channels.items():
        if ch.skipped or ch.targets.size == 0:
            continue
        if name == "nli_directional":
            t_sel, d_sel = np.abs(ch.targets), np.abs(ch.decoys)
        else:
            t_sel, d_sel = ch.targets, ch.decoys
        sel = fdr.select_stratified(t_sel, d_sel, strata, q)
        ch.selection = sel
        flagged_by[name] = {ids[j] for j in np.flatnonzero(sel.flagged)}
        # How close each stratum came, so the report can say why it reported
        # nothing when it did (ENG-007). Same effective strata as the selection.
        eff = np.array(sel.strata)
        for stratum in sel.per_stratum:
            m = eff == stratum
            best = fdr.best_achievable(t_sel[m], d_sel[m])
            if best is not None:
                ch.best[stratum] = best

    findings: list[Finding] = []
    for j, iid in enumerate(ids):
        hits = {n: float(channels[n].targets[j]) for n, s in flagged_by.items() if iid in s}
        if hits:
            findings.append(Finding(iid, strata_map[iid], hits))
    findings.sort(key=lambda f: (-len(f.channels), f.input_id))

    # Structural conformance over the pooled corpus: the contract is a property
    # of the system, not of one input.
    pool_a = [o for i in ids for o in ca[i]]
    pool_p = [o for i in ids for o in cp[i]]
    pool_b = [o for i in ids for o in cb[i]]
    contract = conformance.induce(pool_a, pool_p) if pool_a else None
    violations = conformance.check(contract, pool_b) if contract else []

    if recording.spans_utc_date_boundary():
        notes.append(
            "this recording crosses midnight UTC. At least one common chat "
            "template interpolates the date into a hidden system prompt, so the "
            "arms may differ by a prompt edit nobody made (BCH-009)."
        )

    short_clouds = sum(
        1 for i in ids if min(len(ca[i]), len(cp[i]), len(cb[i])) < recording.k
    )

    return Report(
        findings=findings,
        channels=channels,
        violations=violations,
        contract=contract,
        gate=gate,
        n_inputs=len(ids),
        q=q,
        notes=notes,
        cost=cost,
        k=recording.k,
        short_clouds=short_clouds,
    )


def _embed_dist(embedder, a: Sequence[str], b: Sequence[str]) -> float:
    """Cosine distance between the two clouds' centroids.

    A centroid is the wrong summary for a multimodal cloud (MTH-005) and this
    knows it — which is one more reason the embedding channel is gated and
    secondary rather than primary. It is kept because it is nearly free once
    the outputs are already encoded, and because the decoy arm bounds how much
    damage a poor statistic can do: a noisy channel produces noisy decoys and
    therefore a high threshold and no findings.
    """
    ea = embedder.model.encode([normalise(x) for x in a], normalize_embeddings=True)
    eb = embedder.model.encode([normalise(x) for x in b], normalize_embeddings=True)
    ca = np.asarray(ea).mean(0)
    cb = np.asarray(eb).mean(0)
    na, nb = np.linalg.norm(ca), np.linalg.norm(cb)
    if na == 0 or nb == 0:
        return 0.0
    return float(1.0 - np.dot(ca / na, cb / nb))


def _nli_score(nli, ca, cb, ids, which: str) -> np.ndarray:
    out = []
    for iid in ids:
        a, b = ca[iid], cb[iid]
        n = min(len(a), len(b))
        scores = nli.score_both(a[:n], b[:n])[which]
        out.append(float(np.mean(scores)))
    return np.asarray(out, dtype=float)
