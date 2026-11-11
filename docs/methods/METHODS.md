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
   **The sampling seed is explicitly not covered by this rail.** Pinning it
   makes the two baseline arms land on the same handful of outputs, and the
   decoy arm is the null distribution, so pinning it for reproducibility
   destroys the thing being reproduced. The arms mirror the seed policy of the
   deployment under audit, the policy used is recorded in provenance, and a run
   is reproducible because the seeds are known rather than because they are
   equal. Ratified 2026-09-30, MTH-023.
   **This rail covers the instruments, not the systems under test.** The NLI
   model and the embedder do the measuring, so a change in either makes old
   numbers incomparable. A system under test that changes is not a violation of
   this rail, it is the thing being detected. An earlier version of this note
   claimed a hosted model breaks the rail. It does not, and the correction is in
   HANDOFF §15. The real constraint on a changing system under test is narrower:
   A and A-prime must be the same system, because their spread is the null. The
   recorder keeps a triple to consecutive calls (ENG-001), which bounds that
   exposure to a handful of triples across a long run.
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
- **Float ties in grid-valued statistics** — a mode-share distance of 5/6 is
  `0.8333333333333333` from one pair of clouds and `0.8333333333333334` from
  another, and anything that sorts, uniques or compares raw floats will split a
  tie and count the lower form as below the cut. Compare as values: `fdr.py`
  rounds to nine places at every entry point (ENG-010), and any new estimator
  or re-derivation over stored scores must do the same before counting. The
  split is one-directional, so a pre-fix number overstates separation and
  never understates it.

## The null-design simulator's decision-4 blocks (MTH-027 first append)

`scripts/simulate_null_designs.py` blocks 6 to 9, commissioned 2026-11-11.
Each runs on its own `[seed, block]` rng stream, so its figures are stable
whichever blocks run (`--only 6 7 8 9`); blocks 1 to 5 keep sharing one
stream, so the proposals' committed figures are unchanged. On an all-null
cell the realised FDR equals P(any flag), which is what the rate columns
report. Acceptance figures below: 2000 cells per entry, n=40, 4 modes,
q=0.10, seed 20261020 (`--only 6 7 8 9 --null-cells 2000`, run 2026-11-11).

- **Block 6 — the (a') hole.** All-null cells whose CANDIDATE cloud is
  within-cloud dependent; primary selection s(A,B) against s(A,A'). Two
  constructions carry the rho dial: "chain" (each sample copies the
  previous with probability rho) and "anchor" (each copies the first — a
  cached session answer that recurs). **The anchor form is the audit's
  construction:** at k=20 it reads 0.068 / 0.681 / 0.983 at rho
  0.3 / 0.5 / 0.7 against the audit's 0.090 / 0.652 / 0.983 — exact at the
  top point, within about two combined standard errors elsewhere with the
  audit's cell count unknown — while the chain form reads
  0.004 / 0.050 / 0.377 and cannot be it. k=6 contrast, anchor:
  0.002 / 0.022 / 0.101. The run-time guard for this configuration is the
  recorder's per-arm sampling-seed warning (decision 2,
  `docs/knowledge/recorder.md`).
- **Block 7 — the stored-baseline mirror.** The same dependence planted on
  the stored, un-re-recordable A, selection on s(B,B'): anchor at k=20
  reads 0.076 / 0.672 / 0.985. The audit's symmetry refutation is now
  measured rather than argued: the blind side moves, the failure does not.
- **Block 8 — the r-decoy all-null row** (the decision-5 read, item 2).
  The within-input competition max-method (`select_maxmethod`: factor 1/r
  over decoy WINS, rank ties to the decoy) against the parked naive
  C' = (1+d)/(rt), at r in {1,2,3} by k in {6,20} by the rho sweep. **At
  rho 0 both control everywhere** (P(any) at most 0.002 against the 0.10
  budget): the read's expectation holds for the max-method, and naive C'
  happening to control in this exact geometry is the case the read
  pre-empted — a finding about our geometry, not a licence; the un-parking
  append still adopts the form with the theorem. At rho above 0 every form
  fails together, as the read predicted: sub-cloud dependence breaks cloud
  exchangeability one level down, and no counting rule repairs it. Top-tie
  share 3 percent at k=20 and 6 to 7 at k=6 — the price of the
  deterministic tie rule. The r=1 rows are classical TDC, labelled so, and
  are NOT the frozen paper-one estimator.
- **Block 9 — the shock alternative.** eps of mass moves to one novel
  mode, so the dial IS the population mode-share distance (the mixture
  alternative's per-input realised effect only bounds it). Realised FDR
  stays at or under 0.030 across the grid; power on the single-decoy
  design: 0.55 at eps 0.8 for k=6; 0.42 at eps 0.4 and 0.96 by eps 0.6
  for k=20. Use it wherever a power curve needs an exact x-axis.

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
