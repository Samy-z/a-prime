# Agent self-variance, titrated — PROPOSAL, dated 2026-10-20, awaiting owner ratification

**Status: PROPOSAL. Not a decision. No grid point below may be recorded
until the owner ratifies the grid and the generalised estimator it needs,
by a dated append here, and the sizing of each point is in a dated entry
(CLAUDE.md: no study-shaping parameter outside a dated entry).** Written to
the methods STATE queue opened 2026-10-17 at the owner's direction:
investigate the agent limitation with clear numbers before a reviewer does.

## 1. What is being titrated

The agent row at k=6 was silent in three of three domains and classified
resolution-limited under MTH-025 (STD-011 second and fourth appends): the
decoys, the second baseline run scored against the first, span 0 to 0.83
in banking and logistics and 0 to 1.0 in hospitality, covering the fired
targets' range except at most the top value; four touched inputs separate
in banking and logistics, none in hospitality, and the floor needs ten.
The decision-level reading (STD-011 first append) says why: at the level
of the decision token the fault moves the agent about as much as the
agent moves itself between two identical runs (median total-variation
0.17 against 0.17), and the rationale text is distinct on 71 to 86 percent
of samples.

So the quantity under titration is **the certifiable difference per agent
output**, and the dials are the things that could change it without
changing what the detector is: how finely the statistic can resolve (`k`),
how many decoys the estimate stands on (`m`), how much of the variation is
sampling entropy (`temperature`), and which part of the output the
channel reads (decision token against rationale text). Each dial comes
with an expectation filed here, before any point runs, so that a result
can disagree with it.

## 2. The dials

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
not the fineness of the grid. **If banking-agent at k=20 still cannot reach
the budget, the reading is a statement about information per agent output
on this fault, not about `k`**, and the k=40 point is run only if the k=20
best estimate moved by more than one grid step toward the budget.

### `m`, baseline runs per system: decoys per target

The estimator assumes one decoy per target. With `m` baseline runs the
within pairs number `m(m+1)/2`, all exchangeable with the target under the
null, and the estimate generalises to `(1 + d/r) / t` with `r` the number
of decoy pairs per target. This is the same generalisation the
cross-system null needs (`docs/methods/cross-system-null-proposal.md`, §3)
and it is **designed and frozen there once, before any point here uses
it**, per the k=6 lesson (HANDOFF §21).

Expectation: `m` does not move the agent cells. More decoys cut the
estimate's step size, and the step was not the agent row's problem: with
four targets above zero decoys the estimate is `1/4 = 0.25` whatever `r`
is, and with decoys covering the target range more decoys cover it more.
**This dial is included as a cheap falsification of "more decoys would fix
it"**, run at one point only (`m = 3`, k=20, banking), and expected to
leave the best estimate within one step of the `m = 1` point.

### `temperature`, the entropy dial, with a caveat that is part of the finding

Every cell so far ran at temperature 0.2 with the seed unset (MTH-023
correction: mirror the deployment, record the regime). Lower temperature
narrows the system's own variation and so the decoys; it also changes the
system under test, so a result at another temperature describes a
different deployment policy, not a sharper measurement of this one. That
is why the dial is in the grid rather than out of it: the question a
reviewer will ask is whether the agent format's silence is a property of
the format or of a sampling policy, and only a titration answers it.

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
output is, which the domain-agnostic detector does not; it is a user-
registered projection, not a shipped channel.

### Held fixed

The step cap, the prompt and the tools: section 6 of paper one said the
format was kept as it is, and changing it would titrate the bench rather
than the detector. The fault: stale knowledge base, as in every cell. The
corpus: the 40 banking-agent inputs, so that every point shares one
activation pattern as far as the agent's own tool choices allow (the fault
fires only on runs that make the stale read; STD-011).

## 3. The grid, in the order worth running

Banking-agent throughout: the most varied cell (785 of 944 distinct at
k=6) and the slowest, so a point that works there works anywhere.

| point | k | m | arms | temperature | status | what it decides |
|---|---|---|---|---|---|---|
| 0 | 6 | 1 | 3 | 0.2 | recorded (`04b75acf8f69d4ec`) | the baseline reading |
| 1 | 20 | 1 | 3 | 0.2 | scheduled, owner's machine | does `k` alone reach the budget |
| 2 | 20 | 3 | 4 (A, A', A'', B) | 0.2 | needs the roster change | falsifies "more decoys" |
| 3 | 20 | 1 | 3 | 0.0 | after point 1 | is the silence a sampling policy |
| 4 | 20 | 1 | 3 | 0.5 | after point 3, only if 3 moved | the other end of the dial |
| 5 | 40 | 1 | 3 | 0.2 | only if point 1 moved by more than one step | does `k` saturate |

Decision channel at every point from the checkpoint, no recording. Points
3 and 4 are different deployments by MTH-023's reading and are reported as
such. Points 2 and 5 are conditional, so the committed grid is three
points plus two gates.

## 4. Cost

The brief's figure is 16.9 seconds per agent invocation, measured on the
owner's machine during the k=20 banking-agent recording. The k=6 agent
checkpoints measured higher: mean call time 65.0 s in banking, 30.8 s in
logistics and 15.5 s in hospitality (median 62.7, 15.4 and 16.1; the sums
are 12.8, 6.1 and 3.1 hours per cell). The table carries both the brief's
figure and the banking k=6 mean, because the difference is a factor of
four on the cell this grid runs on, and the k=20 banking file will say
which is right for the current serving setup.

Calls per point are `n × k × arms` with `n = 40`; hours are calls times
seconds per call, with no allowance for pauses or the serving process
stopping (environment.md).

| point | calls | hours at 16.9 s | hours at 65.0 s |
|---|---|---|---|
| 1 (k=20, 3 arms) | 2,400 | 11.3 | 43.3 |
| 2 (k=20, 4 arms) | 3,200 | 15.0 | 57.8 |
| 3 (k=20, 3 arms, t=0) | 2,400 | 11.3 | 43.3 |
| 4 (k=20, 3 arms, t=0.5) | 2,400 | 11.3 | 43.3 |
| 5 (k=40, 3 arms) | 4,800 | 22.5 | 86.7 |
| committed (1 + 2 + 3) | 8,000 | 37.6 | 144 |
| full grid (1 to 5) | 15,200 | 71.4 | 274 |

At the brief's figure the committed grid is four nights; at the k=6 mean
it is two to three weeks of nights, which would not fit the trial and
would need the owner to decide between the grid and the k=20 JSON cells
paper one lists as unmeasured. **The first thing point 1's file settles is
which column this table lives in.**

Analysis cost is small beside recording: 79 to 93 seconds per agent cell
with the judge loaded at k=6 (Appendix F of paper one, third pass),
proportionally more at k=20; the diagnosis and decision instruments add a
minute each.

## 5. Sizing and reading rules, so the result cannot be read after the fact

- Sizing follows MTH-024's corrected rule, `n ≥ (1/q) / (a·s)`, with `a`
  the touched fraction (26 of 40 in banking) and `s` the fraction of
  touched inputs that separate; at k=6 `s` was 4 of 26, so `a·s` is 0.10
  and the rule puts `n` at 100 for q=0.10, two and a half times the corpus. **The grid therefore tests whether the
  dials raise `s`, not whether the cell can report at n=40**; a point is
  read by its best estimate and its separating count, under MTH-025,
  never by its flag count alone.
- Each point's classification is taken from `diagnose_channels.py` on the
  GPU machine under MTH-025 as frozen, and the decision channel's reading
  from `agent_decision_variation.py`; both files are committed beside the
  checkpoint.
- A point moves the reading if its best estimate changes by more than one
  grid step (`1/t` at the point's target count) from point 1's; anything
  smaller is within the estimator's resolution and is reported as no
  change.
- The write-up reports the best estimate, the separating count and the
  decoy range per point, in one table, with the expectation beside each
  and whether it held.

## 6. What this proposal asks the owner to ratify

1. The grid in §3, with points 2 and 5 conditional as stated.
2. The generalised estimator, frozen in the cross-system proposal before
   point 2 is recorded.
3. The reading rules in §5, frozen before point 1's file is read.
4. Which cost column the budget is planned on, once point 1's file lands.

**Evidence:** STD-011 and its four appends; MTH-015, MTH-018, MTH-023 and
correction, MTH-024 and correction, MTH-025; the three agent checkpoints
(call times); `scripts/agent_decision_variation.py`;
`docs/study/cloud-trial-tasks.md` (the 16.9 s figure).
**Reopen if:** point 1 lands outside both expectations filed for it; or
the serving setup changes the per-call time by more than a factor of two,
which re-costs the grid.
