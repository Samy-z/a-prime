# bench — METHODS

## Conventions

- **Per-input fault activation instrumentation is mandatory.** Record whether
  each injected fault actually touched each input, and label positive only
  where it fired. Cell-level labels applied to every input in the cell are
  label noise by construction: truncation only bites long-context inputs, tool
  removal only bites tool-requiring inputs.
- **Base-rate control across cells.** If one domain's cells carry a higher
  regression rate than another's, measured "domain sensitivity" is a
  class-frequency artifact. See STD-007.
- **Severity ladders, not binary faults.** Report minimum detectable severity
  per fault type. Detection rate should be monotone in severity; a non-monotone
  curve is a harness bug before it is a finding.
- **Build cells as one thin agent with swappable knowledge packs and output
  modes**, not as nine applications. Nine cells is roughly three builds.

## Known traps

- Near-duplicate inputs create trivial hotspots and corrupt the FDR estimate.
  Dedup before anything else.
- Systems under test should be cheap models. The object of measurement is the
  detector; spending budget on strong systems under test buys nothing.
- The dev system (palworld-rag) must not leak into headline numbers. Any
  analysis script that pools systems excludes it by explicit allowlist, not by
  someone remembering to.
