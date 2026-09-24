# methods — METHODS

Instruments, conventions, and known traps for the statistical work.

## The integrity rails

These silently invalidate a result rather than failing loudly.

1. **Pre-registration.** The fault taxonomy and severity ladder are frozen in a
   committed, dated document before any detector tuning. Amendments are dated
   appends with a reason; never in-place edits. The freeze commit is the
   reference point.
2. **Sealed holdout.** The real-regression set is opened once. The opening is
   recorded in `STATE.md` with its date and who opened it. Used for calibration
   assessment, never for tuning.
3. **No threshold outside a fold.** Every cutoff, hyperparameter and fittable
   design choice is selected inside nested leave-one-system-out. With 6-9
   systems, a handful of free knobs overfits trivially.
4. **Pinned instruments.** Embedding and NLI model versions locked in
   `STATE.md`. A bump invalidates prior results.
5. **Provenance.** Every number traces to a run id and a config hash. See
   `docs/knowledge/provenance.md` when it exists.

## Known traps

- **Circular stratification** — never bin on a quantity estimated from the same
  samples used for the within-bin estimate. See MTH-004.
- **Near-duplicates** — dedup before any counting, testing or clustering. They
  corrupt the FDR estimate and manufacture fake hotspots.
- **Base rates faking transfer** — apparent cross-domain transfer is frequently
  a class-frequency artifact rather than a methodological result. Domain cells
  must have controlled regression base rates or the transfer finding is
  uninterpretable in either direction. See STD-007.
- **Correlated blind spots** — the embedding channel and the noise floor
  degenerate on the *same* inputs: highly templated, low-variety outputs. Two
  instruments failing together produces confident wrong answers rather than
  obvious ones. Flag these inputs explicitly instead of reporting them clean.
- **Label noise by construction** — a fault labelled at the cell level is wrong
  for every input the fault never touched. Per-input activation instrumentation
  is mandatory; label positive only where the fault fired.

## Recommended statistics (as of 2026-09-24)

Per input, four channels, all calibrated against the A-prime decoy arm:

1. Energy distance on centred, L2-normalised embeddings.
2. Mode-share change (Fisher exact or permutation on the k-by-modes table)
   after semantic mode clustering.
3. Dispersion ratio, permutation-calibrated, to catch collapse and explosion.
4. Bidirectional NLI contradiction rate, baselined on A-vs-A-prime.

Flagging by target-decoy FDR at q = 0.10 within stratum. Minimum k = 10 per arm.

## Standing duty — prior art

The novelty claim depends on a moving landscape. Prior-art monitoring is a
recurring `methods` duty, not a one-off survey. Findings go to
`docs/study/LEDGER.md` under STD ids, since they bear on what the study may
claim.
