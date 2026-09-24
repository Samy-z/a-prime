# study — METHODS

## Reporting conventions

- Every number carries its denominator and its interval.
- Naive random-split numbers are reported *alongside* LOSO and LOFO, never
  instead of them, so the inflation gap is visible to the reader.
- Negative results are written up with the same care as positive ones. A
  finding that detection does not transfer is publishable and is currently the
  more interesting outcome.
- The development system (palworld-rag) is reported separately and never pooled
  into headline transfer numbers.

## Overclaiming — banned phrasings

Recorded so they are not reached for under deadline pressure:

- "Domain-agnostic regression detection" as a bare claim.
- Any recall or precision figure on real regressions generalised beyond the
  30-80 case holdout, or quoted without its interval (MTH-010).
- Any claim to distinguish regression from improvement (MTH-001).
- Any causal claim that a disagreement hotspot *is* a coverage gap, absent the
  intervention test.
- Any headline number produced under random splits (MTH-009).

## Largest defensible claim shape

Under leave-one-system-out, across N systems spanning the named task types and
domains, the detector flagged changed inputs at FDR q against A-prime decoys and
detected injected faults down to severity s per fault class; performance on
unseen systems is expected within the stated interval. See MTH-008 for why that
interval is wide.
