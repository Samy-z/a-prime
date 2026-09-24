# engine — STATE

## Live

> GAP — nothing built. Week 1 delivers recorder, three-arm replay, dedup and
> target-decoy FDR against one system.

## Interfaces owned

| Interface | Status |
|---|---|
| Adapter (`input -> output + trace`) | GAP — week 1. Deliberately minimal; resist widening it. |
| Trace format | GAP — week 1 |
| Report format | GAP — week 2 |

## Cost posture

30 model calls per input (three arms, k=10). Cheap models for systems under
test — the object of measurement is the detector, not the systems. Subsample
corpora rather than reducing k: k is load-bearing (MTH-006), corpus size is not.
