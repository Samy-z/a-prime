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


@dataclass
class ChannelResult:
    name: str
    targets: np.ndarray
    decoys: np.ndarray
    selection: fdr.StratifiedSelection | None = None
    skipped: str | None = None

    @property
    def n_flagged(self) -> int:
        return 0 if self.selection is None else self.selection.n_discoveries


@dataclass
class Finding:
    input_id: str
    stratum: str
    channels: dict[str, float] = field(default_factory=dict)

    def __str__(self) -> str:
        ch = ", ".join(f"{k}={v:+.3f}" for k, v in sorted(self.channels.items()))
        return f"{self.input_id} [{self.stratum}] {ch}"


@dataclass
class Report:
    findings: list[Finding]
    channels: dict[str, ChannelResult]
    violations: list[conformance.Violation]
    contract: conformance.InducedContract | None
    gate: dict[str, GateVerdict]
    n_inputs: int
    q: float
    notes: list[str] = field(default_factory=list)

    @property
    def n_flagged(self) -> int:
        return len(self.findings)

    def text(self) -> str:
        lines = [
            f"a-prime report: {self.n_flagged} of {self.n_inputs} inputs flagged "
            f"at q={self.q}",
            "",
            "channels:",
        ]
        for name, ch in sorted(self.channels.items()):
            if ch.skipped:
                lines.append(f"  {name:<28} skipped - {ch.skipped}")
            else:
                s = ch.selection
                lines.append(
                    f"  {name:<28} {ch.n_flagged:>4} flagged   "
                    + (s.summary() if s else "")
                )
        if self.contract is not None:
            lines += ["", f"conformance: {self.contract.summary()}"]
            for v in self.violations:
                lines.append(
                    f"  VIOLATED {v.rule}  {v.n_violating}/{v.n_total} "
                    f"({v.rate:.0%}) e.g. {v.examples[0][:80]!r}"
                    if v.examples
                    else f"  VIOLATED {v.rule}  {v.rate:.0%}"
                )
            if self.contract.band:
                lines.append(
                    f"  {len(self.contract.band)} rules surfaced for review "
                    "(held often but not always; see contract.band)"
                )
        if self.notes:
            lines += ["", "notes:"] + [f"  {n}" for n in self.notes]
        if self.findings:
            lines += ["", "flagged inputs:"]
            lines += [f"  {f}" for f in self.findings[:25]]
            if len(self.findings) > 25:
                lines.append(f"  ... and {len(self.findings) - 25} more")
        return "\n".join(lines)


def _pairwise(
    clouds_a: dict[str, list[str]],
    clouds_other: dict[str, list[str]],
    ids: Sequence[str],
    predicate: EquivalencePredicate | None,
    stat: str,
) -> np.ndarray:
    out = []
    for iid in ids:
        a, b = clouds_a[iid], clouds_other[iid]
        ma, mb, _ = cluster_jointly(a, b, predicate)
        if stat == "mode_share":
            out.append(stats.tv_distance(ma, mb))
        elif stat == "dispersion":
            out.append(stats.dispersion_ratio(ma, mb))
        elif stat == "novel_mode":
            out.append(stats.novel_mode_mass(ma, mb))
        else:  # pragma: no cover
            raise ValueError(stat)
    return np.asarray(out, dtype=float)


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

    for stat in ("mode_share", "dispersion", "novel_mode"):
        t = _pairwise(ca, cb, ids, predicate, stat)
        d = _pairwise(ca, cp, ids, predicate, stat)
        channels[stat] = ChannelResult(stat, t, d)

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
            sel = fdr.select_stratified(np.abs(ch.targets), np.abs(ch.decoys), strata, q)
        else:
            sel = fdr.select_stratified(ch.targets, ch.decoys, strata, q)
        ch.selection = sel
        flagged_by[name] = {ids[j] for j in np.flatnonzero(sel.flagged)}

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

    return Report(
        findings=findings,
        channels=channels,
        violations=violations,
        contract=contract,
        gate=gate,
        n_inputs=len(ids),
        q=q,
        notes=notes,
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
