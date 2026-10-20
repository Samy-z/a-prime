# Paper two — pre-registration — DRAFT — NOT REGISTERED

**Status: DRAFT, 2026-10-20, by the cloud session. Nothing in this file is
registered. Every slot marked `[SLOT]` is empty on purpose and every
prediction is blank. Registration is the procedure in §9, and it has not
run.** Written to STD-012 (the second study's thesis), HANDOFF §24 and its
amendment (pre-registration starts now, gated on the cross-system null
design), and the two methods proposals this draft depends on.

The paper whose integrity story is "everything was registered first"
needs the registering to be cheap. This draft is the form: fill the slots,
date the predictions, commit, tag. Section 9 says exactly how.

## 0. What is frozen already, and inherited

- The fault taxonomy and severity ladders (`docs/knowledge/fault-taxonomy.md`,
  frozen 2026-09-24, amendments by dated append).
- The zero-classification rule (MTH-025) and its instrument.
- The seed policy (MTH-023 correction: mirror the deployment, record the
  regime) and the load-regime rule (MTH-015: every arm interleaved).
- The pinned judge (`MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli`,
  revision `6f5cf0a2…`, methods STATE) and the equivalence threshold 0.7
  (MTH-020). A bump invalidates everything below it.
- The estimator's tie handling (ENG-010, nine decimals).
- Provenance: every number traces to a per-cell report file, never to
  `matrix.json`, which is a view of the last run (STD-013, study METHODS).
- The standing disciplines added 2026-10-16 (CLAUDE.md): no study-shaping
  parameter outside a dated entry; runtime state committed when it exists.

## 1. The question, stated so that it can fail

STD-012 names the thesis: **how much difference-information between
systems can be mined from outputs alone.** Registered form:

> For two systems A and B run on the same inputs, with no labels and no
> knowledge of what the outputs mean, what fraction of inputs can be
> certified as differing at a chosen false-discovery budget, and what
> governs that fraction?

The quantity: the **certified fraction** `c_q(A, B)` = flagged inputs over
`n` at budget `q`, under the cross-system null design of
`docs/methods/cross-system-null-proposal.md` once ratified, with each
system's **self-variance** (its own within pair's score distribution)
reported beside it.

Three hypotheses, each with the observation that would refute it:

- **H1, the null pair.** One model recorded as both A and B, under two
  names, in the four-arm design, realises a false-discovery rate at or
  under `q`. *Refuted if* the realised rate exceeds `q` on the null pair in
  any cell; then the pooled null is not exchangeable for these scores and
  no other result in the paper is interpretable. This is the validity
  check and it runs first.
- **H2, format over domain, registered this time.** Across the pool's
  pairs, the certified fraction is governed by output format, through the
  diversity of wording, and by `k`, and not by domain: the share of its
  spread accounted for by format exceeds the share accounted for by domain
  by [SLOT: margin, e.g. a factor of three] in the same two-way partition
  paper one computed post hoc (section 8 of `paper/draft.md`). *Refuted
  if* the domain share is within that margin of the format share.
- **H3, the self-variance ceiling.** A pair's certified fraction is bounded
  by the self-variance of its noisier member: no pair whose noisier
  member's decoy range covers [SLOT: fraction] of the score range reaches
  `c_q` above [SLOT: value]. *Refuted if* a pair does. This is the agent
  row's lesson stated as a prediction.

What the paper will not claim (study METHODS, banned phrasings): that any
system is "better"; a leaderboard from per-pair FDR (a many-way ranking
needs a multiple-comparison design, parked in the compare METHODS);
cross-system transfer of paper one's result; "domain-agnostic" as a bare
statement; anything about production systems.

## 2. The pool

D10's four models, weights on disk, confirmed current by BCH-019 (no 2026
candidate clears every bar; watch conditions listed there):

| model | role | from the survey (BCH-007, `.agents/bench-model-survey.md`) |
|---|---|---|
| `granite4.2:8b` | paper one's model; reference | chained tool use 12 of 12 |
| `ministral-3:8b` | second 8B family | 12 of 12; injects a date-varying system prompt when none is supplied, so every call carries an explicit system message |
| `qwen3.5:9b` | third family | 12 of 12 with thinking off; thinking is on by default and eats the output budget, so it is set off explicitly |
| `ministral-3:3b` | the capability axis | chained tool use 9 of 12 |

Six pairs. Sampling parameters are set explicitly on every model and enter
the configuration hash, because vendor defaults differ (temperatures 0.15
to 1.0 across the four); the study temperature is [SLOT: 0.2 as in paper
one, or the value the agent titration settles on], seed unset (MTH-023).
Model digests are pinned per cell and a digest change aborts a recording
(the MTH-026 guard, generalised).

## 3. Cells

[SLOT: the domain-by-format cells, chosen before any recording.] Default
proposal: the three summary cells (where paper one's detector works) and
the three extraction cells at k=20 (where it works at twenty samples),
giving `6 pairs × 6 cells = 36` cross-system recordings plus the null
pairs of §4; the agent format enters only after the titration proposal has
answered whether any `k` certifies it.

## 4. Protocol slots that wait on the ratified null design

- [SLOT: arm roster and combination rule, from the cross-system proposal
  §3 once ratified: targets `s(A, B)`, decoys the union of within pairs,
  estimate `(1 + d/r) / t`.]
- [SLOT: the engine entry that lands the generalised estimator with the
  three-arm case byte-identical.]
- [SLOT: the engine entry that lands the recorder roster change.]
- [SLOT: which channels select and which only report; the proposal's §5
  says the partition channels select and the text channels report until
  the null pair has measured their cross-style false-alarm rate.]
- Null pairs: one per model, [SLOT: in which cells], recorded before any
  cross pair in the same cell, so that H1 is tested before anything it
  guards is read.
- Negative control for time: the drift control (MTH-026) is the
  instrument for any stored-baseline comparison the paper makes; its
  first report lands with the period-two recording now at 212 of 240
  triples.

## 5. Sizing, from MTH-024

With no injected fault there is no activation rate; the quantity that
plays its part is the certified fraction itself. The floor stands: at
`q = 0.10` nothing is reportable below ten flagged inputs, so a pair whose
true certified fraction is `c` needs `n ≥ 10 / (c · s)` inputs, with `s`
the fraction of genuinely different inputs that separate from every
decoy. Neither `c` nor `s` is knowable before recording. The registration
therefore fixes:

- `q` = [SLOT: 0.10, as paper one];
- `k` = [SLOT: 20, the value D25 confirmed; 6 is below the stated minimum
  and may not be used];
- `n` = [SLOT: 40 per cell, or the value that makes `n ≥ 10 / (c·s)` hold
  for the smallest `c` the paper means to resolve, stated here];
- the reading rule: a pair that flags nothing is classified under MTH-025
  from its diagnosis file, and a resolution-limited pair is reported with
  its best estimate, never as "no difference".

Cost, at the summary cell's measured 4 seconds per call: `n × k × 4 arms
= 3,200` calls and about 3.6 hours per cross-system cell; 36 cells is
about 130 hours of recording before null pairs, which is the number the
owner sizes against.

## 6. Predictions — EMPTY, to be filled and dated before any recording

Each line is filled with a number or an interval, a date and the commit
that holds it, before the first cross-system tuple is recorded. An empty
line at recording time is a protocol violation, not an omission.

| hypothesis | prediction | filed on | commit | if outside |
|---|---|---|---|---|
| H1 null pair realised FDR | [SLOT] | | | stop; reopen the null design |
| H2 format share over domain share | [SLOT] | | | report as refuted; no reframing |
| H3 ceiling: no pair above `c` = [SLOT] when decoy coverage ≥ [SLOT] | [SLOT] | | | report as refuted |
| the reference pair (granite vs itself at two temperatures, if run) | [SLOT] | | | |
| certified fraction, per format, interval | [SLOT] | | | |

## 7. Analysis plan, frozen with the predictions

- Per cell: `select` under the ratified rule at `q`; the four replicate
  target sets reported as a stability check (proposal §2, Design 1).
- Leave-one-system-out across the pool: every fittable choice (there are
  few: the equivalence threshold and the stratum floor are already
  frozen) is re-fitted with one system held out, and the certified
  fractions reported from the held-out fits (methods METHODS rail 3).
- The two-way partition of the certified fraction by format and domain,
  the same arithmetic as paper one's section 8, computed once, on the
  registered cells.
- Every number with its denominator and interval (study METHODS); Wilson
  intervals on fractions, Clopper-Pearson on per-system counts, as paper
  one.
- Nothing fitted on the cross-system recordings is used to choose which
  cells or pairs are reported.

## 8. Instruments and provenance

`scripts/run_study.py` generalised to the roster, or a sibling runner;
`scripts/diagnose_channels.py` under MTH-025; `scripts/agent_decision_variation.py`
where the agent format enters; the drift control. Every recording is a
checkpoint with its activation store committed as it exists, every
analysis a per-cell report file; the matrix file is never cited.

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

Three things make this cheap: the slots are few and named; the
predictions table has its "if outside" column filled already, so filing a
number commits to a consequence; and the freeze is a commit and a tag,
which the repository already does for everything else.

**Evidence:** STD-012, STD-013, BCH-019, MTH-023 to MTH-026, the compare
METHODS and STATE, paper one's section 8.
**Reopen if:** the cross-system proposal is ratified in a form other than
Design 1, which rewrites §4 and §5; or the agent titration certifies the
agent format at some `k`, which adds its cells to §3.
