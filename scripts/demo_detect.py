"""Run the full detector against a synthetic system and print the report.

Model-free: mode-share, dispersion, novel-mode and structural conformance need
no models, which is the whole structured-output path. The NLI and embedding
channels report themselves as skipped rather than silently doing nothing.
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.detect import detect                      # noqa: E402
from aprime.provenance import capture, corpus_fingerprint  # noqa: E402
from aprime.recorder import iter_invocations, record   # noqa: E402
from aprime.stub import build_arms                     # noqa: E402

N, K, Q = 300, 12, 0.10
ids = [f"in{i:03d}" for i in range(N)]
affected = set(random.Random(7).sample(ids, 30))

prov = capture(
    instruments={"predicate": "exact-match@builtin"},
    params={"k": K, "q": Q, "n_inputs": N, "perturbation": "mode_share@0.9"},
    corpus=corpus_fingerprint(ids),
    notes={"purpose": "demo of the composed detector on a stub"},
)
print(f"run {prov.run_id}  config {prov.config_hash}  git {str(prov.git_commit)[:8]}"
      f"{'  DIRTY' if prov.git_dirty else ''}\n")

a, ap, b = build_arms(ids, affected, "mode_share", strength=0.9, seed=7)
rec = record(iter_invocations(ids), {"A": a, "A_prime": ap, "B": b}, k=K)
print(f"recorded {len(rec.samples)} samples, interleaving gap "
      f"{rec.interleaving_gap()}, span {rec.wallclock_span_s():.1f}s\n")

rep = detect(rec, q=Q)
print(rep.text())

flagged = {f.input_id for f in rep.findings}
if flagged:
    print(f"\nground truth (a stub privilege, never available in production):")
    print(f"  {len(flagged & affected)}/{len(flagged)} flagged inputs were genuinely "
          f"changed -> realised FDR {len(flagged - affected) / len(flagged):.3f} "
          f"against q={Q}")
    print(f"  recall {len(flagged & affected)}/{len(affected)} "
          f"= {len(flagged & affected) / len(affected):.0%}")
