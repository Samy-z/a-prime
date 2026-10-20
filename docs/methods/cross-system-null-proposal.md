# The cross-system null — PROPOSAL, awaiting owner ratification

**Status: PROPOSAL, drafted 2026-10-20 by the cloud session and revised
twice the same day: once after an adversarial pass refuted its first
recommendation (§2, Design 1), once after a three-seat cross-model review
of the revision. Not a decision. Nothing here is frozen; nothing may be
recorded against it until an owner ratification is appended to this file
with a date and the methods STATE points at that append.** Written to the
methods STATE queue opened 2026-10-16 (HANDOFF §24 amendment), which gates
paper two's pre-registration (`docs/study/preregistration-2-draft.md`).

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
  them. The **star pairs** are the `b - 1` of them that share the reference
  cloud with the target, `s(A, A'), s(A, A''), ...`; the others, such as
  `s(A', A'')`, share no cloud with it.
- `r`: the number of decoy pairs that stand against one target in a
  selection, counting only star pairs, so `r = b - 1`. Today `r = 1`. The
  agent titration's `b` dial
  (`docs/methods/agent-self-variance-titration-proposal.md`) is this `b`
  for the baseline system; its point with arms A, A', A'', B has `b = 3`
  and `r = 2`, with `s(A', A'')` reported and never pooled (§1 item 3 says
  why).
- Per input `i`, the null `H0_i`: **A and B have the same output
  distribution on `i` at the level the channel reads.** For the partition
  channels (share of answers, new answers, spread) that is the mode
  distribution after the judge merges paraphrases. At its operating point
  the judge merges paraphrase, synonym and format at 97 to 100 percent but
  reorderings at 75 percent (MTH-020), so two models giving the same
  answer in systematically different styles satisfy it only as far as the
  judge merges those styles (§7). For the text-level channels it is the
  pairwise relation between samples, where house style enters directly.

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
   under MTH-025. In hospitality extraction the binding fact was one decoy
   at the top value against 18 inputs above the cut (0.111); in banking
   extraction the lowest estimate in its diagnosis file is NLI
   contradiction's 0.125, 8 inputs above every decoy (4 labelled touched,
   0 labelled quiet, 4 unlabelled), beside mode share's 0.176 with 17
   above 2, under MTH-025's lowest-estimate rule, which its precedent line
   did not apply to the NLI channel (STD-010 third append; the diagnosis
   file). Banking extraction detected 21 of 21 touched inputs when
   recorded at k=20; hospitality extraction is untested at k=20 (STD-013).
   In the agent cells the binding count is separating inputs, 4, 4 and 0,
   with the decoys spanning the fired targets' range (STD-011 appends).
3. **Validity rests on pairwise exchangeability, not on equal marginals.**
   Control at the cut `select` chooses from the data needs, for every
   input where `H0_i` holds, that swapping the target score with its decoy
   score leaves the joint distribution of all scores unchanged. Equal
   marginals give only the fixed-cut identity E[#null targets ≥ c] =
   E[#decoys ≥ c]; a counterexample with equal per-input marginals and a
   shared cell-level shock flags every input in half of all-null cells.
   Under `H0_i` the clouds `A, A', B` are draws from one distribution, so
   exchanging the labels `A'` and `B` maps `s(A, B)` to `s(A, A')` and back:
   `(T_i, D^A_i)` is exchangeable exactly, which is the condition the
   current estimator's argument uses. No relabelling of the four clouds
   exchanges `s(A, B)` with `s(A, A')` while fixing `s(B, B')`, so
   `(T_i, D^A_i, D^B_i)` is not exchangeable, and the same holds for a pair
   of baseline clouds that shares no cloud with the target: on all-null
   inputs at k=20 the instrument (block 2) finds the target the strict
   maximum among `(T, s(A,A'), s(A,A''))` on 25.3 percent of inputs against
   25.1 and 25.0 for the two star pairs, equal shares as exchangeability
   requires, but among all four scores with `s(A', A'')` added on 21.4
   against 15.3, 15.3 and 17.8. Designs that pool such pairs, or take
   their maximum, rest on conservativeness at a fixed cut, not on the
   argument `fdr.py` cites. Whether that argument covers `select`'s
   separate counting, where one input can count as a target and as a decoy
   at the same cut, is inherited and not re-derived here (§9).
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
test, scores compared as values as the detector compares them. Every
simulation figure below is its printed output at seed 20261020; the two
commands are `--reps 400` (four modes, half changed) and
`--reps 400 --modes 3 --changed 20`. Where the two regimes differ, both
are quoted.

### Design R — the reference null, with four arms recorded

Select exactly as today: targets `s(A, B)`, decoys `s(A, A')`, `r = 1`.
Record `B'` as well, and use it for two things that are reported and do
not select: the candidate's self-variance (`D^B` as a distribution, the
quantity the agent row taught the project to report) and the **reverse
selection**, decoys `s(B, B')` against the same targets, whose count says
whether B is further from A than B is from itself. In the stored-baseline
regime (§6) it is the only pair recorded under the candidate's load and is
the selecting null there. Orientation is declared: A is the reference, its
clouds define the strata and the direction of the new-answers check, and
the **reverse orientation** (B as reference: strata from B's clouds, the
new-answers check read from B to A) is computed and reported beside it.

Validity: the current pairwise-exchangeability argument, unchanged; of the
designs here it is the only one for which that argument holds in exactly
the form the estimator uses. Power: that of the current estimator, which
is the most any design below reaches. Cost: four arms.

### Design 1 — pooled null, ratio-adjusted estimator (the first recommendation, withdrawn)

Decoys pooled, `2n` of them, estimate `(1 + d/2) / t`. The pooled count has
the same expectation at every cut as today's and half the variance, and
the first draft of this proposal read that as added resolution. The
instrument says otherwise:

| k | sev | single: FDR, power, P(any) | pooled r=2: FDR, power, P(any) | max: FDR, power, P(any) |
|---|---|---|---|---|
| 6 | 0.9 | 0.002, 0.009, 0.018 | 0.000, 0.000, 0.000 | 0.000, 0.000, 0.000 |
| 20 | 0.7 | 0.011, 0.081, 0.152 | 0.002, 0.023, 0.040 | 0.002, 0.019, 0.037 |
| 20 | 0.8 | 0.018, 0.202, 0.355 | 0.005, 0.095, 0.170 | 0.004, 0.083, 0.155 |
| 20 | 0.9 | 0.020, 0.316, 0.530 | 0.012, 0.207, 0.350 | 0.010, 0.196, 0.343 |

(Four modes, half changed; the three-mode run with 20 changed keeps the
ordering at every row.) **In every row of both runs, pooling reports no
more often than the single decoy. At k=20 it reports between none and two
thirds as often (0.000 against 0.025 at severity 0.5, 0.013 against 0.077
at 0.6, then 0.040 against 0.152, 0.170 against 0.355 and 0.350 against
0.530 at 0.7 to 0.9), and at k=6 in 0 of 400 cells at every severity with
four modes and 1 of 400 at severity 0.9 with three, where the single decoy
reports in 0.3 to 1.8 percent of cells at severities 0.6 to 0.9.** The
reason is in how `select` works. A cut admitting `t` targets tolerates at
most `q t - 1` single decoys at or above it, or `2(q t - 1)` pooled ones:
with `t` under 15 that is none of 40 against none of 80, and above it the
pooled tolerance doubles while the pooled count's spread about its doubled
mean is narrower, so the lucky low counts the most-permissive-cut rule
exploits are rarer. Halving the decoy count's variance is the same fact
stated for the mean. The realised rate of the single form sits far under
`q` at this size (0.02 at its highest row, averaged over cells that mostly
report nothing), and measured directly the flags it makes on inputs
pooling does not flag are 92 to 95 percent true at the three k=20 rows
(488 of 533, 887 of 953, 882 of 928; 91 to 95 percent with three modes)
and 80 to 86 percent at k=6 on 10 to 86 flags. Pooling buys a flagged set
that varies less between draws and pays for it in reports, most of them
true.

Pooling is therefore not the selector. The ratio-adjusted estimator stays
as the candidate generalisation for the titration's `b` dial, over the
star pairs only, and the instrument runs that configuration (block 2;
titration §2): at k=20 and severity 0.9 the two star pairs at `r = 2`
report in 0.362 of cells against the single decoy's 0.490, with power
0.219 against 0.300 and realised rate 0.010 against 0.019, and all three
pairs at `r = 3` in 0.295; at the floor, more decoys cost reports.

### Design 2 — per-input maximum

Decoy `max(D^A_i, D^B_i)`, estimator unchanged. Under `H0_i` the three
scores share marginals; the maximum of two of them exceeds the target more
often than not, and at the top of the grid the decoy count runs at about
twice the null target count: in expectation the ratio is
`2 - P(both decoys ≥ c) / P(one decoy ≥ c)`, at most 2, and the instrument
(block 5, 2,000 all-null cells) measures 2.03, 1.99 and 1.91 at the top
three cuts of the k=6 grid with four modes (69, 903 and 5,825 null
targets) and 1.56, 1.87 and 1.94 with three (41, 526 and 3,304), the top
cut resting on few targets; the pooled count halved runs at 1.01, 1.00,
0.99 and 0.78, 0.94, 1.00 at the same cuts, expectation exactly 1, which
is the equal-marginals identity measured. The instrument's third column:
the realised rate between none and half of the single form's (0.18, 0.22
and 0.50 at k=20 severities 0.7 to 0.9; zero at the rows below), where the
single form's own rate is about a fifth of `q` at its highest row (0.020
and 0.021 in the two regimes), and the reports fewer at every row where
the single form reports at all. Conservative at a fixed cut, symmetric,
and nothing gained.

### Design 3 — two one-sided selections

`select` against `D^A` and against `D^B`. Both selections cut the same
target vector, so under `select` the flagged sets are nested and the
intersection and union are the two selections themselves. Under
`select_stratified`, which §3 runs, each stratum's pair is nested but the
overall sets need not be, because one null can admit a stratum the other
cannot. Either way, taking whichever selection the data favour is not
controlled at `q` by either null, so "run both" is a choice of one, made
before the data, and Design R is Design 3 with the choice declared and the
other count reported.

### Not proposed

Head-to-head competition (each target against its own decoy, keep the
winner) discards the ranking across inputs that `select` works from.
Averaging the four cross pairs `s(A,B), s(A,B'), s(A',B), s(A',B')` into
the target breaks the exchangeability argument, because an average of four
correlated scores is not distributed as one two-cloud score; the three
extra cross pairs are **replicate target sets**, selected separately and
reported as a stability check, as MTH-018 reported power per seed.

## 3. Recommendation

**Design R.** The combination rule, to be frozen by a dated append before
any cross-model tuple is recorded:

- roster: every system in the run contributes at least two clouds, and
  all arms of the run are interleaved in one tuple per
  `(input, sample index)`, MTH-015 applying to every arm; a pair-cell
  reads its `A, A', B, B'` from that tuple. Whether a roster may hold more
  than one pair (one eight-arm roster for a four-model pool, the layout
  the pre-registration costs in its §5) departs from the "four arms" of
  the 2026-10-16 queue entry and is put to the owner in §8 item 1 rather
  than assumed;
- A is the reference of each pair, declared before recording: its clouds
  define the output-shape strata and the per-stratum floors, and the
  new-answers check is read from A to B;
- selection: targets `s(A, B)`, decoys `s(A, A')`, `r = 1`, `select` and
  `select_stratified` as they stand, except in the stored-baseline regime
  (§6), where the decoys are `s(B, B')` and `s(A, A')` is reported, A's
  stored clouds still defining the strata;
- reported beside every selection, never selecting: the candidate's
  self-variance `s(B, B')`; the reverse selection against `s(B, B')`; the
  reverse orientation; the pooled estimate `(1 + d/2)/t` at the
  selection's cut, or, when the selection is empty, at the cut
  `best_achievable` reports for the selecting pair under the tie rule of
  §8 item 7; and the three replicate target sets;
- seed policy per system (MTH-023 correction: mirror each system's
  deployment, record the regime), with `decoy_independence_warnings`
  extended to every within pair.

Why this and not the first draft's pooling: the instrument, §2, and the
exchangeability argument, §1 item 3. Why four arms at all if only one pair
selects: the candidate's self-variance is a finding in its own right (the
agent row), the reverse count is the second half of "whose null", and the
stored-baseline regime has no other live pair.

## 4. What the recorder and the estimator need

`record` requires exactly `ARMS = ("A", "A_prime", "B")` (`adapter.py`),
rotates the lead arm by `idx % 3`, writes the three samples of an
`(input, sample_idx)` together or not at all, and `load_checkpoint` calls
a triple complete when `set(ARMS)` is present and dead when every arm
errored. The roster change:

- `ARMS` and `adapter.check_arm` become roster-aware (arm labels validated
  against the run's roster), with the three constructors that call
  `check_arm` (`stub.py`, `systems/ollama.py`, `cells/cell.py`) and the
  preflight updated; no field is added to `Invocation`, `Trace` or
  `Response`, so this changes the harness's arm vocabulary, not the
  interface the adapter docstring guards;
- the roster is a property of the run, from the `arms` mapping, with the
  decoy requirement generalised (no roster without a within pair for the
  reference);
- the atomic unit is the full roster for one `(input, sample_idx)`:
  rotation over its length, completeness as all arms present, dead as all
  arms errored, resume unchanged;
- the roster enters the configuration hash only when it differs from
  `(A, A_prime, B)`, so every committed checkpoint keeps its hash
  (`compute_config_hash` digests the whole parameter dict, and
  `run_study.py` says what a changed hash does: it orphans the recording
  on disk); a test asserts the nine k=6 and four k=20 hashes unchanged;
- `detect` takes the pairing (reference, selecting decoy pairs, reported
  pairs) instead of reading clouds by the names A, A-prime, B;
  `Recording.clouds` needs nothing;
- the preflight asks one question per arm; the cost is `len(roster) / 3` of
  today's per-input time, 4/3 for this design.

The estimator, for the reported pooled number and for the titration's `b`
dial: `(1 + d/r) / t` over the `r = b - 1` star pairs, the `r = 1` path
byte-identical to today and asserted by a test; the pairs that share no
cloud with the target are reported and never pooled. `select_stratified`
requires targets, decoys and strata of one length; with `r > 1` every decoy
needs a stratum label, and the rule is that **a decoy carries the stratum of
its input**, so the signature grows a decoy-to-input mapping.
`best_achievable` takes `r` too, since the titration's reading rule reads
`1/t` at its best cut.

One mismatch to settle before anything freezes: `best_achievable`'s
docstring says ties in the estimate go to the cut admitting more targets,
"matching `select`", and the code keeps the first cut it meets in
descending order, which is the one admitting fewer. Either is defensible;
the frozen rule must say which.

## 5. Validation: what the stub sweep tests, and what the null pair can see

**The stub sweep (MTH-018's protocol) validates the selector at the
registered `k` and `n`.** It runs on MTH-018's stub (`aprime.stub`, the
`mode_share` perturbation, the `_run` protocol of `tests/test_pipeline.py`)
at the registered `k` over candidate `n` of 40, 60, 100 and 200, with half
the inputs changed at strengths 0.5 to 0.9, under `r = 1` and the star
`r = 2`, with the seed count filed beside its Monte Carlo standard error.
Its criterion is the one the project already asserts: the mean
false-discovery proportion over seeds at or under `q + 0.02` in every
(strength, `r`) cell and no single seed above 0.35
(`tests/test_pipeline.py`; the MTH-018 amendment reopens at 0.12), and a
strength whose P(any report) is under 0.10 is void, not passed. A single
seed above `q` is sampling: MTH-018's own validation realised 0.101 at
`q = 0.10`. It runs before `n` is filed, so the pre-registration can read
`s` at each candidate `n`, and V's row then records the realised rate at
the `n` filed. **It cannot test equal marginals between two systems**,
which hold in the stub by construction (an unchanged input's B behaviour
is a copy of the baseline table), and neither can the null pair, which is
one model: no check in this protocol tests them for cross-model scores,
and paper two states them as an assumption.

**The null pair**, one model recorded as both A and B under two names, is
a smoke test of the recording harness, not of the combination rule. Under
every sound design the instrument ran, a null pair passes almost surely:
P(any report) 0.0000 in 2,000 all-null cells at `n = 40` for k=6 and k=20
with four modes, 1 in 2,000 at k=6 with three (block 3). The guarantee
itself permits a false flag at rate up to `q` per cell, so a flag on a
null pair means the recording or the channel's scores depart from what the
instrument models, and the hard stop is for that: with the decoy arm tied
to the reference, as a pinned or cached seed makes it (MTH-023 and its
correction), `A'` copying each sample of `A` with probability 0.7 flags in
0.318 of null cells at k=6 and 0.475 at k=20 (0.100 and 0.215 with three
modes), probability 0.9 in 0.885 and 0.980, and a copy in every cell. The
null pair therefore stays, as two things: a **hard stop** (any flag by any
selection run on it, selecting or reported, on any channel that runs,
stops recording in that cell until the departure is found) and an
**exchangeability statistic**: among the inputs whose target and
reference decoy differ as values (ENG-010), the share with the target
above. Under pairwise exchangeability with independent inputs that count
is Binomial(m, 1/2) whatever the score distribution, the grid or the
mode structure, so its band is the binomial's central 95 percent at the
`m` non-tied inputs the cell shows (at `m = 30`, 0.32 to 0.68); the
instrument confirms it (block 4: mean 0.497 to 0.504, central 95 percent
0.31 to 0.69 at a mean `m` of 26 to 27 for k=6 and 0.32 to 0.68 at 32 to
33 for k=20, both regimes). The first draft's statistic, the share of
targets at or above the pooled decoy median, is withdrawn: its band moved
with the mode count and the tie convention and read 1.0 wherever the
decoy median was zero.

## 6. The stored-baseline regime

A was recorded weeks ago, B is live, the arms cannot be interleaved, and
the target `s(A_p1, B_p2)` spans two periods. The stored pair `(A, A')_p1`
is a null for A's self-variance under period-one load; the live pair
`(B, B')_p2` for B's under period-two load; neither holds the term time
adds, and MTH-015 says a decoy from another load regime mis-calibrates.
No decoy shares the target's regime, because the target has two.

Under Design R in this regime: the live pair is the selecting null, since
it is the one recorded under the conditions the candidate experienced,
with A's stored clouds still defining the strata (§3); the stored pair is
reported; and certification is gated on the drift negative control
(MTH-026), whose three comparisons measure the missing term on the same
system: cross-period with the stored pair as null, cross-period with the
live pair as null, within-period as sanity. **The gate is read from the
control's diagnosis under MTH-025, never from its flag count**, because
MTH-026 itself says a zero count at `n = 40` is consistent with up to nine
drifted inputs: if in both cross-period comparisons no channel separates
more than [SLOT] inputs above every decoy (`targets_above` at the best
cut with `decoys_above = 0`), the time term is below what this corpus
resolves at the control's `k` and the comparison may be certified with
that count disclosed as the upper bound on the term; otherwise the
separating counts and best estimates quantify the term and the comparison
is reported beside them, not certified at `q`. The control must run at the
comparison's `k`: the first control (`scripts/run_drift_control.py`,
`N, K, Q = 40, 6, 0.10`) cannot bound the time term of a k=20 comparison,
because the separating count is set by `k` (MTH-024 correction). For the
gate to run, the control's per-comparison record needs the
`best_achievable` output per channel (estimate, cut, targets and decoys
above) and the sorted target and decoy arrays, which `detect` already
computes; that is an engine entry (§8 item 5). If A is no longer
servable, the control cannot run, the null is one-sided and the time term
unmeasured, and the report says so.

The period-two recording for the first control sits at 212 of 240 triples
on main (`results/drift/drift-p2.4366ced9c36980a3.jsonl`); its report is
the first number this regime gets.

## 7. Both channel families carry a style term no within-system decoy calibrates

Two models that give the same answer in different house styles satisfy
`H0_i` at the mode level only where the judge merges the styles: at 0.7
it merges paraphrase, synonym and format at 97 to 100 percent but
reorderings at 75 percent (MTH-020; hedging is a detected class under
MTH-021), so a systematic ordering habit that differs between two models
splits same-answer outputs into separate modes a quarter of the time, and
both within pairs sit inside one style. At the pairwise text level the
term is larger still: the contradiction and information-direction scores
between an A sample and a B sample can exceed those between two A samples
with no difference in answer. The null pair cannot measure this either,
because it is one model. The instrument for it is a **style-only
control**: the same model under two system prompts that change register
and not content, scored as A against B, whose certified fraction on every
channel, partition and text alike, is the false-alarm rate the confound
produces on that channel. A channel family selects in cross-system runs
only once its certified fraction on the control is at or under `q`; until
the control has run, no channel selects, or, if the owner prefers to let
the partition channels select meanwhile, the 25 percent reorder split is
disclosed beside every certified fraction (§8 item 6). This is a
limitation of the decoy construction, not of the estimator, and it belongs
in paper two's limits.

## 8. What this proposal asks the owner to ratify

1. Design R as the cross-system null, with the combination rule in §3
   frozen by a dated append here before any cross-model tuple is
   recorded; and whether a roster may hold more than one pair (the
   eight-arm layout), which departs from the "four arms" of the
   2026-10-16 queue entry.
2. The recorder roster change (§4) as an engine entry, including
   `adapter.check_arm` and the hash rule that keeps every committed
   checkpoint's hash, three-arm behaviour unchanged.
3. The generalised estimator `(1 + d/r) / t` over the `b - 1` star pairs
   as an engine entry, for the reported pooled number and the titration's
   `b` dial, with `r = 1` byte-identical and tested, `select_stratified`
   taking a decoy-to-input mapping with a decoy carrying its input's
   stratum, and `best_achievable` taking `r`; its condition, the joint
   exchangeability of `(s(A,B), s(A,A'), s(A,A''))` under `H0_i`, named
   as measured by the instrument and to be checked against the literature
   (§9), not as a proven guarantee.
4. The validation protocol (§5): the stub sweep at the registered `k`
   over candidate `n` before `n` is filed, with its criterion; the null
   pair as a hard stop plus the sign statistic with its binomial band.
5. The stored-baseline gate (§6), read from the separating count at the
   comparison's `k`, with the drift-control record change that lets it
   run.
6. The style-only control (§7) as a registered instrument, read per
   channel family; and whether no channel selects in cross-system runs
   until it has run, or the partition channels select meanwhile with the
   reorder split disclosed.
7. Which way `best_achievable` breaks ties in the estimate, so that the
   docstring and the code agree before the freeze.

## 9. Evidence, and what was not verified

`src/aprime/fdr.py`, `stats.py`, `detect.py`, `gating.py`, `adapter.py`,
the recorder's `record` and `load_checkpoint`, `scripts/run_study.py` and
`scripts/run_drift_control.py`, at the commit this file lands in;
MTH-007, MTH-015, MTH-018 and amendment, MTH-020, MTH-021, MTH-023 and
correction, MTH-024 and correction, MTH-025 and amendment, MTH-026;
STD-010 and appends, STD-011 appends, STD-012, STD-013;
`tests/test_pipeline.py` (the bounds the sweep inherits);
`scripts/simulate_null_designs.py` and `tests/test_simulate_null_designs.py`
for every simulation figure, at the two commands named in §2; the two
review passes of 2026-10-20 (session artifacts, not committed), whose
confirmed findings this revision answers.

The attribution of the `+1` correction to Barber and Candès is inherited
from `fdr.py`'s docstring and MTH-024; neither states, and this proposal
does not derive, a finite-sample guarantee for separately scored targets
and decoys, and the exchangeability condition in §1 item 3 is the one that
argument uses, stated here without its proof.

Proteomics references, from a web search on 2026-10-20 that confirmed each
paper's existence and gist but not its exact estimator: Elias and Gygi
2007, *Nature Methods* 4:207; Käll, Storey, MacCoss and Noble 2008,
*J. Proteome Res.* 7:29; Keich, Tamura and Noble 2019, *J. Proteome Res.*,
averaged target-decoy competition; Emery, Hasam, Noble and Keich 2020,
multiple competition-based FDR control. Two of the four are, by their own
titles, competition procedures, which §2 declines, and the separate-list
form `fdr.select` uses is not what they describe; the non-competitive
ratio form on separate lists is attributed to none of them until the full
texts are read, and **its validity at `r > 1` rests on the exchangeability
argument of §1 and the instrument's block 2, not on the citations.**

**Reopen if:** the stub sweep under `r = 1` at the registered `k` and `n`
realises a seed-mean rate above `q + 0.02` in any cell, which would indict
the selector at that `k` and `n`; the style-only control certifies a
fraction at or above `q` on a partition channel, which makes the reorder
split a selecting-channel defect and not a text-channel one; or the drift
control flags in a within-period comparison, which indicts the harness.
