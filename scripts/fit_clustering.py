"""Fit the semantic-equivalence threshold against the probe suite.

The clustering predicate asks "do these two outputs mean the same thing", and
that question has a threshold in it. Choosing it by eye would be exactly the
kind of free knob MTH-009 warns about, so it is fitted against cases where the
answer is known by construction: probe pairs labelled PRESERVING are equivalent,
BREAKING pairs are not.

Scored by balanced accuracy, and the whole grid is printed rather than just the
argmax — a flat optimum means the threshold barely matters, which is useful to
know, and a sharp one means it is load-bearing and fragile.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.net import enable_os_truststore  # noqa: E402

enable_os_truststore()

from aprime.clustering import NLIEquivalence, cluster_jointly, fit_threshold  # noqa: E402
from aprime.normalize import normalise  # noqa: E402
from aprime.probes import channels, pairs  # noqa: E402


def main() -> int:
    pair_list = pairs.build_pairs()
    eq = [(normalise(p.text_a), normalise(p.text_b))
          for p in pair_list if p.relation == "PRESERVING"]
    diff = [(normalise(p.text_a), normalise(p.text_b))
            for p in pair_list if p.relation == "BREAKING"]
    print(f"equivalent pairs {len(eq)}   different pairs {len(diff)}")

    spec = next(s for s in channels.NLI_MODELS if s.key == "deberta_mnli")
    nli = channels.NLIChannel(spec)
    print(f"model {spec.hub_id}\nrevision {nli.revision}\n")

    best, info = fit_threshold(nli, eq, diff)
    print(f"{'threshold':>10} {'balanced acc':>13}")
    for t, s in sorted(info["balanced_accuracy"].items()):
        mark = "  <-- best" if t == best else ""
        print(f"{t:>10.2f} {s:>13.3f}{mark}")
    print(f"\nbest threshold {best:.2f}")

    # Per-category breakdown at the chosen operating point: which preserving
    # perturbations does the predicate still refuse to merge, and which breaking
    # ones does it wrongly merge?
    pred = NLIEquivalence(nli, threshold=best)
    by_cat: dict[str, list[bool]] = {}
    B = 64
    for i in range(0, len(pair_list), B):
        chunk = pair_list[i : i + B]
        verdicts = pred.equivalent(
            [(normalise(p.text_a), normalise(p.text_b)) for p in chunk]
        )
        for p, v in zip(chunk, verdicts):
            by_cat.setdefault(f"{p.relation[:4]} {p.category}", []).append(v)

    print(f"\n{'category':<24} {'n':>4} {'merged':>8}   (PRES should merge, BREA should not)")
    for cat in sorted(by_cat):
        vals = by_cat[cat]
        print(f"{cat:<24} {len(vals):>4} {sum(vals)/len(vals):>7.1%}")

    out = {
        "fitted_utc": datetime.now(timezone.utc).isoformat(),
        "hub_id": spec.hub_id,
        "revision": nli.revision,
        "threshold": best,
        "n_equivalent": len(eq),
        "n_different": len(diff),
        "grid": {str(k): v for k, v in info["balanced_accuracy"].items()},
        "per_category_merge_rate": {k: sum(v) / len(v) for k, v in by_cat.items()},
    }
    path = ROOT / "results" / "clustering_threshold.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nwrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
