# engine — STATE

## Live

- `adapter.py` — system-under-test boundary. `docs/knowledge/adapters.md`.
- `stub.py` — synthetic system with known ground truth.
- `recorder.py` — interleaved three-arm replay. `docs/knowledge/recorder.md`.
- `dedup.py` — exact and normalised input dedup. Semantic near-dup is a gap.
- `stats.py`, `fdr.py` — mode-share statistics and target-decoy selection.
  `docs/knowledge/decoy-fdr.md`.

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

## Not built

Embedding style-stability gate (MTH-012); semantic mode clustering, which blocks
every statistic from applying to free text; structural conformance; shape
stratification of thresholds; format normalisation before scoring.
