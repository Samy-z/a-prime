# Agent self-variance, titrated — PROPOSAL, dated 2026-10-20, awaiting owner ratification

**Status: PROPOSAL, revised the same day after an adversarial verification
pass. Not a decision. No grid point below may be recorded until the owner
ratifies the grid, the prerequisites in §2 and the generalised estimator
it needs, by a dated append here, and the sizing of each point is in a
dated entry (CLAUDE.md: no study-shaping parameter outside a dated
entry).** Written to the methods STATE queue opened 2026-10-17 at the
owner's direction: investigate the agent limitation with clear numbers
before a reviewer does.

Terms (`b`, within pairs, `r`) are fixed in
`docs/methods/cross-system-null-proposal.md` §0 and used here unchanged:
`b` baseline clouds per system with the first run counted, `C(b, 2)` within
pairs, `r` decoy pairs per target.

## 1. What is being titrated

The agent row at k=6 was silent in three of three domains and classified
resolution-limited under MTH-025 (STD-011 second and fourth appends): the
decoys, the second baseline run scored against the first, span 0 to 0.83
in banking and logistics and 0 to 1.0 in hospitality, covering the fired
targets' range except at most the top value; four touched inputs separate
in banking and logistics, none in hospitality, and the floor needs ten.
The decision-level reading (STD-011 first append) says why: at the level
of the decision token the fault moves the agent about as much as the agent
moves itself between two identical runs (median total-variation on touched
inputs 0.17 against a decoy median of 0.17 in banking and logistics, 0.25
against 0.17 in hospitality), and the rationale text is distinct on 71 to
86 percent of samples.

So the quantity under titration is **the certifiable difference per agent
output**, and the dials are the things that could change it without
changing what the detector is: how finely the statistic can resolve (`k`),
how many decoys the estimate stands on (`b`, through `r`), how much of the
variation is sampling entropy (`temperature`), and which part of the output
the channel reads (decision token against rationale text). Each dial comes
with an expectation filed here, before any point runs, so that a result
can disagree with it.

## 2. The dials, and what each needs before it can run

### `k`, samples per cloud: grid fineness and mass per mode

The share-of-answers statistic takes `k + 1` values; at k=6 that is seven
and the decoys crowd them. k=20 took the summary row from a false-alarm
bracket straddling the budget to 0.056 under it, and banking extraction
from nothing flagged to 21 of 21 (STD-013). **First data point: the
banking-agent cell at k=20**, recorded on the owner's machine on the next
quiet night; its report file is the anchor the rest of this grid is built
around.

Expectation, carried from STD-011 second append and filed again here: the
grid refines from 7 to 21 values, which should pull the decoys at 0.83 off
the top and raise the best estimate's resolution; whether ten or more
touched inputs then stand clear of every decoy is the open question,
because what binds in the agent cells is the number of separating inputs,
not the fineness of the grid. **If banking-agent at k=20 still cannot
reach the budget, the reading is a statement about information per agent
output on this fault, not about `k`**, and the k=40 point runs only on the
gate in §5.

A confound to declare: the k=6 banking point was recorded on 6 October at
a mean of 65 seconds per call (median 63; the 209 logistics-agent calls
made the same day ran at a mean of 75), and every agent call since 15
October has run at a per-day mean of 13 to 17 seconds (the checkpoints'
`latency_ms`: logistics 12.8 on the 15th, hospitality 17.3 on the 15th and
14.6 on the 16th; the logistics cell straddles the change, mean 30.8,
median 15.4). MTH-023's correction names server
state as a driver of null width that provenance does not capture, so
point 0 and point 1 differ in serving regime as well as in `k`. Either the
k-dial reading carries that caveat, or an optional point 0' re-anchors
k=6 in the current regime (720 calls, about 3.4 hours at the current
rate) before point 1 is read against point 0.

### `b`, baseline runs: decoys per target

The estimator assumes one decoy per target. With `b` baseline clouds the
within pairs number `C(b, 2)`, each with the target's marginal distribution
under the null, and the estimate generalises to `(1 + d/r) / t` with
`r = C(b, 2)`. This is the generalisation the cross-system proposal freezes
(§4 there), **designed and frozen there once, before any point here uses
it**, per the k=6 lesson (HANDOFF §21); it also needs `select_stratified`
to take a decoy-to-input mapping, as that proposal says.

Expectation: `b` does not move the agent cells, and the committed
simulation says why (`scripts/simulate_null_designs.py`): more decoys cut
the variance of the decoy count without moving its mean, and at the floor
that removes the draws the selection profits from; in the agent cells,
with four targets above zero decoys, the estimate is `1/4 = 0.25` whatever
`r` is, and with decoys covering the target range more decoys cover it
more. **This dial is a cheap falsification of "more decoys would fix it"**,
run at one point (`b = 3`, k=20, banking: arms A, A', A'', B, so `r = 3`),
and expected to leave the best estimate within one step of the `b = 2`
point.

### `temperature`, the entropy dial, with a prerequisite and a caveat

Every cell so far ran at temperature 0.2 with the seed unset (MTH-023
correction: mirror the deployment, record the regime). Lower temperature
narrows the system's own variation and so the decoys; it also changes the
system under test, so a result at another temperature describes a
different deployment policy, not a sharper measurement of this one. It is
in the grid because a reviewer will ask whether the agent format's
silence is a property of the format or of a sampling policy, and only a
titration answers it.

**Prerequisite, an engine and study change with a dated entry:**
`scripts/run_study.py` hard-codes temperature 0.2 in its chat factory, has
no flag for it, and does not include it in the parameters that feed the
configuration hash. Recorded as it stands, a point at another temperature
would hash to point 1's configuration, share its checkpoint file name and
resume it. Temperature (and the other sampling parameters: top_p, top_k,
num_predict, num_ctx, think, seed policy) must become hashed study
parameters with a flag before points 3 or 4 can be recorded.

Expectation: at temperature 0 the decoys narrow and more touched inputs
separate, but temperature-0 decoding is not deterministic on batched
serving (MTH-015) and the fault's effect narrows with the variation it
rides on, so the best estimate improves by less than the decoy width
shrinks. At 0.5 the row stays silent. Filed as directions, not numbers:
nothing measured so far says how the two effects trade.

### Channel: decision token against rationale text

`scripts/agent_decision_variation.py` reads the decision token (APPROVE,
DECLINE, ESCALATE, or none) with no model and scores it with the same
distance the share-of-answers check uses; the three committed
`.decisions.json` files are the k=6 points. The rationale text is what the
judge-based channels read. The split costs no recording: every grid point
yields both readings from the same checkpoint.

Expectation: the decision channel stays inside the system's own variation
at every `k` on this fault (the fault barely moves decisions: majority
flips on 3 of 26, 11 of 25 and 9 of 26 touched inputs against 7, 7 and 8
of 40 between the two baseline runs). If it ever separates ten inputs, the
agent limitation is a text-channel limitation and the paper says so. The
tension to state in paper two: a decision-token channel knows what the
output is, which the domain-agnostic detector does not; it is a
user-registered projection, not a shipped channel.

### Held fixed, and recorded per point

The step cap, the prompt and the tools: section 6 of paper one said the
format was kept as it is, and changing it would titrate the bench rather
than the detector. The fault: stale knowledge base, as in every cell. The
corpus: the 40 banking-agent inputs. The model digest, guarded as the
drift control guards it. And three things that are not fixed by the
harness and must be recorded per point and compared across points: the
server version, the serving and batch regime (the per-call time is its
proxy; the 6 and 15 October figures above are two regimes), and the
model's thinking setting.

## 3. The grid, in the order worth running

Banking-agent throughout: the slowest cell and the second most varied (785
of 944 samples distinct at k=6; hospitality is the most varied at 824 of
958), so a point that works there works in two of the three.

| point | k | b | arms | temperature | status | what it decides |
|---|---|---|---|---|---|---|
| 0 | 6 | 2 | 3 | 0.2 | recorded 6 October (`04b75acf8f69d4ec`) | the baseline reading, old serving regime |
| 0' | 6 | 2 | 3 | 0.2 | optional, current regime | removes the regime confound from the k reading |
| 1 | 20 | 2 | 3 | 0.2 | scheduled, owner's machine | does `k` alone reach the budget |
| 2 | 20 | 3 | 4 (A, A', A'', B) | 0.2 | needs the roster change and the estimator | falsifies "more decoys" |
| 3 | 20 | 2 | 3 | 0.0 | needs temperature hashed; after point 1 | is the silence a sampling policy |
| 4 | 20 | 2 | 3 | 0.5 | after point 3, only if 3 moved | the other end of the dial |
| 5 | 40 | 2 | 3 | 0.2 | only if point 1 moved against point 0 by the §5 rule | does `k` saturate |

Decision channel at every point from the checkpoint, no recording. Points
3 and 4 are different deployments by MTH-023's reading and are reported as
such. Points 2 and 5 are conditional, so the committed grid is three
points (1, 2, 3) plus two gates and one optional anchor.

## 4. Cost

The brief's figure, 16.9 seconds per agent invocation, is the pooled
estimate from the nine-cell smoke run of 2026-09-29
(`results/cells_smoke.json`: three agent cells of four inputs, 202 seconds
and 63 model calls, so 16.9 seconds per input run through the agent and
3.2 per model call), the constant `run_study.py` uses for its time
estimates. The agent recordings since 15 October ran at per-day means of
13 to 17 seconds per call, so it is the right planning figure for the
current serving regime. The 6 October recordings ran at means of 65 and
75 seconds per call, and the budget column that regime implies is
carried as the risk case, because nothing in provenance says which regime
the machine will be in on a given night.

Calls per point are `n × k × arms` with `n = 40`; hours are calls times
seconds per call, with no allowance for pauses or the serving process
stopping (environment.md).

| point | calls | hours at 16.9 s (current regime) | hours at 65.0 s (6 October regime) |
|---|---|---|---|
| 0' (k=6, 3 arms) | 720 | 3.4 | 13.0 |
| 1 (k=20, 3 arms) | 2,400 | 11.3 | 43.3 |
| 2 (k=20, 4 arms) | 3,200 | 15.0 | 57.8 |
| 3 (k=20, 3 arms, t=0) | 2,400 | 11.3 | 43.3 |
| 4 (k=20, 3 arms, t=0.5) | 2,400 | 11.3 | 43.3 |
| 5 (k=40, 3 arms) | 4,800 | 22.5 | 86.7 |
| committed (1 + 2 + 3) | 8,000 | 37.6 | 144 |
| full grid (0' and 1 to 5) | 15,920 | 74.7 | 287 |

At the current regime the committed grid is four nights; at the 6 October
regime it is two to three weeks of nights, which would not fit the trial
and would need the owner to decide between the grid and the k=20 JSON
cells paper one lists as unmeasured. Point 1's checkpoint will carry its
own per-call time and settle the column.

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
- Each point's classification is taken from `diagnose_channels.py` on the
  GPU machine under MTH-025 as frozen, and the decision channel's reading
  from `agent_decision_variation.py`; both files are committed beside the
  checkpoint.
- A point **moves the reading** against its reference point if its best
  estimate differs by more than one grid step, where the step is the
  coarser of the two points' `1/t` at their best cuts (the larger of the
  two values). Reference points: point 1 against point 0 (or 0' if
  recorded); points 2, 3 and 4 against point 1; point 5 against point 1.
  Anything smaller is within the estimator's resolution and is reported as
  no change.
- The write-up reports the best estimate, the separating count, the decoy
  range and the per-call time per point, in one table, with the
  expectation beside each and whether it held.

## 6. What this proposal asks the owner to ratify

1. The grid in §3, with points 2 and 5 conditional and 0' optional as
   stated.
2. The two prerequisites: the generalised estimator and roster change,
   frozen in the cross-system proposal before point 2; temperature and the
   other sampling parameters as hashed study parameters with a flag, in a
   dated engine and study entry, before points 3 or 4.
3. The reading rules in §5, frozen before point 1's file is read.
4. Whether to record point 0', or to carry the serving-regime caveat on
   the k reading.
5. Which cost column the budget is planned on, once point 1's file lands.

**Evidence:** STD-011 and its four appends; MTH-015, MTH-018, MTH-023 and
correction, MTH-024 and correction, MTH-025; the agent checkpoints (call
times and dates); `scripts/run_study.py` (the chat factory, the hashed
parameters, `SECONDS_PER_INVOCATION`); `results/cells_smoke.json`;
`scripts/agent_decision_variation.py`; `scripts/simulate_null_designs.py`.
**Reopen if:** point 1 lands outside both expectations filed for it; or
the serving regime changes the per-call time by more than a factor of
two, which re-costs the grid.
