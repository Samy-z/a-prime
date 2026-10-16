"""What a silent agent cell looks like without the judging model.

`scripts/diagnose_channels.py` is the diagnosis of record for a cell that
flags nothing, and it needs the NLI judge. This script is the part of that
reading that needs no model, for a machine that cannot load one, and for the
one question the judge cannot answer anyway: how much of an agent cell's
run-to-run variation is in the decision itself.

An agent cell's output is a decision line (APPROVE, DECLINE or ESCALATE) with
a rationale. The rationale is free text and is where the judge earns its
keep; the decision is three tokens and needs no judge at all. So this reads
the decision out of every sample and asks the detector's own question of it:
per input, how far does the candidate's mix of decisions sit from the
baseline's, and how far does the second baseline run sit from the first?
That second number is the system's own variation at the level a user of an
agent cares about, and if it is as wide as the first, no statistic over the
rationale can be expected to report the input at the budget.

It also runs the shipped exact-match configuration of the three partition
statistics (no predicate, no judge) over the same recording, so the reading
has both ends: the decision alone, and the whole text with no paraphrase
merging. The NLI diagnosis sits between the two and is still the one that
classifies the cell.

Writes `<cell>.<hash>.decisions.json` beside the checkpoint so that every
number quoted from it traces to a committed file.
"""

from __future__ import annotations

import json
import re
import statistics as st
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np  # noqa: E402

from aprime.detect import PARTITION_STATS, detect  # noqa: E402
from aprime.fdr import best_achievable  # noqa: E402
from aprime.normalize import normalise  # noqa: E402
from aprime.recorder import Recording, load_checkpoint  # noqa: E402
from aprime.stats import tv_distance  # noqa: E402

DECISIONS = ("APPROVE", "DECLINE", "ESCALATE")
_DECISION = re.compile(r"\b(APPROVE|DECLINE|ESCALATE)\b")


def decision(text: str) -> str:
    """The first decision token in the text, or NONE.

    Case-sensitive on purpose: the cells' prompts ask for the token in upper
    case, and a lower-case "decline" inside a rationale is not the decision.
    """
    m = _DECISION.search(text or "")
    return m.group(1) if m else "NONE"


def majority(cloud: list[str]) -> str:
    if not cloud:
        return "NONE"
    counts = Counter(decision(x) for x in cloud)
    # Ties resolve alphabetically so the answer does not depend on sample order.
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[0][0]


def load_activation(cp: Path) -> dict[str, bool]:
    """Per-input activation from the study's per-sample store, if present."""
    sib = Path(str(cp)[: -len(".jsonl")] + ".activation.json")
    if not sib.exists():
        return {}
    raw = json.loads(sib.read_text(encoding="utf-8"))
    out: dict[str, bool] = {}
    for key, hit in raw.items():
        iid = key.rpartition("#")[0] or key
        out[iid] = out.get(iid, False) or bool(hit)
    return out


def describe(vals) -> dict:
    v = sorted(float(x) for x in vals)
    if not v:
        return {"n": 0}
    return {"n": len(v), "min": round(v[0], 4), "median": round(st.median(v), 4),
            "max": round(v[-1], 4)}


def analyse(cp: Path, q: float = 0.10) -> dict:
    samples, _, _ = load_checkpoint(cp)
    if not samples:
        raise SystemExit(f"no complete triples in {cp}")
    k = max(s.sample_idx for s in samples) + 1
    ids = list(dict.fromkeys(s.input_id for s in samples))
    rec = Recording(samples=samples, k=k, input_ids=ids)
    clouds = {arm: rec.clouds(arm) for arm in ("A", "A_prime", "B")}
    activation = load_activation(cp)
    fired = [i for i in ids if activation.get(i)]
    quiet = [i for i in ids if i in activation and not activation[i]]

    # --- the decision alone -------------------------------------------------
    def mix(cloud: list[str]) -> list[str]:
        # The decision token is the mode label; tv_distance reads the shares.
        return [decision(x) for x in cloud]

    targets, decoys = [], []
    flips = {"A_vs_A_prime": 0, "A_vs_B_fired": 0, "A_vs_B_quiet": 0}
    token_counts = {arm: Counter() for arm in clouds}
    for iid in ids:
        a, ap, b = clouds["A"][iid], clouds["A_prime"][iid], clouds["B"][iid]
        for arm, cloud in (("A", a), ("A_prime", ap), ("B", b)):
            token_counts[arm].update(decision(x) for x in cloud)
        targets.append(tv_distance(mix(a), mix(b)))
        decoys.append(tv_distance(mix(a), mix(ap)))
        if majority(a) != majority(ap):
            flips["A_vs_A_prime"] += 1
        if majority(a) != majority(b):
            if iid in fired:
                flips["A_vs_B_fired"] += 1
            elif iid in quiet:
                flips["A_vs_B_quiet"] += 1
    t, d = np.asarray(targets, float), np.asarray(decoys, float)
    order = {iid: n for n, iid in enumerate(ids)}
    fi = np.array([order[i] for i in fired], dtype=int)
    qi = np.array([order[i] for i in quiet], dtype=int)
    best = best_achievable(t, d)
    decision_block = {
        "tokens_per_arm": {arm: dict(c) for arm, c in token_counts.items()},
        "targets_fired": describe(t[fi]) if len(fi) else {"n": 0},
        "targets_quiet": describe(t[qi]) if len(qi) else {"n": 0},
        "decoys": describe(d),
        "decoys_zero": int((d <= 0).sum()),
        "targets_fired_zero": int((t[fi] <= 0).sum()) if len(fi) else 0,
        "best_estimate": round(best.estimate, 4) if best else None,
        "best_cut": round(best.cut, 4) if best else None,
        "targets_above": best.targets_above if best else None,
        "decoys_above": best.decoys_above if best else None,
        "majority_flips": {**flips, "inputs": len(ids), "fired": len(fired),
                           "quiet": len(quiet)},
        "scores": {"targets": [round(float(x), 4) for x in t],
                   "decoys": [round(float(x), 4) for x in d]},
    }

    # --- the whole text, exact match, no judge ------------------------------
    rep = detect(rec, predicate=None, nli_channel=None, q=q)
    exact = {"cost": rep.cost, "short_clouds": rep.short_clouds, "channels": {}}
    for name in PARTITION_STATS:
        ch = rep.channels[name]
        tt, dd = np.asarray(ch.targets, float), np.asarray(ch.decoys, float)
        b = best_achievable(tt, dd)
        exact["channels"][name] = {
            "flagged": ch.n_flagged,
            "best_estimate": round(b.estimate, 4) if b else None,
            "best_cut": round(b.cut, 4) if b else None,
            "targets_above": b.targets_above if b else None,
            "decoys_above": b.decoys_above if b else None,
            "decoys_at_top_value": int((dd >= 1.0 - 1e-9).sum()),
            "targets_fired_at_top_value": int((tt[fi] >= 1.0 - 1e-9).sum()) if len(fi) else 0,
        }
    distinct = []
    for arm in clouds:
        for cloud in clouds[arm].values():
            if cloud:
                distinct.append(len({normalise(x) for x in cloud}) / len(cloud))
    exact["within_cloud_distinct_fraction_mean"] = round(st.mean(distinct), 4) if distinct else None

    live = {"samples": len(samples), "errored_dropped": sum(1 for s in samples if s.error),
            "empty_kept": sum(1 for s in samples if s.error is None and not (s.output or "").strip()),
            "finish_reasons": dict(Counter(str(s.finish_reason) for s in samples))}

    return {"checkpoint": cp.name, "k": k, "n_inputs": len(ids), "fired": len(fired),
            "quiet": len(quiet), "q": q, "live": live, "decision": decision_block,
            "exact_match": exact}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: agent_decision_variation.py <checkpoint.jsonl> [...]")
        return 2
    for arg in argv:
        cp = Path(arg)
        out = analyse(cp)
        dec, ex = out["decision"], out["exact_match"]
        print(f"{cp.name}: {out['live']['samples']} live samples, k={out['k']}, "
              f"{out['n_inputs']} inputs, {out['fired']} fired, {out['quiet']} quiet; "
              f"{out['live']['errored_dropped']} errored samples dropped")
        print(f"  decision only: targets fired {dec['targets_fired']}; "
              f"decoys {dec['decoys']}; {dec['decoys_zero']} decoys at 0; "
              f"best estimate {dec['best_estimate']} at cut {dec['best_cut']} "
              f"({dec['targets_above']} targets, {dec['decoys_above']} decoys above)")
        mf = dec["majority_flips"]
        print(f"  majority decision differs: A vs A' {mf['A_vs_A_prime']} of {mf['inputs']}; "
              f"A vs B {mf['A_vs_B_fired']} of {mf['fired']} fired, "
              f"{mf['A_vs_B_quiet']} of {mf['quiet']} quiet")
        for name, ch in ex["channels"].items():
            print(f"  exact {name}: best {ch['best_estimate']} at {ch['best_cut']} "
                  f"({ch['targets_above']} t, {ch['decoys_above']} d); "
                  f"decoys at top value {ch['decoys_at_top_value']} of {out['n_inputs']}")
        print(f"  within-cloud distinct fraction, exact after normalisation: "
              f"{ex['within_cloud_distinct_fraction_mean']}")
        dest = cp.with_name(cp.name[: -len(".jsonl")] + ".decisions.json")
        dest.write_text(json.dumps(out, indent=1), encoding="utf-8")
        print(f"  wrote {dest.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
