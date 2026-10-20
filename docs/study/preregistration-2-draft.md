# Paper two — pre-registration — DRAFT — NOT REGISTERED

**Status: DRAFT, 2026-10-20, by the cloud session, revised twice the same
day, the second time after a three-seat cross-model review. Nothing in
this file is registered. Every slot marked `[SLOT]` is empty on purpose
and every prediction is blank. Registration is the procedure in §9, and it
has not run.** Written to STD-012 (the second study's thesis), HANDOFF §24
and its amendment (pre-registration starts now, gated on the cross-system
null design), and the two methods proposals this draft depends on.

The paper whose integrity story is "everything was registered first"
needs the registering to be cheap. This draft is the form: fill the slots,
date the predictions, commit, tag. What the form can compute, it has
computed; what it cannot, it asks for by name.

## 0. What is frozen, and by what

Frozen by a dated entry already, inherited as is:

- the fault taxonomy and severity ladders (`docs/knowledge/fault-taxonomy.md`,
  2026-09-24, amendments by dated append);
- the pinned judge (`MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`, revision
  `6f5cf0a2…`, methods STATE); a bump invalidates everything below;
- the seed policy (MTH-023 correction) and the load-regime rule (MTH-015:
  every arm interleaved, one tuple per input and sample index);
- the estimator's tie handling (ENG-010, nine decimals);
- provenance: every number traces to a per-cell report file, never to
  `matrix.json` (STD-013, study METHODS);
- the standing disciplines of 2026-10-16 (CLAUDE.md): no study-shaping
  parameter outside a dated entry; runtime state committed when it exists.

Frozen **by this registration**, because paper one fixed them for its own
instrument and paper two re-binds them to a new runner:

- the equivalence threshold 0.7 (MTH-020) and the stratum floor of 30
  inputs (MTH-024), carried unchanged;
- the zero-classification rule (MTH-025), re-bound by a dated MTH-025
  amendment filed before registration to the roster runner's diagnosis
  output, with the diagnosis script at a named commit. A cross-model
  pair-cell has no fault labels, and the rule's first test reads a
  label-dependent field (`mean_target_fired_minus_decoy`, which the script
  sets to zero with no fired set, so every silent pair-cell would classify
  as blindness by construction). For label-free cells the first test reads
  "no channel has a target above every decoy" from the `targets_above` and
  `decoys_above` fields at the best cut, the script writes the full sorted
  target array beside the decoys, and it refuses the activation fallback
  it has today (with no sibling `.activation.json` it reads the newest
  `cell_detection_*.json`, whose input ids match the study corpus);
- the sampling parameters of every model in the roster (§2), hashed.

## 1. The question, stated so that it can fail

STD-012 names the thesis: **how much information about a system, and
about differences between systems, can be mined from outputs alone.** This
registration takes the between-systems half and reports each system's
self-variance beside it. Registered form:

> For two systems A and B run on the same inputs, with no labels and no
> knowledge of what the outputs mean, what fraction of inputs can be
> certified as differing at a chosen false-discovery budget, and what
> governs that fraction?

The quantity: the **certified fraction** `c_q(A, B)`, inputs flagged by
the share-of-answers channel's stratified selection at budget `q` over
`n`, under the ratified cross-system design; its unit is the pair-cell
(one unordered pair of systems in one domain-format cell, with its
declared reference). The other selecting channels' flags are reported
beside it and enter no claim, and the union over channels is reported as
such without a budget claim, because each channel's selection is
controlled at `q` on its own and the union is bounded only by the sum.
Each system's **self-variance** (its within pair's score distribution on
the share-of-answers channel) is reported beside it.

STD-012 also names the resolution surface over (`k`, `n`, dispersion, `q`)
as a required instrument: [SLOT: registered as an instrument sweep, the
synthetic half from `scripts/simulate_null_designs.py` over `k` in {6, 20,
40}, `n` in {40, 100, 200}, `q` in {0.05, 0.10} with the mode count as the
dispersion axis, and the recorded half from the registered cells at the
registered `k`; or deferred by a dated STD-012 append named here with its
reason].

Three hypotheses, each with the observation that refutes it, plus one
validity check that runs before any of them is read:

- **V, validity, before recording.** The stub sweep of MTH-018's protocol
  (`aprime.stub`, the `mode_share` perturbation, the `_run` protocol of
  `tests/test_pipeline.py`) at the registered `k` over candidate `n` of
  40, 60, 100 and 200, with half the inputs changed at strengths 0.5 to
  0.9, under the selecting rule (`r = 1`) and the star `r = 2`, with
  [SLOT: seeds per strength, filed with the sweep together with its Monte
  Carlo standard error]. It realises, in every (strength, `r`) cell, a mean
  false-discovery proportion over seeds at or under `q + 0.02` (0.12 at
  `q = 0.10`, the bound `tests/test_pipeline.py` asserts and the MTH-018
  amendment reopens on) with no single seed above 0.35, and a mean pooled
  over cells at or under `q`. A strength whose P(any report) is under 0.10
  is void, not passed; V needs at least two non-void strengths. *Refuted
  if* either bound is broken in any non-void cell; then the design is
  reopened and nothing is recorded. A single seed above `q` is sampling,
  not refutation (MTH-018's own validation realised 0.101). The sweep
  validates the selector at `k` and `n`; it cannot test equal marginals
  between two systems, which hold in the stub by construction, and this
  registration states those as an assumption.
- **H1, the null pair.** One model recorded as both A and B, under two
  names, in the ratified roster: (a) **hard stop**, no input is flagged by
  any selection run on the null pair, selecting or reported (the reference
  selection, the reverse selection and the three replicate target sets),
  on any channel that runs. Every such flag is a false discovery; the
  guarantee permits one at rate up to `q` per cell, but the instrument
  puts the event at 0 of 2,000 all-null cells at `n = 40` under an
  independent decoy arm and at 0.1 to 0.5 of cells under a decoy arm that
  copies the reference 70 percent of the time, across its two regimes and
  both `k` (null proposal §5), so a
  flag means the recording departs from what the instrument models;
  (b) the **sign statistic**: among inputs whose target and reference
  decoy differ as values, the share with the target above. Under pairwise
  exchangeability with independent inputs it is Binomial(m, 1/2) whatever
  the score distribution, so each cell's band is that binomial's central
  95 percent at its own `m` non-tied inputs (at `m = 30`, 0.32 to 0.68;
  `scripts/simulate_null_designs.py` block 4 confirms it at k=6 and 20
  with three and four modes). *Refuted if* (a) fires in any cell, or (b)
  the number of null-pair cells outside their bands reaches `c`, the
  smallest count with P(Binomial(N, 0.05) ≥ c) ≤ 0.05 for the registered
  number `N` of null-pair cells (two or more of N = 4; three or more of
  N = 12, the cost table's case). Fewer cells outside is reported, not a
  refutation. H1 is a smoke test of the recording harness (interleaving,
  seed policy, the score tail), not the validity check: an all-null cell
  with an independent decoy arm flags nothing almost surely under any
  sound combination rule (null proposal §5).
- **H2, format over domain, registered this time.** At the one registered
  `k`, across the pool's pairs and the registered cells, the certified
  fraction's spread is partitioned three ways, by format, by domain and by
  pair, with the same sum-of-squares arithmetic paper one applied post hoc
  to recall (section 8). *Prediction slot:* the format share exceeds the
  domain share by at least [SLOT: a factor, with the reason for it].
  *Refuted if* it does not. Because the comparison is label-free, one cell
  carries a **positive control**, recorded apart from the roster and the
  null pairs: one model, [SLOT: which model], recorded as both A and B with
  the stale-knowledge-base fault injected into B (paper one's own design)
  in [SLOT: which cell]. It is a known difference whose certified fraction
  anchors the scale: paper one's k=20 value on banking extraction was 21
  of 40 inputs, 0.525, with all 21 touched inputs flagged and none false
  (STD-013), so the control's certified fraction is expected near the
  fault's activation rate in the chosen cell (paper one's k=20 cells
  touched 21, 19, 15 and 22 of 40), not near 1. It is excluded from H1 and
  from the H2 partition.
- **H3, the self-variance ceiling.** On the share-of-answers channel's own
  stratified selection, within each selection stratum: a pair-cell whose
  candidate decoys `s(B, B')` (the pair that reports and does not select)
  have a 90th percentile above the reference decoys' and cover at least
  [SLOT: F] of its targets (the share of the stratum's targets at or below
  that 90th percentile) certifies no more than [SLOT: G] of its inputs.
  *Refuted if* one does. Pair-cells whose reference decoys reach the higher
  90th percentile are reported and not tested: there, certified ≤ 1 − F
  holds by arithmetic at `q = 0.10`, because no admissible cut sits at or
  below the selecting decoys' 90th percentile (at least `n/10` decoys stand
  at or above it and `(1 + d)/t ≤ 0.10` would need `t ≥ n + 10`), so a
  consequent at or above 1 − F could not be refuted. The form asks, before
  recording, for the number of tested pair-cells expected to satisfy the
  antecedent, so the test cannot be vacuous: [SLOT].

What the paper will not claim, the study METHODS list carried whole and
three additions. From the list: "domain-agnostic regression detection" as
a bare claim; any recall or precision on real regressions beyond what a
holdout supports, or without its interval; any claim to distinguish
regression from improvement; any causal claim that a disagreement hotspot
is a coverage gap without the intervention test; any headline number
under a random split. Added for paper two: that any system is "better"; a
leaderboard from per-pair FDR (a many-way ranking needs a
multiple-comparison design, parked in the compare METHODS); cross-system
transfer of paper one's result.

## 2. The pool

D10 names three models and "a 3B" and leaves the 3B unnamed; this
registration is the dated entry that fixes it as `ministral-3:3b`, the 3B
measured in BCH-007 and BCH-012. Weights on disk; pool confirmed current
by BCH-019 (no 2026 candidate clears every bar; watch conditions listed
there):

| model | role | from the survey (`.agents/bench-model-survey.md`; chaining BCH-007, template injection and thinking default BCH-009 and BCH-012) |
|---|---|---|
| `granite4.2:8b` | paper one's model; reference | chained tool use 12 of 12 |
| `ministral-3:8b` | second 8B family | 12 of 12; injects a date-varying system prompt when none is supplied, so every call carries an explicit system message |
| `qwen3.5:9b` | third family | 12 of 12 with thinking off; thinking is on by default and eats the output budget, so it is set off explicitly |
| `ministral-3:3b` | the capability axis | chained tool use 9 of 12; injects the same date-varying system prompt as the 8B, so every call carries an explicit system message |

Six unordered pairs, so six pair-cells per cell, each with its declared
reference; the reverse orientation is computed and reported, never
selecting (null proposal §2 and §3). Sampling parameters are set
explicitly on every model, including every parameter any pool model's
Modelfile sets (`ollama show --parameters`, recorded per model before the
freeze): vendor defaults differ (temperature 0.15 to 1.0 across the three
the survey measured; `qwen3.5:9b` also sets presence_penalty 1.5;
`ministral-3:8b`'s defaults are unrecorded and are measured before the
freeze), and `OllamaChat.options()` today sends only num_ctx, temperature,
top_p, top_k, num_predict and seed, so the rest are added to the request
and hashed with it. Temperature is 0.2 as in paper one; any other value is
a separate registered configuration. Seed unset (MTH-023). These
parameters enter the configuration hash through the engine entry in §4,
and a digest change on any model aborts a recording, as the drift
control's guard does.

Per-call times on these models are unmeasured except granite's; they are
measured before `n` is filed (§5), together with the model-switch cost §5
names.

## 3. Cells and recording layout

[SLOT: the domain-by-format cells.] Default proposal: the three summary
cells and the three extraction cells. Paper one's detector works at k=20
in the summary cells and in banking extraction (21 of 21 touched inputs,
STD-013); logistics and hospitality extraction are unmeasured at k=20
(study STATE), logistics having flagged 11 of 23 touched and hospitality 0
of 25 at k=6. The agent format enters only if the titration certifies it
at some `k` (a point at or under `q`), read under MTH-025.

Recording layout, a slot because the cost differs by three: per pair-cell
four-arm tuples (A, A', B, B'), 3,200 calls per pair-cell at k=20 and
n=40, 36 recordings for six pairs in six cells; or **one roster per cell
holding every model twice** (eight arms, 6,400 calls per cell, six
recordings), from which every pair is read with all arms under one load
regime. Whether the frozen combination rule permits a roster holding more
than one pair is put to the owner in the null proposal's §8 item 1; the
eight-arm layout is the one its recorder change would permit and MTH-015
favours. Its cost is in §5. [SLOT: layout.] The positive control (§1 H2)
and the style-only control (§4) are recordings of their own, costed in §5.

## 4. Protocol slots that wait on the ratified null design

- [SLOT: the combination rule, from the cross-system proposal §3 once
  ratified: Design R, the reference pair selects at `r = 1`; the
  candidate pair, the reverse selection, the reverse orientation, the
  pooled estimate and the replicate sets are reported; which system is the
  reference in each pair, declared before recording.]
- [SLOT: the engine entry for the recorder roster change, including
  `adapter.check_arm` and the hash rule that keeps every committed
  checkpoint's hash.]
- [SLOT: the engine entry for the generalised estimator over the star
  pairs and `select_stratified`'s decoy-to-input mapping.]
- [SLOT: the engine entry that hashes the sampling parameters without
  orphaning the committed checkpoints and adds the digest guard and the
  server-version field to the roster runner.]
- [SLOT: the dated MTH-025 amendment for label-free pair-cells (§0).]
- [SLOT: which channels select and which report: the null proposal's §7
  says no channel selects in cross-system runs until the style-only
  control has run and its certified fraction on that channel family is at
  or under `q`, since the partition channels carry part of the style term
  (the judge merges reorderings 75 percent of the time, MTH-020); or, if
  the owner so decides, the partition channels select meanwhile with the
  reorder split disclosed.]
- [SLOT: the style-only control: the same model under two system prompts
  that change register and not content, recorded as A against B in
  [which cell], read per channel family, before any channel selects.]
- Null pairs: one per model per cell, in [SLOT: which cells; at
  summary-cell timings a null pair is about 3.6 hours], recorded before
  any cross pair in the same cell.
- [SLOT: the leave-one-system-out script, §7.]
- [SLOT: the fittable choices re-fitted under leave-one-system-out,
  listed, or "none" with the reason.]
- Negative control for time: the drift control (MTH-026) is the
  instrument for any stored-baseline comparison, read from the separating
  count at the comparison's `k` (null proposal §6), which needs the
  control's record to carry the per-channel `best_achievable` output
  [SLOT: the engine entry]; its first report lands with the period-two
  recording now at 212 of 240 triples.

## 5. Sizing, from MTH-024, with the arithmetic done

The floor: at budget `q` nothing is reportable below `1/q` flagged inputs,
so the smallest certifiable fraction at `n` inputs is `(1/q) / n`:

| n | smallest certifiable fraction at q = 0.10 |
|---|---|
| 40 | 0.25 |
| 60 | 0.17 |
| 100 | 0.10 |
| 200 | 0.05 |

With `a` the fraction of inputs on which the pair genuinely differs and
`s` the fraction of those that separate from every decoy, the corrected
rule is `n ≥ (1/q) / (a·s)`. Neither is knowable before recording, and for
a cross pair `a` is part of what the study measures, so `n` is not solved
from them: the registrant fixes `c_min`, the smallest certified fraction
the paper means to resolve, and files `n ≥ (1/q) / c_min` from the table
above. The stub sweep of V, run before `n` is filed, reports the stub's
`s` at each candidate `n` as a check that `c_min` is reachable. The rule
`n ≥ (1/q)/(a·s)` stays MTH-024's rule for reading a silent pair-cell:
one that flags nothing is classified under MTH-025 from its diagnosis
file, and a resolution-limited pair-cell is reported with its best
estimate, never as "no difference". One prior is available and recorded as
such: paper one's within-system k=20 rows touched 21, 19, 15 and 22 of 40
inputs on banking extraction and the three summary cells and flagged 21,
16, 15 and 23, which sizes the positive-control row only.

The registration fixes:

- `q` = [SLOT: 0.10, as paper one];
- `k` = [SLOT: 20, the value D25 confirmed; 6 is below the stated minimum
  and may not be used];
- `n` = [SLOT], from `c_min` and the table above;
- `c_min` = [SLOT].

Cost, on granite's measured per-call times. Summary cells ran at 3.8 to
4.6 s per call and banking extraction at 5.0 s at k=20, all in the current
serving regime; logistics and hospitality extraction were recorded only on
4 and 5 October at 28.2 and 37.7 s, in the partial-CPU load regime that
`docs/knowledge/environment.md` documents, and the smoke-run ratios put
them near 4.0 and 5.9 s in the current regime. Both columns are given:

| layout | calls | hours at the 4 to 5 October extraction rates | hours at current-regime estimates |
|---|---|---|---|
| per pair-cell, four arms, 36 recordings | 115,200 | about 440 | about 145 |
| one eight-arm roster per cell, six recordings | 38,400 | about 150 | about 50 |
| null pairs, one per model per summary cell, twelve recordings | 38,400 | about 43 | about 43 |
| positive control, one four-arm pair-cell | 3,200 | 3.6 in a summary cell, 4.4 in banking extraction | same |
| style-only control, one four-arm pair-cell | 3,200 | 3.6 in a summary cell | same |

These per-call times were measured with one model resident. No two pool
models fit the 8 GB card together (measured peak 6,041 to 7,888 MiB each),
so a cross-model roster reloads weights at every model switch inside a
tuple, about one switch per two calls in either layout, a cost this table
excludes and that scales with calls rather than with the layout; one
interleaved tuple of each layout is timed before the layout slot is
filled, and the hours column re-stated with it. The eight-arm layout costs
a third of the four-arm one in either regime; whether the two slow
extraction cells dominate (86 percent of the eight-arm hours at the
October rates, 55 percent at the current-regime estimates) is settled by a
k=20 granite timing of them before `n` is filed.

## 6. Predictions — EMPTY, to be filled and dated before any recording

Each row is filled with a number or an interval, a date and the commit
that holds it, before the first tuple is recorded. An empty row at
recording time is a protocol violation, not an omission.

| hypothesis | prediction | filed on | commit | if outside |
|---|---|---|---|---|
| V, stub sweep: seed-mean false-discovery proportion per non-void cell at the registered k over n in {40, 60, 100, 200}, r = 1 and r = 2 | at or under 0.12, no seed above 0.35, pooled at or under q; the realised rate at the filed n recorded beside it | | | stop; reopen the null design |
| H1a, flags by any selection on any null pair | 0 | | | stop recording in that cell; check interleaving, seed policy and the channel's score tail against the instrument; reopen the null design if none explains it |
| H1b, null-pair cells outside their sign-statistic band, of N = [SLOT] | fewer than c = [SLOT: smallest c with P(Bin(N, 0.05) ≥ c) ≤ 0.05] | | | report; cross-pair recording in that cell halts until the null design is reopened by dated append |
| H2, format share over domain share | [SLOT] | | | report as refuted; no reframing |
| H2 positive control, certified fraction (a fraction of n) | [SLOT: an interval around the chosen cell's activation rate] | | | if activation shows the fault did not fire, re-record the control before anything else is read; if it fired, report the value with its Wilson interval as the scale and read H2 as registered |
| H3, ceiling on the tested pair-cells | [SLOT: F, G, and the expected number of tested pair-cells] | | | report as refuted |
| per-format certified fraction, interval | [SLOT] | | | report |
| certified fraction of the pair-cells with paper one's model (`granite4.2:8b`) as the reference A, in [SLOT: which pairs] | [SLOT: interval] | | | report |

## 7. Analysis plan, frozen with the predictions

- Per pair-cell: `select_stratified` under the ratified rule at `q` on the
  share-of-answers channel; the other selecting channels and the
  replicate target sets reported as a stability check.
- Leave-one-system-out across the pool, with the script named in §4:
  every fittable choice is re-fitted with one system held out and the
  certified fractions reported from the held-out fits (methods METHODS
  rail 3). The fittable choices are listed in the §4 slot, or that slot
  says "none" with the reason.
- Control is per selection, at `q`, within each pair-cell; what is
  claimed across cells is the partition of H2 and the ceiling of H3,
  neither of which is a selection.
- The three-way partition of H2, computed once, on the registered cells,
  excluding the positive control.
- Every number with its denominator and interval (study METHODS): Wilson
  score intervals on rates over inputs (MTH-010,
  `aprime.probes.analysis.wilson`); Clopper-Pearson on counts of systems,
  pairs or pair-cells (MTH-008, as paper one's 0.29 for three of three; no
  helper exists in `src`, so the registration names the computation, the
  two-sided 95 percent exact binomial interval, lower bound `0.025^(1/n)`
  when all `n` succeed).
- Nothing fitted on the cross-system recordings is used to choose which
  cells or pairs are reported.

## 8. Instruments and provenance

`scripts/run_study.py` generalised to the roster, or a sibling runner;
`scripts/diagnose_channels.py` under the MTH-025 amendment of §0;
`scripts/agent_decision_variation.py` where the agent format enters;
`scripts/simulate_null_designs.py` for the bands and the synthetic half of
the resolution surface; the drift control with its record change. Every
recording is a checkpoint with its activation store committed as it
exists, every analysis a per-cell report file; the matrix file is never
cited.

## 9. How to register this, cheaply

1. Fill every `[SLOT]` in §0 to §5 and every row of §6. Do not record.
2. Commit the file alone with the message `REGISTER paper two: v1` and tag
   the commit `prereg-2-v1`. The commit hash goes into the methods STATE
   under a new "Frozen" line and into the first row of a new study ledger
   entry, STD-014 or next free.
3. From then on the file is append-only: amendments are dated appends at
   the foot, with the reason and what prompted it, never edits above the
   line (the taxonomy's own rule; STD-012 is the template for a declared
   change).
4. The first recording is a null pair, and it may not start before step 2
   is pushed.

What makes it cheap: the slots are named and few; the floor table and the
cost table are computed; the "if outside" column is filled for every row,
so filing a number commits to a consequence; and the freeze is a commit
and a tag, which the repository already does for everything else. What the
registrant still has to supply: the cells and layout, the per-model
timings and the model-switch cost, `c_min`, the H2 factor, the two H3
fractions and the H3 antecedent count, and the predictions.

**Evidence:** STD-012, STD-013, BCH-007, BCH-009, BCH-012, BCH-019,
MTH-008, MTH-010, MTH-015, MTH-018 and amendment, MTH-020, MTH-021,
MTH-023 to MTH-026, the compare METHODS and STATE, paper one's section 8,
`tests/test_pipeline.py`, `src/aprime/cells/chat.py`,
`scripts/diagnose_channels.py`, `scripts/simulate_null_designs.py`.
**Reopen if:** the cross-system proposal is ratified in a form other than
Design R, which rewrites §4 and §5; or the agent titration certifies the
agent format at some `k`, which adds its cells to §3.
