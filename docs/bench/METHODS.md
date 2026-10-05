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

## Severity for a near-binary fault

The titration figure asks for detection rate as a function of severity per
fault class, monotone, with a minimum detectable severity. The fault the first
matrix used cannot drive it. `stale_view` is all-or-nothing per input: 101 of
the 111 inputs it touched fired on five or six of their six samples (STD-010
append), so every touched input moves its whole cloud and there is no
per-input severity to sweep. Its `severity` argument reaches `FaultSpec` as a
label and nothing else; the tool layer's `stale` flag is binary. Do not plot a
curve from it at any k.

Three real knobs exist, and a titration per class uses the one that class has:

| class | knob | where it lives |
|---|---|---|
| F11 degraded retrieval | `noise`, the share of rows replaced, on the published ladder 0.10 / 0.20 / 0.30 | `degraded_retrieval(noise=...)`, seeded per call |
| F2 prompt regression | the frozen rung, 1 to 3, as lines added or removed | `PROMPT_EDITS`, `severity = rung/3` |
| output-rewriting faults | the fraction cut, dropped or inserted | `faults.py` injections |

A fourth is blast share, `regime="B2", share=...`, which grades how many
inputs a fault touches rather than how hard it touches each one. That is a
different axis (BCH-001) and must not be reported as severity; it is the knob
for the activation-rate and sizing questions (MTH-024), not for a severity
curve.

Two requirements before any titration on real systems: k of at least 20
(MTH-018; at k=6 the statistic's seven values measure the quantisation, not the
detector, STD-010 append), and a fault from the table above. If `stale_view`
needs a graded form, give the tool layer a per-call probability of serving the
shifted view, seeded like degradation, so the knob reaches the data.
