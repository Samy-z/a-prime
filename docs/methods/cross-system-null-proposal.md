# The cross-system null — PROPOSAL, awaiting owner ratification

**Status: PROPOSAL, drafted 2026-10-20 by the cloud session and revised the
same day after an adversarial verification pass refuted its first
recommendation (§2, Design 1). Not a decision. Nothing here is frozen;
nothing may be recorded against it until an owner ratification is appended
to this file with a date and the methods STATE points at that append.**
Written to the methods STATE queue opened 2026-10-16 (HANDOFF §24
amendment), which gates paper two's pre-registration
(`docs/study/preregistration-2-draft.md`).

The question: A versus A-prime calibrates one system against its own
variation. A versus B, where B is a different system, has two
self-variances and no entry says whose null certifies the comparison. This
proposal defines the terms, names the candidate designs, measures what each
does to the estimator in `src/aprime/fdr.py` with a committed instrument,
says what the recorder needs, how the stored-baseline regime fits, and
recommends one design.

## 0. Terms, fixed here so that the two proposals agree

- `b`: the number of baseline clouds a system has in a roster, the first
  run counted. Today every system has `b = 1` and the baseline system
  `b = 2` (A and A-prime).
- Within pairs of a system: every pair of its baseline clouds, `C(b, 2)` of
  them; `b = 2` gives one pair, `b = 3` gives three. The pairs of one system
  are not independent of one another (they share clouds) but each has the
  same marginal distribution under the null below.
- `r`: the number of decoy pairs that stand against one target in a
  selection. Today `r = 1`. The agent titration's `m` dial
  (`docs/methods/agent-self-variance-titration-proposal.md`) is `b` for the
  baseline system; its point with arms A, A', A'', B has `b = 3` and `r = 3`.
- Per input `i`, the null `H0_i`: **A and B have the same output
  distribution on `i` at the level the channel reads.** For the partition
  channels (share of answers, new answers, spread) that is the mode
  distribution after the judge merges paraphrases, so two models giving
  the same answer in different words satisfy it. For the text-level
  channels it is the pairwise relation between samples, where house style
  enters; §7.

## 1. What the estimator assumes, read from the code

`fdr.estimate_fdr` is `(1 + d) / max(t, 1)` with `t` the targets and `d` the
decoys at or above a cut, compared as values (ENG-010). `select` takes the
most permissive cut with the estimate at or under `q`; `best_achievable`
reports the lowest estimate any cut reaches; `select_stratified` runs
`select` once per output shape with that shape's decoys and requires
targets, decoys and strata of one length. Four consequences carry into any
cross-system design:

1. **The floor.** With no decoys above the cut the estimate is `1 / t`, so
   nothing is reportable below `1/q` findings (MTH-024), and no design
   below changes it, because the `+1` is per selection.
2. **The null is the decoys' order statistics.** Paper one's five silent
   cells at k=6 (two extraction, three agent) are all resolution-limited
   under MTH-025. In the two extraction cells the binding fact was one or
   two decoys at or near the top value against 17 and 18 inputs above the
   cut; banking extraction detected 21 of 21 when recorded at k=20, and
   hospitality extraction is untested at k=20 (STD-010, STD-013). In the
   agent cells the binding count is separating inputs, 4, 4 and 0, with
   the decoys spanning the fired targets' range (STD-011 appends).
3. **Validity rests on equal marginals.** For an input where `H0_i` holds,
   the target score and every decoy score must share a distribution. Under
   `H0_i` the four clouds `A, A', B, B'` are draws from one distribution,
   so every two-cloud score among them has the same marginal distribution.
   They are not jointly exchangeable: `s(A, B)` shares a cloud with
   `s(A, A')` and with `s(B, B')`, which share none; the estimator's
   expectation argument needs only the marginals.
4. **The reference is not interchangeable with the candidate in the code.**
   `stats.novel_mode_mass(baseline, candidate)` is asymmetric by design,
   and `detect` derives the output-shape strata, hence the per-stratum
   selections and their floors, from the baseline's clouds
   (`gating.strata_from_baseline`). A rule that "does not depend on which
   system is called A" is not available without changing both; the rule
   below declares the orientation instead.

## 2. The candidate designs, measured

Notation: clouds `A, A', B, B'` of `k` samples per input; `s(X, Y)` a
channel's score; targets `T_i = s(A_i, B_i)`; the reference pair
`D^A_i = s(A_i, A'_i)`; the candidate pair `D^B_i = s(B_i, B'_i)`.

The instrument is `scripts/simulate_null_designs.py`: a synthetic cell of
`n = 40` inputs, each with a mode distribution drawn at random, half of
them changed by a mixture of severity `sev`, clouds of `k` samples, the
mode-share distance on the true modes so that only the estimator is under
test, grid-valued scores and value-compared ties as in the detector. It
reports realised false-discovery rate, power and the probability that a
cell reports anything, for three selectors. The two commands quoted below
are `--reps 400` and `--reps 400 --modes 3 --changed 20`.

### Design R — the reference null, with four arms recorded

Select exactly as today: targets `s(A, B)`, decoys `s(A, A')`, `r = 1`.
Record `B'` as well, and use it for three things that are reported and do
not select: the candidate's self-variance (`D^B` as a distribution, the
quantity the agent row taught the project to report); the **reverse
selection**, decoys `s(B, B')` against the same targets, whose count says
whether B is further from A than B is from itself; and the stored-baseline
regime (§6), where it is the only pair recorded under the target's load.
Orientation is declared: A is the reference, its clouds define the strata
and the direction of the new-answers check, and the reverse orientation is
computed and reported beside it.

Validity: the same equal-marginals argument the current estimator rests on.
Power: that of the current estimator, which is the most any design below
reaches. Cost: four arms.

### Design 1 — pooled null, ratio-adjusted estimator (the first recommendation, withdrawn)

Decoys pooled, `2n` of them, estimate `(1 + d/2) / t`. The pooled count has
the same expectation at every cut as today's and half the variance, and
the first draft of this proposal read that as added resolution. The
instrument says otherwise, in both regimes it was run in:

| k | sev | single: FDR, power, P(any) | pooled r=2: FDR, power, P(any) | max: FDR, power, P(any) |
|---|---|---|---|---|
| 6 | 0.9 | 0.002, 0.009, 0.018 | 0.000, 0.000, 0.000 | 0.000, 0.000, 0.000 |
| 20 | 0.7 | 0.011, 0.081, 0.152 | 0.002, 0.023, 0.040 | 0.002, 0.019, 0.037 |
| 20 | 0.8 | 0.018, 0.202, 0.355 | 0.005, 0.095, 0.170 | 0.004, 0.083, 0.155 |
| 20 | 0.9 | 0.020, 0.316, 0.530 | 0.012, 0.207, 0.350 | 0.010, 0.196, 0.343 |

(`--reps 400`, four modes, half changed; the three-mode run with 20 changed
gives the same ordering at every row.) **Pooling never reports more often
than the single decoy. At k=20 it reports between a quarter and two thirds
as often (0.040 against 0.152, 0.170 against 0.355, 0.350 against 0.530 up
the severity column), and at k=6 it reports nothing where the single decoy
reports in 1 to 2 percent of cells.** The reason is in how `select` works: it takes the most permissive
cut whose estimate clears `q`, so it profits from draws in which the
decoys happen to fall below a cut, and halving the decoy count's variance
removes those draws. The realised rate of the single form sits far under
`q` at this size (0.02 at its highest row), so the reports it makes that
pooling would not are overwhelmingly true. What pooling buys is a flagged
set that varies less between draws, and it pays for that in reports.

Pooling is therefore not the selector. The ratio-adjusted estimator is
still the right generalisation to freeze for the titration's `m` dial,
whose expectation is that more decoys do not move the agent cells, and the
instrument says why: at the floor, more decoys cost reports.

### Design 2 — per-input maximum

Decoy `max(D^A_i, D^B_i)`, estimator unchanged. Under `H0_i` the three
scores share marginals; the maximum of two of them exceeds the target more
often than not, and at the top of the grid the decoy count runs at about
twice the null target count, decaying below it (2.2, 2.1 and 1.95 at the
top three cuts of the k=6 grid over 2,000 all-null cells from the
instrument's `cell`; the pooled count halved runs at 1.0 to 1.1 at the
same cuts, which is the equal-marginals argument measured). The
instrument's third column: the realised rate about half the single form's,
which is already a quarter of `q` at this size, and the reports fewer at
every row. Valid, symmetric, and nothing gained.

### Design 3 — two one-sided selections

`select` against `D^A` and against `D^B`. With a symmetric score the two
selections rank the same targets, so the flagged sets are nested: the
intersection is the more conservative of the two selections and the union
the more permissive, each controlled at `q` against its own null. "Run
both" is therefore a choice of one, and Design R is Design 3 with the
choice declared and the other count reported.

### Not proposed

Head-to-head competition (each target against its own decoy, keep the
winner) discards the ranking across inputs that `select` works from.
Averaging the four cross pairs `s(A,B), s(A,B'), s(A',B), s(A',B')` into
the target breaks the equal-marginals argument, because an average of four
correlated scores is not distributed as one two-cloud score; the three
extra cross pairs are **replicate target sets**, selected separately and
reported as a stability check, as MTH-018 reported power per seed.

## 3. Recommendation

**Design R.** The combination rule, to be frozen by a dated append before
any cross-model tuple is recorded:

- roster `A, A', B, B'`, all four interleaved in one tuple per
  `(input, sample index)`, MTH-015 applying to every arm;
- A is the reference: its clouds define the output-shape strata and the
  per-stratum floors, and the new-answers check is read from A to B;
- selection: targets `s(A, B)`, decoys `s(A, A')`, `r = 1`, `select` and
  `select_stratified` as they stand;
- reported beside every selection, never selecting: the candidate's
  self-variance `s(B, B')`, the reverse selection against `s(B, B')`, the
  pooled estimate `(1 + d/2)/t` at the chosen cut, and the three replicate
  target sets;
- seed policy per system (MTH-023 correction: mirror each system's
  deployment, record the regime), with `decoy_independence_warnings`
  extended to every within pair.

Why this and not the first draft's pooling: the instrument, §2. Why four
arms at all if only two decoys select: the candidate's self-variance is a
finding in its own right (the agent row), the reverse count is the second
half of "whose null", and the stored-baseline regime has no other live
pair.

## 4. What the recorder and the estimator need

`record` requires exactly `ARMS = ("A", "A_prime", "B")` (`adapter.py`),
rotates the lead arm by `idx % 3`, writes the three samples of an
`(input, sample_idx)` together or not at all, and `load_checkpoint` calls
a triple complete when `set(ARMS)` is present and dead when every arm
errored. The roster change:

- the roster is a property of the run, from the `arms` mapping, with the
  decoy requirement generalised (no roster without a within pair for the
  reference);
- the atomic unit is the full roster for one `(input, sample_idx)`:
  rotation over its length, completeness as all arms present, dead as all
  arms errored, resume unchanged;
- the roster enters the configuration hash;
- `detect` takes the pairing (reference, selecting decoy pair, reported
  pairs) instead of reading clouds by the names A, A-prime, B;
  `Recording.clouds` needs nothing;
- the preflight asks one question per arm; the cost is `len(roster) / 3` of
  today's per-input time, 4/3 for this design.

The estimator, for the reported pooled number and for the titration's `m`
dial: `(1 + d/r) / t` with `r` the decoy pairs per target, the `r = 1`
path byte-identical to today and asserted by a test. `select_stratified`
requires targets, decoys and strata of one length; with `r > 1` every decoy
needs a stratum label, and the rule is that **a decoy carries the stratum of
its input**, so the signature grows a decoy-to-input mapping. The 15-target
example a reader might work (one of two decoys above the cut, `1.5/15 =
0.100`) holds only within one stratum.

One mismatch to settle before anything freezes: `best_achievable`'s
docstring says ties in the estimate go to the cut admitting more targets,
"matching `select`", and the code keeps the first cut it meets in
descending order, which is the one admitting fewer. Either is defensible;
the frozen rule must say which.

## 5. Validation: not the null pair

The first draft proposed a null pair, one model recorded as both A and B
under two names, as the validity check, "as MTH-018 validated the single
decoy on the stub". It cannot be that. MTH-018 ran on a stub with known
changed inputs, so its realised rate was a fraction; on an all-null cell
the rate is 1 if anything is flagged and 0 otherwise, and the instrument
puts the probability of flagging anything on an all-null cell at 0.0000
for every design at `n = 40`, k=6 and k=20. A null pair passes almost
surely whether or not the design is sound.

What validates: **the stub sweep, MTH-018's protocol**, at the registered
`k` and `n` with known truth, run for `r = 1` and `r = 2`, before `n` is
filed in the pre-registration. The null pair stays, as two things it can
do: a hard stop (any flagged input on a null pair is a failure, because it
is a false discovery by construction) and an exchangeability statistic
with an acceptance band. The instrument gives the band: the share of
targets at or above the pooled decoy median on an all-null cell has mean
0.53 to 0.54 at k=20 (ties on the grid push it above one half) with a
central 95 percent range of 0.35 to 0.70 in both regimes; at k=6, mean
0.58 to 0.59, range 0.35 to 0.78 with four modes and 0.40 to 0.75 with
three. The pre-registration fills its band from the instrument at its own
`k` and `n`.

## 6. The stored-baseline regime

A was recorded weeks ago, B is live, the arms cannot be interleaved, and
the target `s(A_p1, B_p2)` spans two periods. The stored pair `(A, A')_p1`
is a null for A's self-variance under period-one load; the live pair
`(B, B')_p2` for B's under period-two load; neither holds the term time
adds, and MTH-015 says a decoy from another load regime mis-calibrates.
No decoy shares the target's regime, because the target has two.

Under Design R in this regime: the live pair is the selecting null, since
it is the one recorded under the conditions the candidate experienced;
the stored pair is reported; and certification is gated on the drift
negative control (MTH-026), whose three comparisons measure the missing
term on the same system: cross-period with the stored pair as null,
cross-period with the live pair as null, within-period as sanity. If the
control flags nothing in both cross-period comparisons, the time term is
below the certification floor for this system, corpus and gap, and the
comparison may be certified with that disclosure. If it flags, the count
and the best estimates quantify the term, and the comparison is reported
beside them and not certified at `q`. If A is no longer servable, the
control cannot run, the null is one-sided and the time term unmeasured,
and the report says so.

The period-two recording for the first control sits at 212 of 240 triples
on main (`results/drift/drift-p2.4366ced9c36980a3.jsonl`); its report is
the first number this regime gets.

## 7. The text channels carry a style confound no within-system decoy calibrates

Two models that give the same answer in different house styles satisfy
`H0_i` at the mode level and not at the pairwise text level: the
contradiction and information-direction scores between an A sample and a
B sample can exceed those between two A samples with no difference in
answer, and both within pairs sit inside one style. The null pair cannot
measure this either, because it is one model. The instrument for it is a
**style-only control**: the same model under two system prompts that change
register and not content, scored as A against B, whose certified fraction
on the text channels is the false-alarm rate the confound produces. Until
that control has run, the partition channels select in cross-system runs
and the text channels report. This is a limitation of the decoy
construction, not of the estimator, and it belongs in paper two's limits.

## 8. What this proposal asks the owner to ratify

1. Design R as the cross-system null, with the combination rule in §3
   frozen by a dated append here before any cross-model tuple is recorded.
2. The recorder roster change (§4) as an engine entry, three-arm behaviour
   unchanged.
3. The generalised estimator `(1 + d/r) / t` as an engine entry, for the
   reported pooled number and the titration's `m` dial, with `r = 1`
   byte-identical and tested, and `select_stratified` taking a decoy-to-
   input mapping with a decoy carrying its input's stratum.
4. The validation protocol (§5): the stub sweep at the registered `k` and
   `n` before `n` is filed; the null pair as a hard stop plus the
   exchangeability band from the instrument.
5. The stored-baseline gate (§6).
6. The text channels reported and not selected on in cross-system runs
   until the style-only control (§7) has run; the control itself as a
   registered instrument.
7. Which way `best_achievable` breaks ties in the estimate, so that the
   docstring and the code agree before the freeze.

## 9. Evidence, and what was not verified

`src/aprime/fdr.py`, `stats.py`, `detect.py`, `gating.py`, the recorder's
`record` and `load_checkpoint`, at the commit this file lands in;
MTH-007, MTH-015, MTH-018, MTH-023 and correction, MTH-024 and correction,
MTH-025, MTH-026; STD-010, STD-011 appends, STD-012, STD-013;
`scripts/simulate_null_designs.py` and `tests/test_simulate_null_designs.py`
for every simulation figure; the verification pass of 2026-10-20 (a
session artifact, not committed), whose refutations this revision answers.

Proteomics references, from a web search on 2026-10-20 that confirmed each
paper's existence and gist but not its exact estimator: Elias and Gygi
2007, *Nature Methods* 4:207; Käll, Storey, MacCoss and Noble 2008,
*J. Proteome Res.* 7:29; Keich, Tamura and Noble 2019, *J. Proteome Res.*,
averaged target-decoy competition; Emery, Hasam, Noble and Keich 2020,
multiple competition-based FDR control. The ratio form `(1 + d/r) / t` is
attributed to that literature on the strength of titles and abstracts;
**before paper two cites it, the full texts are to be read for the exact
formula and its conditions.** The claim that the single-decoy guarantee is
Barber and Candès's is inherited from `fdr.py`'s docstring and MTH-024, not
re-derived here.

**Reopen if:** the stub sweep under `r = 1` at the registered `k` and `n`
realises a rate above `q`, which would mean the equal-marginals argument
fails for these scores; the style-only control shows the partition
channels also carry a style term; or the drift control flags in a
within-period comparison, which indicts the harness.
