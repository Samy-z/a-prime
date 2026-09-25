"""Severity titration: detection rate against how hard the fault was pushed.

For each injection and each rung of its severity ladder, wrap the candidate arm,
run the detector, and score against **activation** — the inputs the fault
actually touched — never against the cell label.

Two things this is for.

**Minimum detectable severity per fault class.** BCH-004 requires it, and it is
the honest form of a coverage claim: not "we catch omission" but "we catch
omission down to this rung, and below it we do not".

**A monotonicity check on the harness.** Detection that does not rise with
severity is a harness bug before it is a finding. A non-monotone curve here
means the injection is not doing what its name says.

All three arms share one behaviour table, so the injected fault is the only
difference between B and the baseline. That is what makes activation the exact
ground truth rather than an approximation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.net import enable_os_truststore  # noqa: E402

enable_os_truststore()

from aprime.detect import detect  # noqa: E402
from aprime.faults import FaultInjector, FaultSpec  # noqa: E402
from aprime.provenance import capture, corpus_fingerprint  # noqa: E402
from aprime.recorder import iter_invocations, record  # noqa: E402
from aprime.stub import StubSystem, realistic_table  # noqa: E402

N_INPUTS = 120
K = 12
Q = 0.10
SEVERITIES = (0.1, 0.25, 0.5, 0.9)

LADDER = {
    "omission": "F5",
    "output_truncation": "F12",
    "script_corruption": "F7",
    "unicode_escape": "F7",
    "refusal": "F13",
    "verbosity": "F9",
}


def run_cell(name: str, fclass: str, severity: float, seed: int,
             predicate=None, n_inputs=N_INPUTS, k=K) -> dict:
    ids = [f"in{i:03d}" for i in range(n_inputs)]
    table = realistic_table(ids)
    a = StubSystem("sut", "A", dict(table), seed=seed)
    ap = StubSystem("sut", "A_prime", dict(table), seed=seed + 101)
    b = StubSystem("sut", "B", dict(table), seed=seed + 202)
    spec = FaultSpec(fclass, name, severity, regime="B0", seed=seed)
    b_broken = FaultInjector(b, spec)

    rec = record(iter_invocations(ids), {"A": a, "A_prime": ap, "B": b_broken}, k=k)
    rep = detect(rec, predicate=predicate, q=Q)

    touched = b_broken.log.touched
    flagged = {f.input_id for f in rep.findings}
    untouched = set(ids) - touched
    return {
        "fault": name,
        "class": fclass,
        "severity": severity,
        "activated": len(touched),
        "recall": len(flagged & touched) / len(touched) if touched else float("nan"),
        "false_on_untouched": len(flagged & untouched) / len(untouched) if untouched else 0.0,
        "n_flagged": len(flagged),
        "channels": {
            n: c.n_flagged for n, c in rep.channels.items() if not c.skipped
        },
        "violations": [str(v.rule) for v in rep.violations],
    }


def main() -> int:
    ap_ = argparse.ArgumentParser()
    ap_.add_argument("--semantic", action="store_true",
                     help="cluster with the NLI predicate instead of exact match")
    ap_.add_argument("--inputs", type=int, default=N_INPUTS)
    ap_.add_argument("--k", type=int, default=K)
    args = ap_.parse_args()

    predicate = None
    pred_id = "exact-match@builtin"
    severities = SEVERITIES
    if args.semantic:
        from aprime.clustering import NLIEquivalence
        from aprime.probes import channels as ch_mod
        spec = next(s for s in ch_mod.NLI_MODELS if s.key == "deberta_mnli")
        nli = ch_mod.NLIChannel(spec)
        predicate = NLIEquivalence(nli, threshold=0.7)
        pred_id = f"{spec.hub_id}@{nli.revision}/thr0.7"
        severities = (0.1, 0.5, 0.9)

    prov = capture(
        instruments={"predicate": pred_id},
        params={"k": args.k, "q": Q, "n_inputs": args.inputs,
                "severities": list(severities), "semantic": args.semantic},
        corpus=corpus_fingerprint([f"in{i:03d}" for i in range(args.inputs)]),
        notes={"purpose": "severity titration on the stub"},
    )
    print(f"run {prov.run_id}  config {prov.config_hash}  "
          f"git {str(prov.git_commit)[:8]}{'  DIRTY' if prov.git_dirty else ''}")
    print(f"{N_INPUTS} inputs, k={K}, q={Q}, all arms share one behaviour table\n")

    header = f"{'fault':<20} {'cls':<4} {'sev':>5} {'fired':>6} {'recall':>8} {'FP':>7}  channels"
    print(header)
    print("-" * len(header))

    rows = []
    for name, fclass in LADDER.items():
        for sev in severities:
            r = run_cell(name, fclass, sev, seed=41, predicate=predicate,
                         n_inputs=args.inputs, k=args.k)
            rows.append(r)
            ch = ",".join(f"{k}:{v}" for k, v in sorted(r["channels"].items()) if v)
            rec_s = "  n/a " if r["recall"] != r["recall"] else f"{r['recall']:>7.1%}"
            print(f"{name:<20} {fclass:<4} {sev:>5.2f} {r['activated']:>6} "
                  f"{rec_s} {r['false_on_untouched']:>6.1%}  {ch or '-'}")
        print()

    out = ROOT / "results" / f"titration_{prov.run_id}_{prov.config_hash}.json"
    out.write_text(json.dumps({"provenance": prov.__dict__, "rows": rows},
                              indent=2, default=str), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")

    print("\nmonotonicity check (recall must not fall as severity rises):")
    for name in LADDER:
        rs = [r["recall"] for r in rows if r["fault"] == name]
        rs = [0.0 if x != x else x for x in rs]
        ok = all(b >= a - 0.05 for a, b in zip(rs, rs[1:]))
        print(f"  {name:<20} {['%.2f' % x for x in rs]}  "
              f"{'ok' if ok else 'NON-MONOTONE -- harness bug before finding'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
