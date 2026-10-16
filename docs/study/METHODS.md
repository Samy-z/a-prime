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

## Known data traps

- **Seven activation keys on a cell's first input.** The preflight re-invokes
  the first input in-process before recording, and the per-sample activation
  store numbers that invocation too, so that input carries `#0` to `#6` where
  every other input carries `#0` to `#5`. Count per-sample firing over the six
  recorded keys: drop `#0` when there are seven. An exact-six count silently
  drops a fully fired input (STD-010 fifth append: 96 reported where 100 was
  right). Inputs with fewer than six keys lost labels (BCH-018) and cannot be
  judged for "fired on all six"; keep them out of both numerators and say so.
- **`cost.samples_clustered` below 4·k·n is errored calls, not dedup.**
  `Recording.clouds` drops a sample whose call errored, and A is counted in
  both arm pairs, so the shortfall is 2·A + A′ + B errored samples (STD-011
  first append). Exact duplicates are still clustered; they collapse in
  `distinct_after_normalisation`, not here.
