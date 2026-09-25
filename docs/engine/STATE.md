# engine — STATE

## Live

- `adapter.py` — system-under-test boundary. `docs/knowledge/adapters.md`.
- `stub.py` — synthetic system with known ground truth.
- `recorder.py` — interleaved three-arm replay. `docs/knowledge/recorder.md`.
- `dedup.py` — exact and normalised input dedup. Semantic near-dup is a gap.
- `stats.py`, `fdr.py` — mode-share statistics and target-decoy selection.
  `docs/knowledge/decoy-fdr.md`.
- `normalize.py`, `clustering.py` — output normalisation and semantic mode
  clustering, which is what lets every statistic above apply to free text.
  `docs/knowledge/mode-clustering.md`. Equivalence threshold 0.7 (MTH-020).
- `conformance.py` — induced structural conformance, pruned by the decoy arm.
  `docs/knowledge/conformance.md`. The unoccupied mechanism (STD-003).
- `provenance.py` — run id, config hash over everything that changes a result,
  git state, pinned instrument revisions.
- `gating.py` — surface-drift gate for the embedding channel (MTH-012),
  output-shape inference, and stratified selection. `docs/knowledge/gating.md`.
- Recorder checkpoints per triple and resumes; safe to kill. Grouped by input
  (ENG-001), with wall-clock timestamps and a midnight-crossing flag.

Validated: realised FDR at or below 0.101 against a target of 0.10 on ground
truth, across nine (k, severity) cells (MTH-018).

## Interfaces owned

| Interface | Status |
|---|---|
| Adapter (`input -> output + trace`) | **done**. Deliberately minimal; resist widening it, log the pressure instead. |
| Trace format | **done** — latency, tools, steps, finish reason, model id, error. |
| Report format | GAP — week 2 |

## Cost posture

**60 model calls per input** (three arms, k=20). Not 30: MTH-006 derived k=10
from combinatorics, but the measured envelope puts k=10 at 8% detection for a
moderate shift, against 73% at k=20 (MTH-018). Cheap models for systems under
test — the object of measurement is the detector, not the systems. Subsample
corpora rather than reducing k: k is load-bearing, corpus size is not.

## Hard requirement: runs must be resumable

Study runs are free in money (local models) and expensive in wall-clock, and
they occupy the owner's only machine. A multi-hour run that cannot be paused and
resumed is not a long job, it is a machine lockout. The recorder must checkpoint
per (input, arm, sample) and restart from where it stopped, and it must be
safe to kill. Owner constraint, 2026-09-25.

## Not built

The Palworld adapter; the cell factorial and fault-injection harness.

The embedding gate and shape stratification exist but the gate's 0.25 threshold
is **unfitted** — a guess, labelled as one, where the clustering threshold was
measured.

Clustering and conformance both exist but **neither has run inside the detector
on real outputs** — only fitted and unit-tested against synthetic corpora.
Clustering cost figures are structural expectations, not measurements.
