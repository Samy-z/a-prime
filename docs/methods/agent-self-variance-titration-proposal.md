# Agent self-variance, titrated — PROPOSAL, dated 2026-10-20, awaiting owner ratification

**Status: PROPOSAL, revised twice on the day it was drafted, the second
time after a three-seat cross-model review. Not a decision.** Point 1
(banking-agent at k=20, `b = 2`, three arms, temperature 0.2) is the
owner's own direction of 2026-10-17 (methods STATE queue), uses only the
configuration `scripts/run_study.py` already hashes, and carries its
expectation in STD-011's second append, so it records without further
ratification. **No other grid point may be recorded until the owner
ratifies the grid, the prerequisites in §6 and the generalised estimator
it needs, by a dated append here, with each point's sizing in a dated
entry (CLAUDE.md: no study-shaping parameter outside a dated entry); the
§5 reading rules are frozen before point 1's file is read.** Written to
the methods STATE queue opened 2026-10-17 at the owner's direction:
investigate the agent limitation with clear numbers before a reviewer
does.

Terms (`b`, within pairs, `r`) are fixed in
`docs/methods/cross-system-null-proposal.md` §0 and used here unchanged:
`b` baseline clouds per system with the first run counted; `r = b - 1`
the within pairs that share the reference cloud with the target (the star
pairs), which are the decoy pairs that select; the remaining
`C(b, 2) - (b - 1)` pairs are reported and never pooled.

## 1. What is being titrated

The agent row at k=6 was silent in three of three domains and classified
resolution-limited under MTH-025 (STD-011 second append, corrected by the
third append and the MTH-025 amendment, confirmed by the fourth): the
decoys, the second baseline run scored against the first, span 0 to 0.83
in banking and logistics and 0 to 1.0 in hospitality, covering the fired
targets' range except at most the top value; four fired inputs stand
above every decoy in banking and in logistics, none in hospitality (whose
best cut admits 5 targets, 3 fired and 2 quiet, above 1 decoy at the top
value), and the floor needs ten. The decision-level reading (STD-011
first append) says why: at the level of the decision token the fault
moves the agent about as much as the agent moves itself between two
identical runs (median total-variation on touched inputs 0.17 against a
decoy median of 0.17 in banking and logistics, 0.25 against 0.17 in
hospitality), and the whole output is distinct after normalisation on 71
to 86 percent of clustered samples (785 of 944, 674 of 956, 824 of 958,
the A cloud counted in both arm pairs).

So the quantity under titration is **the certifiable difference per agent
output**, and the dials are the things that could change it without
changing what the detector is: how finely the statistic can resolve (`k`),
how many decoy pairs the estimate stands on (`b`, through `r`), how much
of the variation is sampling entropy (`temperature`), and which part of
the output the channel reads (decision token against rationale text).
Each dial comes with an expectation filed here, before any point runs,
and each expectation names the observation that refutes it.

## 2. The dials, and what each needs before it can run

### `k`, samples per cloud: grid fineness and mass per mode

The share-of-answers statistic takes `k + 1` values; at k=6 that is seven
and the decoys crowd them. k=20 took the summary row from a false-alarm
bracket straddling the budget to 0.056 under it, and banking extraction
from nothing flagged to 21 of 21 touched inputs (STD-013). **First data
point: the banking-agent cell at k=20**, recorded on the owner's machine
on the next quiet night; its report file is the anchor the rest of this
grid is built around.

Expectation, sharpened from STD-011's second append so that a result can
refute it: the grid refines from 7 to 21 values; at point 1 the
mode-share decoy maximum falls below its k=6 value of 0.833 while fired
targets still reach the top value, and the best cut admits more targets
than point 0's four. *Refuted if* the decoy maximum at k=20 is at or
above 0.833, or if the best cut admits no more than four targets. Whether
ten or more touched inputs stand clear of every decoy is left open and is
not an expectation, because what binds in the agent cells is the number
of separating inputs, not the fineness of the grid. **If banking-agent at
k=20 still cannot reach the budget, the reading is a statement about
information per agent output on this fault, not about `k`**, and the
k=40 point runs only on the gate in §5.

A confound to declare, with its cause: the k=6 banking point was
recorded on 6 October at a mean of 65 seconds per call (median 63; the
209 logistics-agent calls made the same day ran at a mean of 75), and
every agent call since 15 October has run at a per-day mean of 13 to 17
seconds (the checkpoints' `latency_ms`: logistics 12.8 on the 15th,
hospitality 17.3 on the 15th and 14.6 on the 16th; the logistics cell
straddles the change, mean 30.8, median 15.4). The slow regime is the
partial-CPU load that `docs/knowledge/environment.md` documents: a run
started or resumed during the owner's evening VRAM use loads the model
partly on CPU and runs three to four times slow all night; the idle-close
hook has unloaded the model before the night run since 2026-10-06, and no
recording since has run in that regime. MTH-023's correction names server
state as a driver of null width that provenance does not capture, so
point 0 and point 1 differ in serving regime as well as in `k`. Either
the k-dial reading carries that caveat, or an optional point 0'
re-anchors k=6 in the current regime (720 calls) before point 1 is read
against point 0. **Point 0' cannot be recorded with the runner as it
stands:** it is the same (domain, format, k, n, q, fault, seed policy,
instruments, corpus) tuple as point 0, so it hashes to `04b75acf8f69d4ec`,
finds point 0's complete checkpoint and records nothing. It needs a
hashed anchor label (§6 item 2); hashing the sampling parameters does not
separate it, since paper one's values stay out of the hash.

### `b`, baseline runs: decoy pairs per target

The estimator assumes one decoy per target. With `b` baseline clouds the
star pairs `s(A, A'), s(A, A''), ...` number `b - 1`, and each is
exchangeable with the target under the null because `B` and every other
baseline cloud are interchangeable given `A`; the pair `s(A', A'')`, which
shares no cloud with the target, is not (the cross-system proposal §0 and
§1, measured by its instrument on all-null inputs at k=20: the target is
the strict maximum among `(T, s(A,A'), s(A,A''))` on 25.3 percent of
inputs against 25.1 and 25.0 for the two star pairs, equal shares as
exchangeability requires; with `s(A', A'')` added the four shares are
21.4, 15.3, 15.3 and 17.8 percent). So
the estimate generalises to `(1 + d/r) / t` over the star pairs with
`r = b - 1`, and `s(A', A'')` is reported beside it. This is the
generalisation the cross-system proposal freezes (§4 and §8 item 3 there),
**designed and frozen there once, before any point here uses it**, per the
k=6 lesson (HANDOFF §21); it also needs `select_stratified` to take a
decoy-to-input mapping, and `detect`, `diagnose_channels.py`,
`fdr.best_achievable` and `agent_decision_variation.py` made roster-aware
under a dated MTH-025 amendment, as §6 item 2 lists.

Expectation: `b` does not move the agent cells. The committed instrument
(`scripts/simulate_null_designs.py`, block 2) runs this configuration,
three baseline clouds with the two star pairs selecting at `r = 2`: at
k=20 and severity 0.9 it reports in 0.362 of cells against the single
decoy's 0.490, with power 0.219 against 0.300 and realised rate 0.010
against 0.019 (four modes, half changed, 400 cells; 0.370 against 0.500
with three modes), and at k=6 it reports in no cell where the single
decoy reports in 1.8 percent; pooling all three pairs at `r = 3` reports
less often still (0.295 and 0.287). More
decoy pairs cut the variance of the decoy count without moving its mean,
and at the floor that removes the draws the selection profits from. In
banking and logistics four targets stand above the cut and none of the 40
decoys; against 80 star scores the estimate at that cut is `(1 + d/2)/4`:
0.25 if no added decoy reaches the top value, 0.375 or 0.5 if one or two
do (the k=6 rate at the top value is 0 of 40 in banking, 1 of 40 in
hospitality, where the best cut's 5 above 1 becomes `(1 + 1/2)/5 = 0.3` at
`r = 2`, so hospitality's figure does depend on `r`). Under §5's rule the
point is expected to read as no change against point 1. **This dial is a
cheap falsification of "more decoys would fix it"**, run at one point
(`b = 3`, k=20, banking: arms A, A', A'', B, so `r = 2`). *Refuted if*
point 2 improves on point 1 by the §5 rule.

### `temperature`, the entropy dial, with two prerequisites and a guard

Every cell so far ran at temperature 0.2 with the seed unset (MTH-023
correction: mirror the deployment, record the regime). Lower temperature
narrows the system's own variation and so the decoys; it also changes the
system under test, so a result at another temperature describes a
different deployment policy, not a sharper measurement of this one. It is
in the grid because a reviewer will ask whether the agent format's
silence is a property of the format or of a sampling policy, and only a
titration answers it.

**Prerequisite one, an engine and study change with a dated entry:**
`scripts/run_study.py` hard-codes temperature 0.2 in its chat factory, has
no flag for it, and does not include it in the parameters that feed the
configuration hash; the same holds for top_p, top_k, num_predict, num_ctx
and the thinking switch (which the harness fixes at off and sends on
every call, but does not hash). The seed policy is already hashed as a
declared string and lacks only the flag. Recorded as it stands, a point at
another temperature would hash to point 1's configuration, share its
checkpoint file name and resume it. These must become hashed study
parameters with flags before points 3 or 4 can be recorded, **without
orphaning the thirteen committed checkpoints**: `compute_config_hash`
digests the whole parameter dict, so a parameter enters the hash only
when it differs from the value paper one recorded under, and a test
asserts the nine k=6 and four k=20 hashes unchanged.

**Prerequisite two, eight calls:** whether temperature-0 decoding varies
on this server is unmeasured. MTH-015's mechanism is batched serving, and
this server does not batch (BCH-008); the mechanism on record for it is
the cache-state instability of MTH-023's correction, under which a pinned
regime collapses eight runs onto two outputs rather than one. Before
point 3 is recorded, the MTH-023 correction's protocol runs at
temperature 0 on one banking-agent input: eight repeats, reported as
distinct outputs in eight.

Expectation at temperature 0: point 3's mode-share decoy 90th percentile
falls below point 1's and its separating count rises above point 1's,
while its best estimate does not move the reading against point 1 under
§5, because the fault's effect narrows with the variation it rides on.
*Refuted if* the decoys do not narrow, if the separating count does not
rise, or if the best estimate moves the reading. At 0.5 the separating
count is at or below point 1's and the best estimate does not move the
reading; *refuted if* either does. Both are read under §5, by best
estimate and separating count, never by flag count. **Guard:** if point
3's decoys on the selecting channel sit at exactly 0 on more than
[threshold, fixed in the ratifying append; point 1's own count is the
anchor, and the k=6 counts are 2, 2 and 1 of 40 on mode share] inputs, or
take fewer than [count] distinct values, the point is classified as
MTH-023's near-zero self-variance regime, reported by exact diff with its
decoy-zero count and its distinct-value count, and is not read against
point 1 by the step rule: a collapsed null makes every touched difference
clear every cut and would masquerade as a sharper measurement.

### Channel: decision token against rationale text

`scripts/agent_decision_variation.py` reads the decision token (APPROVE,
DECLINE, ESCALATE, or none) with no model and scores it with the same
distance the share-of-answers check uses; the three committed
`.decisions.json` files are the k=6 points. The rationale text is what the
judge-based channels read. The split costs no recording: every grid point
yields both readings from the same checkpoint (point 2 after the script is
roster-aware, §6 item 2).

Expectation, for banking, the grid's cell: the decision channel stays
inside the system's own variation at every `k` on this fault. At k=6 its
best estimates are 0.667, 0.50 and 0.60 against q = 0.10, with decoy
medians equal to the fired-target medians in banking and logistics. The
fault moves decisions less than the system moves its own only in banking
(majority flips on 3 of 26 touched inputs against 7 of 40 between the two
baseline runs); in logistics and hospitality it moves them more (11 of 25
and 9 of 26 against 7 and 8 of 40), so the expectation is filed for the
cell the grid runs in. *Refuted if* the decision channel separates ten or
more touched inputs from every decoy at any point; the agent limitation
is then a text-channel limitation and the paper says so. The tension to
state in paper two: a decision-token channel knows what the output is,
which the domain-agnostic detector does not; it is a user-registered
projection, not a shipped channel.

### Held fixed, recorded per point, and what the runner still lacks

Held fixed: the step cap, the prompt and the tools (section 6 of paper one
said the format was kept as it is, and changing it would titrate the bench
rather than the detector); the fault, stale knowledge base, as in every
cell; the corpus, the 40 banking-agent inputs; the thinking switch, off
and sent explicitly on every call (fixed by the harness, hashed with the
other sampling parameters under prerequisite one). The model digest is to
be guarded as the drift control guards it, refusing to record when the
digest differs from point 0's recorded `system_digest`; `run_study.py` has
no such guard today (a changed digest silently starts a new checkpoint),
so it is a prerequisite (§6 item 2). Recorded per point and compared
across points, because the harness does not fix them: the server version
(from `/api/version`, a provenance field to add in the same entry) and the
serving regime (the per-call time is its proxy; the 6 and 15 October
figures above are two regimes).

## 3. The grid, in the order worth running

Banking-agent throughout: the second most varied cell (785 of 944
clustered samples distinct at k=6; hospitality is the most varied at 824
of 958), the longest to record (12.8 hours of call time against 6.1 and
3.1) and the one recorded wholly in the 6 October regime.

| point | k | b | r | arms | temperature | status | what it decides |
|---|---|---|---|---|---|---|---|
| 0 | 6 | 2 | 1 | 3 | 0.2 | recorded 6 October (`04b75acf8f69d4ec`) | the baseline reading, old serving regime |
| 0' | 6 | 2 | 1 | 3 | 0.2 | optional; needs a hashed anchor label (§6 item 2) | removes the regime confound from the k reading |
| 1 | 20 | 2 | 1 | 3 | 0.2 | owner-directed 2026-10-17; scheduled, owner's machine | does `k` alone reach the budget |
| 2 | 20 | 3 | 2 | 4 (A, A', A'', B) | 0.2 | needs the roster change, the estimator and the roster-aware readers | falsifies "more decoys" |
| 3 | 20 | 2 | 1 | 3 | 0.0 | needs the sampling parameters hashed and the eight-repeat check; after point 1 | is the silence a sampling policy, or does temperature 0 collapse the null |
| 4 | 20 | 2 | 1 | 3 | 0.5 | after point 3, only if point 3 improved on point 1 by §5 | the other end of the dial |
| 5 | 40 | 2 | 1 | 3 | 0.2 | only if point 1 improved on point 0 (or 0') by §5 | does `k` saturate |

Decision channel at every point from the checkpoint, no recording. Points
3 and 4 are different deployments by MTH-023's reading and are reported as
such. Points 4 and 5 are conditional on results, and points 2 and 3 wait
on prerequisites, so the committed grid is three points (1, 2, 3) plus two
gates and one optional anchor.

## 4. Cost

The brief's figure, 16.9 seconds per agent invocation, is the pooled
estimate from the nine-cell smoke run of 2026-09-29
(`results/cells_smoke.json`: three agent cells of four inputs, 202 seconds
and 63 model calls, so 16.9 seconds per input run through the agent and
3.2 per model call), the constant `run_study.py` uses for its time
estimates. The banking-agent row of the same run is 83.5 seconds over four
inputs, 20.9 per invocation. The per-day means since 15 October (13 to 17
seconds) are logistics and hospitality only, and both run within about ten
percent of their own smoke rows (12.3 against 12.8; 17.4 against 15.5);
banking-agent has not been recorded in the current regime, so the
banking-only grid is planned on 20.9 seconds until point 1 lands. The 6
October regime is the documented partial-CPU load (§2); its column is the
cost if the idle-close guard fails on a grid night, and point 1's per-call
time shows which regime it ran in.

Calls per point are `n × k × arms` with `n = 40`; hours are calls times
seconds per call, with no allowance for pauses or the serving process
stopping (environment.md).

| point | calls | hours at 16.9 s (pooled smoke) | hours at 20.9 s (banking smoke row) | hours at 65.0 s (6 October regime) |
|---|---|---|---|---|
| 0' (k=6, 3 arms) | 720 | 3.4 | 4.2 | 13.0 |
| 1 (k=20, 3 arms) | 2,400 | 11.3 | 13.9 | 43.3 |
| 2 (k=20, 4 arms) | 3,200 | 15.0 | 18.6 | 57.8 |
| 3 (k=20, 3 arms, t=0) | 2,400 | 11.3 | 13.9 | 43.3 |
| 4 (k=20, 3 arms, t=0.5) | 2,400 | 11.3 | 13.9 | 43.3 |
| 5 (k=40, 3 arms) | 4,800 | 22.5 | 27.9 | 86.7 |
| committed (1 + 2 + 3) | 8,000 | 37.6 | 46.4 | 144 |
| full grid (0' and 1 to 5) | 15,920 | 74.7 | 92.4 | 287 |

At 20.9 seconds the committed grid is about 46 hours, five nights; at the
6 October regime it is two to three weeks of nights, which would not fit
the trial and would need the owner to decide between the grid and the
k=20 JSON cells paper one lists as unmeasured. Point 1's checkpoint will
carry its own per-call time and settle the column.

Analysis cost is small beside recording: 79 to 93 seconds per agent cell
with the judge loaded at k=6 (Appendix F of paper one, third pass),
proportionally more at k=20; the diagnosis and decision instruments add a
minute each.

## 5. Sizing and reading rules, so the result cannot be read after the fact

- Sizing follows MTH-024's corrected rule, `n ≥ (1/q) / (a·s)`, with `a`
  the touched fraction (26 of 40 in banking) and `s` the fraction of
  touched inputs that separate; at k=6 `s` was 4 of 26, so `a·s` is 0.10
  and the rule puts `n` at 100 for q=0.10, two and a half times the corpus.
  **The grid therefore tests whether the dials raise `s`, not whether the
  cell can report at n=40**; a point is read by its best estimate and its
  separating count, under MTH-025, never by its flag count alone.
- Each three-arm point's classification is taken from
  `diagnose_channels.py` on the GPU machine under MTH-025 as frozen; point
  2's under the dated MTH-025 amendment that re-binds the criterion to the
  roster-aware instrument (§6 item 2). The decision channel's reading comes
  from `agent_decision_variation.py`; both files are committed beside the
  checkpoint.
- A point **moves the reading** against its reference point if exactly
  one of the two reaches the budget (best estimate at or under q), or if
  their best estimates differ by more than the finer of the two points'
  `1/t` at their best cuts (the smaller of the two values). A move is an
  improvement when the estimate falls; points 4 and 5 run only on an
  improvement. Against point 0's four targets over no decoy this registers
  an improvement at nine or more separating inputs with no decoy above, or
  at any estimate at or under q; four to eight reads as no change. The
  step is read at the cut `best_achievable` returns, so its tie direction
  (cross-system proposal §8 item 7) is fixed before point 1's file is
  read. Reference points: point 1 against point 0 (or 0' if recorded);
  points 2, 3 and 4 against point 1; point 5 against point 1. The
  separating count is reported beside the verdict either way.
- A point whose decoys fall under the §2 temperature guard is classified
  as a near-zero self-variance regime and is not read by the step rule.
- The write-up reports, per point, the best estimate, the separating
  count, the decoy range and 90th percentile, the decoys-at-zero count and
  the number of distinct decoy values, and the per-call time, in one
  table, with the expectation beside each and whether it held.

## 6. What this proposal asks the owner to ratify

1. The grid in §3, with points 4 and 5 conditional on results, points 2
   and 3 on their prerequisites, and 0' optional as stated.
2. The prerequisites, each a dated engine and study entry: (a) before
   point 2, the generalised estimator over the star pairs and the roster
   change, frozen in the cross-system proposal, with `adapter.check_arm`,
   `detect`, `diagnose_channels.py`, `fdr.best_achievable` and
   `agent_decision_variation.py` made roster-aware, a dated MTH-025 append
   re-binding the criterion to that instrument, and the three committed
   agent diagnosis and decisions files regenerated byte-identical at
   `r = 1`; (b) before points 3 or 4, temperature and the other sampling
   parameters hashed with flags without orphaning the committed
   checkpoints, and the eight-repeat check at temperature 0; (c) before
   0', a hashed anchor label; (d) before any point after 1, the digest
   guard and the server-version provenance field in `run_study.py`.
3. The reading rules in §5, with `best_achievable`'s tie direction and
   the temperature guard's thresholds, frozen before point 1's file is
   read.
4. Whether to record point 0', or to carry the serving-regime caveat on
   the k reading.
5. Which cost column the budget is planned on, once point 1's file lands.

**Evidence:** STD-011 and its four appends; MTH-015, MTH-018, MTH-023 and
correction, MTH-024 and correction, MTH-025 and amendment; BCH-008; the
agent checkpoints (call times and dates); `scripts/run_study.py` (the chat
factory, the hashed parameters, `SECONDS_PER_INVOCATION`, no digest
guard); `src/aprime/cells/chat.py` (the thinking switch);
`results/cells_smoke.json`; `scripts/agent_decision_variation.py`;
`scripts/simulate_null_designs.py` block 2; `docs/knowledge/environment.md`.
**Reopen if:** point 1 refutes the `k` expectation (decoy maximum at or
above 0.833, or a best cut admitting no more than four targets) or the
decision-channel expectation (ten or more touched inputs separating on the
decision token); point 1 reaches the budget at k=20 alone, which
re-premises points 2 to 5; or the serving regime changes the per-call time
by more than a factor of two, which re-costs the grid.
