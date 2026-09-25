"""Run the probe suite and emit the blind-spot map.

    python scripts/run_probes.py            # all channels
    python scripts/run_probes.py --dry-run  # build pairs only, no models

Every run writes a JSON record under results/ carrying a run id, a config hash,
and the resolved model revisions, so any number quoted later can be traced back
to the exact weights and the exact pair set that produced it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Must run before anything opens an HTTPS connection; see aprime/net.py.
from aprime.net import enable_os_truststore  # noqa: E402

enable_os_truststore()

from aprime.normalize import normalise  # noqa: E402
from aprime.probes import analysis, channels, pairs  # noqa: E402


def config_hash(pair_list, specs) -> str:
    h = hashlib.sha256()
    for p in pair_list:
        h.update(f"{p.seed_id}|{p.shape}|{p.category}|{p.text_a}|{p.text_b}".encode())
    for s in specs:
        h.update(f"{s.key}|{s.hub_id}|{s.prefix}".encode())
    return h.hexdigest()[:16]


def fmt_table(results, thresholds) -> str:
    lines = []
    by_shape: dict = {}
    for r in results:
        by_shape.setdefault(r.shape, []).append(r)
    for shape, rows in by_shape.items():
        thr = thresholds.get(shape or "__global__", float("nan"))
        lines.append(f"\n  shape={shape or 'ALL'}   threshold@5%FPR={thr:.4f}")
        lines.append(f"    {'category':<18} {'n':>4} {'detect':>7} {'95% CI':>16} {'AUC':>6}")
        for r in sorted(rows, key=lambda x: (-x.rate, x.category)):
            ci = f"[{r.lo:.2f},{r.hi:.2f}]"
            a = "  --  " if r.auc != r.auc else f"{r.auc:.3f}"
            lines.append(
                f"    {r.category:<18} {r.n:>4} {r.rate:>6.1%} {ci:>16} {a:>6}"
            )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="build pairs, skip models")
    ap.add_argument("--fpr", type=float, default=0.05)
    ap.add_argument("--only", default=None, help="comma-separated model keys")
    ap.add_argument("--normalise", action="store_true",
                    help="normalise both arms before scoring (D4)")
    args = ap.parse_args()

    pair_list = pairs.build_pairs()
    bad = pairs.degenerate(pair_list)
    print(f"pairs: {len(pair_list)}")
    print(f"  seeds      {len({p.seed_id for p in pair_list})}")
    print(f"  domains    {sorted({p.domain for p in pair_list})}")
    print(f"  shapes     {sorted({p.shape for p in pair_list})}")
    print(f"  categories {len({p.category for p in pair_list})}")
    from collections import Counter as _C
    rc = _C(p.relation for p in pair_list)
    print("  " + "  ".join(f"{k.lower()} {v}" for k, v in sorted(rc.items())))
    wc = [p.words_a for p in pair_list]
    print(f"  words/arm  median {int(np.median(wc))}  range {min(wc)}-{max(wc)}")

    if bad:
        print(f"\nFATAL: {len(bad)} degenerate pairs (identical arms). "
              f"First: {bad[0].seed_id}/{bad[0].shape}/{bad[0].category}")
        return 1
    print("  degenerate 0  (ok)")

    if args.dry_run:
        return 0

    specs = channels.EMBEDDING_MODELS + channels.NLI_MODELS
    if args.only:
        keep = set(args.only.split(","))
        specs = [s for s in specs if s.key in keep]

    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    cfg = config_hash(pair_list, specs)
    if args.normalise:
        cfg = "norm-" + cfg
    print(f"\nrun_id={run_id}  config={cfg}")

    if args.normalise:
        texts_a = [normalise(p.text_a) for p in pair_list]
        texts_b = [normalise(p.text_b) for p in pair_list]
        print("  normalisation: ON")
    else:
        texts_a = [p.text_a for p in pair_list]
        texts_b = [p.text_b for p in pair_list]
    relations = [p.relation for p in pair_list]
    cats = [p.category for p in pair_list]
    shapes = [p.shape for p in pair_list]

    record: dict = {
        "run_id": run_id,
        "config_hash": cfg,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "platform": platform.platform(),
        "n_pairs": len(pair_list),
        "fpr_budget": args.fpr,
        "normalised": bool(args.normalise),
        "channels": {},
    }

    for spec in specs:
        print(f"\n=== {spec.key} ({spec.hub_id}) ===")
        try:
            if spec.kind == "embedding":
                ch = channels.EmbeddingChannel(spec)
                emitted = {spec.key: ch.score(texts_a, texts_b)}
            else:
                ch = channels.NLIChannel(spec)
                # One pair of forward passes, several logical channels.
                emitted = {
                    f"{spec.key}:{name}": vals
                    for name, vals in ch.score_both(texts_a, texts_b).items()
                }
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED: {type(exc).__name__}: {exc}")
            record["channels"][spec.key] = {"error": f"{type(exc).__name__}: {exc}"}
            continue

        print(f"  revision {ch.revision}")

        for key, scores in emitted.items():
            sep = analysis.separability(scores, relations)
            print(f"\n  -- channel {key} --")
            print(f"  separability (breaking vs preserving, pooled AUC) = {sep:.3f}")

            glob, thr_g = analysis.evaluate(
                scores, relations, cats, shapes, args.fpr, per_shape_threshold=False
            )
            per, thr_s = analysis.evaluate(
                scores, relations, cats, shapes, args.fpr, per_shape_threshold=True
            )
            print(fmt_table(glob, thr_g))

            record["channels"][key] = {
                "hub_id": spec.hub_id,
                "revision": ch.revision,
                "prefix": spec.prefix,
                "separability_auc": float(sep),
                "thresholds_global": {k: float(v) for k, v in thr_g.items()},
                "thresholds_per_shape": {k: float(v) for k, v in thr_s.items()},
                "scores": [float(x) for x in scores],
                "results_global": [vars(r) for r in glob],
                "results_per_shape": [vars(r) for r in per],
            }

    record["pairs"] = [
        {
            "seed_id": p.seed_id,
            "domain": p.domain,
            "shape": p.shape,
            "category": p.category,
            "relation": p.relation,
            "words_a": p.words_a,
        }
        for p in pair_list
    ]

    out = ROOT / "results" / f"probes_{run_id}_{cfg}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
