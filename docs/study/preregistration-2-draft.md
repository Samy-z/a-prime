# Paper two — pre-registration — DRAFT — NOT REGISTERED

**Status: DRAFT, 2026-10-20, by the cloud session, revised the same day
after an adversarial verification pass. Nothing in this file is
registered. Every slot marked `[SLOT]` is empty on purpose and every
prediction is blank. Registration is the procedure in §9, and it has not
run.** Written to STD-012 (the second study's thesis), HANDOFF §24 and its
amendment (pre-registration starts now, gated on the cross-system null
design), and the two methods proposals this draft depends on.

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
- the zero-classification rule (MTH-025), re-bound to the roster runner's
  diagnosis output, with the diagnosis script at a named commit;
- the sampling parameters of every model in the roster (§2), hashed.

## 1. The question, stated so that it can fail

STD-012 names the thesis: **how much difference-information between
systems can be mined from outputs alone.** Registered form:

> For two systems A and B run on the same inputs, with no labels and no
> knowledge of what the outputs mean, what fraction of inputs can be
> certified as differing at a chosen false-discovery budget, and what
> governs that fraction?

The quantity: the **certified fraction** `c_q(A, B)`, flagged inputs over
`n` at budget `q`, where an input is flagged if any selecting channel
flags it (§4 names the selecting channels), under the ratified
cross-system design; its unit is the pair-cell (one ordered pair of
systems in one domain-format cell). Each system's **self-variance** (its
within pair's score distribution on the share-of-answers channel) is
reported beside it.

Three hypotheses, each with the observation that refutes it, plus one
validity check that runs before any of them is read:

- **V, validity, before recording.** The stub sweep of MTH-018's protocol
  at the registered `k` and `n`, under the ratified selector, realises a
  false-discovery rate at or under `q` in every cell with known truth.
  *Refuted if* any cell exceeds `q`; then the design is reopened and
  nothing is recorded.
- **H1, the null pair.** One model recorded as both A and B, under two
  names, in the ratified roster: (a) **hard stop**, no input is flagged,
  since any flag is a false discovery by construction; (b) the
  exchangeability statistic, the share of targets at or above the pooled
  decoy median, falls inside the band the instrument gives at the
  registered `k` and `n` (`scripts/simulate_null_designs.py`; at k=20 and
  n=40 the band is 0.35 to 0.70 with mean 0.53 to 0.54), aggregated over the
  null-pair cells with a binomial interval. *Refuted if* (a) fires in any
  cell or (b) falls outside the band in more cells than the band's own
  5 percent allows. H1 is a smoke test, not the validity check: an
  all-null cell flags nothing almost surely under any design (proposal
  §5).
- **H2, format over domain, registered this time.** At the one registered
  `k`, across the pool's pairs and the registered cells, the certified
  fraction's spread is partitioned three ways, by format, by domain and by
  pair, with the same sum-of-squares arithmetic paper one applied post hoc
  to recall (section 8). *Prediction slot:* the format share exceeds the
  domain share by at least [SLOT: a factor, with the reason for it].
  *Refuted if* it does not. Because the comparison is label-free, one
  cell carries a **positive control**: the stale-knowledge-base fault
  injected into B in [SLOT: which cell], a known difference whose
  certified fraction anchors the scale (its k=20 value in paper one was 21
  of 21 on banking extraction).
- **H3, the self-variance ceiling.** On the share-of-answers channel, a
  pair-cell whose noisier member's decoys cover at least [SLOT: fraction]
  of its targets (the share of targets at or below that member's decoy
  90th percentile) certifies no more than [SLOT: fraction] of its inputs.
  *Refuted if* one does. The form asks, before recording, for the number
  of pair-cells expected to satisfy the antecedent, so the test cannot be
  vacuous: [SLOT].

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

D10's four models, weights on disk, confirmed current by BCH-019 (no 2026
candidate clears every bar; watch conditions listed there):

| model | role | from the survey (BCH-007, `.agents/bench-model-survey.md`) |
|---|---|---|
| `granite4.2:8b` | paper one's model; reference | chained tool use 12 of 12 |
| `ministral-3:8b` | second 8B family | 12 of 12; injects a date-varying system prompt when none is supplied, so every call carries an explicit system message |
| `qwen3.5:9b` | third family | 12 of 12 with thinking off; thinking is on by default and eats the output budget, so it is set off explicitly |
| `ministral-3:3b` | the capability axis | chained tool use 9 of 12 |

Six unordered pairs; the design's orientation makes them twelve ordered
pair-cells per cell if both orientations are selected, which §4 decides.
Sampling parameters are set explicitly on every model: vendor defaults
differ (temperature 0.15 to 1.0 across the three the survey measured;
`ministral-3:8b`'s default is unrecorded and is measured before the
freeze). Temperature is 0.2 as in paper one; any other value is a separate
registered configuration. Seed unset (MTH-023). These parameters enter
the configuration hash through the engine entry in §4, and a digest change
on any model aborts a recording, as the drift control's guard does.

Per-call times on these models are unmeasured except granite's; they are
measured before `n` is filed (§5).

## 3. Cells and recording layout

[SLOT: the domain-by-format cells.] Default proposal: the three summary
cells and the three extraction cells, where paper one's detector works at
k=20; the agent format enters only after the titration's k=20 point, and
k=40 if it runs, have been read under MTH-025.

Recording layout, a slot because the cost differs by three: per pair-cell
four-arm tuples (A, A', B, B'), 3,200 calls per pair-cell at k=20 and
n=40, 36 recordings for six pairs in six cells; or **one roster per cell
holding every model twice** (eight arms, 6,400 calls per cell, six
recordings), from which every pair is read with all arms under one load
regime. The eight-arm layout is the one the proposal's recorder change
permits and MTH-015 favours; its cost is in §5. [SLOT: layout.]

## 4. Protocol slots that wait on the ratified null design

- [SLOT: the combination rule, from the cross-system proposal §3 once
  ratified: Design R, reference pair selects at `r = 1`, candidate pair,
  reverse selection, pooled estimate and replicate sets reported; which
  orientation selects, or both as separate pair-cells.]
- [SLOT: the engine entry for the recorder roster change.]
- [SLOT: the engine entry for the generalised estimator and
  `select_stratified`'s decoy-to-input mapping.]
- [SLOT: the engine entry that hashes the sampling parameters and adds the
  digest guard to the roster runner.]
- [SLOT: which channels select and which report: the proposal's §7 says
  the partition channels select and the text channels report until the
  style-only control has run.]
- [SLOT: the style-only control: the same model under two system prompts
  that change register and not content, recorded as A against B in
  [which cell], before any text channel selects.]
- Null pairs: one per model, in [SLOT: which cells; at summary-cell
  timings a null pair is about 3.6 hours], recorded before any cross pair
  in the same cell.
- [SLOT: the leave-one-system-out script, §7.]
- Negative control for time: the drift control (MTH-026) is the
  instrument for any stored-baseline comparison; its first report lands
  with the period-two recording now at 212 of 240 triples.

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
rule is `n ≥ (1/q) / (a·s)`. Neither is knowable before recording; `s` at
the registered `k` comes from the stub sweep of V, run before `n` is
filed, and `a` from the positive control. The registration fixes:

- `q` = [SLOT: 0.10, as paper one];
- `k` = [SLOT: 20, the value D25 confirmed; 6 is below the stated minimum
  and may not be used];
- `n` = [SLOT], chosen so that the smallest certified fraction the paper
  means to resolve clears the table above and the sweep's `s`;
- the reading rule: a pair-cell that flags nothing is classified under
  MTH-025 from its diagnosis file, and a resolution-limited pair-cell is
  reported with its best estimate, never as "no difference".

Cost, on granite's measured per-call times (summary 3.8 to 4.6 s;
extraction 5.0 s in banking at k=20, 28.2 s in logistics and 37.7 s in
hospitality at k=6; other models unmeasured):

| layout | calls | hours |
|---|---|---|
| per pair-cell, four arms, 36 recordings | 115,200 | about 440 |
| one eight-arm roster per cell, six recordings | 38,400 | about 150 |
| null pairs, one per model, summary cells only | 38,400 | about 43 |

The eight-arm layout is the only one that fits a month of nights, and
even it is dominated by the two slow extraction cells. These figures are
the planning input for the layout and cell slots in §3, and they move with
the per-model timings once measured.

## 6. Predictions — EMPTY, to be filled and dated before any recording

Each row is filled with a number or an interval, a date and the commit
that holds it, before the first tuple is recorded. An empty row at
recording time is a protocol violation, not an omission.

| hypothesis | prediction | filed on | commit | if outside |
|---|---|---|---|---|
| V, stub realised FDR at the registered k and n | [SLOT] | | | stop; reopen the null design |
| H1a, flags on any null pair | 0 | | | stop; reopen the null design |
| H1b, exchangeability band at the registered k and n | [SLOT, from the instrument] | | | report; reopen the null design |
| H2, format share over domain share | [SLOT] | | | report as refuted; no reframing |
| H2 positive control, certified fraction | [SLOT] | | | the fault did not fire; check activation before anything else is read |
| H3, ceiling | [SLOT] | | | report as refuted |
| per-format certified fraction, interval | [SLOT] | | | report |
| reference pair in the roster: [SLOT: yes or no] | [SLOT] | | | report |

## 7. Analysis plan, frozen with the predictions

- Per pair-cell: `select` under the ratified rule at `q`; the replicate
  target sets reported as a stability check.
- Leave-one-system-out across the pool, with the script named in §4:
  every fittable choice is re-fitted with one system held out and the
  certified fractions reported from the held-out fits (methods METHODS
  rail 3). The fittable choices are few and the registration lists them.
- Control is per selection, at `q`, within each pair-cell; what is
  claimed across cells is the partition of H2 and the ceiling of H3,
  neither of which is a selection.
- The three-way partition of H2, computed once, on the registered cells.
- Every number with its denominator and interval (study METHODS): Wilson
  score intervals on every rate, the study convention
  (`aprime.probes.analysis.wilson`).
- Nothing fitted on the cross-system recordings is used to choose which
  cells or pairs are reported.

## 8. Instruments and provenance

`scripts/run_study.py` generalised to the roster, or a sibling runner;
`scripts/diagnose_channels.py` under MTH-025; `scripts/agent_decision_variation.py`
where the agent format enters; `scripts/simulate_null_designs.py` for the
bands; the drift control. Every recording is a checkpoint with its
activation store committed as it exists, every analysis a per-cell report
file; the matrix file is never cited.

## 9. How to register this, cheaply

1. Fill every `[SLOT]` in §1 to §5 and every row of §6. Do not record.
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
timings, the three margins, and the predictions.

**Evidence:** STD-012, STD-013, BCH-019, MTH-015, MTH-018, MTH-020,
MTH-023 to MTH-026, the compare METHODS and STATE, paper one's section 8,
`scripts/simulate_null_designs.py`.
**Reopen if:** the cross-system proposal is ratified in a form other than
Design R, which rewrites §4 and §5; or the agent titration certifies the
agent format at some `k`, which adds its cells to §3.
