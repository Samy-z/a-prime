# study — LEDGER

Append-only settled findings about the landscape, the claim surface, and study
execution. Prefix `STD-###`. Never edit an entry in place; correct it with a
dated append below. **Grep this file before investigating anything.**

Entry format: id, date, finding, consequence, evidence, reopen-if.

---

## STD-001 — The noise-floor idea is partially occupied; do not lead with it
**Date:** 2026-09-24
**Finding:** The statistics are already canonical. UK AISI's Inspect ships
repeated decodes with clustered and paired standard errors, and an Anthropic
paper covers error bars for evals. At least four OSS or preprint projects ship
"delta vs noise" CI gates. The commercial tier has not adopted it.
**Consequence:** Not a headline contribution. The unoccupied construction is
the A-prime decoy arm run alongside A-vs-B with target-decoy FDR — target-decoy
appears to have no prior LLM-eval application.
**Evidence:** Landscape survey, 2026-09-24.
**Reopen if:** a tool ships decoy-calibrated drift detection.

## STD-002 — Metamorphic relations are already solved academically
**Date:** 2026-09-24
**Finding:** CheckList (2020) defined invariance and directional testing as a
task-agnostic methodology. A 2025 survey catalogued 191 metamorphic relations
for NLP and ran roughly 560k tests. Giskard ships
`test_metamorphic_invariance` as a named primitive.
**Consequence:** Cite, use, do not claim. Retained as a feature for legibility,
not as a contribution. The one narrow gap is *inducing which relations apply*
from a system's own unlabelled traffic, which is adjacent to STD-003.
**Evidence:** Landscape survey, 2026-09-24.
**Reopen if:** never, as a novelty claim.

## STD-003 — Induced structural conformance is genuinely unoccupied
**Date:** 2026-09-24
**Finding:** Nothing in the tooling space induces conformance rules from a
baseline's own output distribution. Everything adjacent is hand-authored:
JSON-schema assertions, constrained decoding. The nearest ancestor is
Daikon-style dynamic invariant detection from program traces (2001), never
ported to LLM output distributions.
**Consequence:** The most defensible mechanism in the design. It inherits
Daikon's known failure mode — far too many candidate invariants, triage dumped
on the human — which the decoy-arm pruning and the three-tier band answer.
**Evidence:** Landscape survey, 2026-09-24.
**Reopen if:** anyone ships induced output invariants.

## STD-004 — Embedding triage is half-occupied
**Date:** 2026-09-24
**Finding:** Arize Phoenix already clusters embeddings and orders clusters by
drift against a reference set. "Replay, embed, rank by displacement, review the
top N" is not shipped as a regression primitive, but it is an obvious
composition rather than a novel mechanism.
**Consequence:** Defensible as engineering, not as a claim.
**Evidence:** Landscape survey, 2026-09-24.
**Reopen if:** not applicable.

## STD-005 — No existing study of whether regression detection transfers across domains
**Date:** 2026-09-24
**Finding:** The survey found no direct study. This is the open question, and
the survey's own assessment is that it is worth more than any of the four
mechanisms.
**Consequence:** This is the headline contribution. The project is an empirical
study with a tool attached, not a tool with a study attached.
**Evidence:** Landscape survey, 2026-09-24.
**Reopen if:** someone publishes it — in which case the contribution ordering
changes and STD-003 becomes the headline.

## STD-006 — Clausius is the nearest competitor and owns the slogan
**Date:** 2026-09-24
**Finding:** An OSS project doing label-free regression detection on unlabelled
production prompts with a measured null, validated across five model families
and seven task domains, with published sensitivity numbers.
**Limitation that leaves room:** it reads logprobs, so it is local or
self-hosted only and cannot touch a hosted API; its threshold is calibrated on
one stack and its own documentation says the null must be re-measured
elsewhere.
**Consequence:** a-prime is black-box and works against hosted endpoints, where
essentially all real deployments live. Position against this explicitly; do not
write as though the space is empty.
**Evidence:** Landscape survey, 2026-09-24.
**Reopen if:** it gains a black-box mode.

## STD-007 — Base rates can manufacture a fake transfer result
**Date:** 2026-09-24
**Finding:** A 2026 hallucination-detection paper tested cross-domain threshold
transfer and found apparent transfer dominated by class-frequency effects
rather than methodological differences.
**Consequence:** Regression base rates must be controlled across domain cells
by design, before the study runs. Uncontrolled, the transfer finding is
uninterpretable in either direction.
**Evidence:** Landscape survey, 2026-09-24.
**Reopen if:** never.

---

> **Verification note (2026-09-24).** Entries STD-001 through STD-007 come from
> a single landscape survey pass. Vendor documentation for promptfoo,
> Braintrust, LangSmith, Giskard, Phoenix and Inspect was checked directly;
> several other rows rest on changelogs and third-party comparisons. Before any
> hard novelty claim against a specific named tool reaches the paper, verify it
> by running that tool, not by reading it.

## STD-008 — Detecting that a hosted model changed is the same statistic pointed at time
**Date:** 2026-10-04
**Finding:** Owner's question, raised while rejecting the hosted-model arm: we
cannot know when a provider changed the weights under us, "or can we? maybe this
could be an extra tool: version change detection?"

Partly we can, and the machinery is already built.

**Sometimes the provider tells you.** OpenAI returns a `system_fingerprint`
which changes when the backend configuration changes, and exists for exactly
this. It is not universal, and it signals a serving-configuration change rather
than a weight change specifically.

**Otherwise we can measure it, with no new statistics.** The method here is
already "run the same system twice, measure the spread, that spread is the noise
floor". Point it at time instead of at versions:

1. Record arms A and A-prime now. Their spread is the within-period noise floor
   for this corpus.
2. Record the same system again a week later, as a third cloud.
3. Score period one against period two through the same channels, with the
   threshold set by the within-period decoy spread.
4. Anything above that threshold is a change nobody announced.

That is the existing detector with "the candidate system" replaced by "the same
system, later". The decoy arm supplies the calibrated false-alarm rate, which is
the part nobody else offers.

**This is already fault class F6, provider drift**, documented in
`.agents/bench-taxonomy-research.md` section 6. The taxonomy anticipated it. What
is new is shipping it as a capability rather than only injecting it as a fault.

**It reframes the product, which is why it is recorded and not built.** The tool
today is a pre-deployment check: you changed something, here is what moved.
Drift detection is continuous monitoring: nothing was announced, here is what
moved anyway. Same code, different buyer, different claim.

**Novelty: partly occupied, as with STD-001.** Whether a hosted model drifts
over time has published work behind it, including the 2023 study of ChatGPT
behaviour changing across versions. The question is not open. What looks
unclaimed is the calibrated false-alarm rate, which is the same construction
argument STD-001 and STD-006 make for the decoy arm generally.

**Not being built.** The owner has said scope and consistency outrank new
directions, and this is a new direction. Recorded so it is not rediscovered, and
so the paper can offer it as an extension in one honest sentence rather than
claiming it as a result.
**Evidence:** owner exchange 2026-10-04; HANDOFF §15 amendment;
`.agents/bench-taxonomy-research.md` section 6.
**Reopen if:** the transfer result lands and the project wants a second
contribution, or a provider ships a fingerprint reliable enough to replace
step 2.

## STD-008 — APPEND (2026-10-04): is claiming drift detection cheap behaviour?

The owner asked directly: can we brand this as an extra feature for no extra
work, "or do you find it to be cheap behavior".

**It depends entirely on what is claimed, and the line is sharp.**

Honest: *the same construction also detects provider drift, and here is the
argument.* That is a derivation, offered as an extension. It costs nothing
because the derivation really is free.

Not honest: *a-prime detects model drift*, as a capability, with no measurement
behind it.

**Why the distinction matters more here than it would elsewhere.** This
project's credibility rests on everything being measured. ENG-002 reported a
saturated instrument rather than claiming 100% recall. BCH-013 measured tool
selection instead of assuming it. MTH-011 inverted the planned channel ordering
because the measurement contradicted the design. An unmeasured capability claim
would be the **first assertion in a document otherwise built entirely on
measurement**, and a reviewer who spots it is entitled to wonder what else was
asserted. The cost is not the claim. It is the precedent.

### It is about two hours of GPU away from being measured

**Negative control, roughly one hour.** `granite4.2:8b` sits on disk as a file
with a digest. It provably does not change between one week and the next. So:
record a cell now, record the same cell again in a week, and score the two
periods with the threshold taken from the first period's internal decoy spread.
The correct answer is that nothing is flagged. If anything is flagged, the drift
method is broken and we have learned that for one hour.

**Positive control, roughly one more hour.** The pool already holds four models
on disk (BCH-007). Run the same cell on a second model and the drift check
should flag it, because the system genuinely did change. A known change it fails
to see is as informative as a false alarm.

Together that is a two-sided measurement for about two hours on hardware and
weights we already have, and the first half rides along on data being recorded
anyway. After that the claim is a result rather than a derivation, and it can be
stated without hedging.

**Recommendation:** make the claim only after the negative control runs. Until
then the paper says it in one sentence as an extension, in the register STD-001
and STD-006 already use for things that are constructed but not measured.

## STD-009 — The blind-spot map is a recomputation, and two of its rows disagree with probes.md by design
**Date:** 2026-10-04
**Finding:** The declared figure exists: nine checks by fourteen kinds of change,
each cell the firing rate out of 64 pairs at the stated false-alarm budget, plus
five floors below which nothing fired. It is built by
`scripts/draw_blind_spot_map.py` from the `scores` arrays in three committed
probe runs (`20260925T041059Z` normalised, `20260924T031004Z` and
`20260924T022150Z` raw) and runs no model. `tests/test_blind_spot_map.py` pins
it to MTH-019, MTH-021 and MTH-022: 11/64 omission on contradiction, cuts at
-0.055/+0.096, 63/64 omission on the upper tail, 64/64 both register directions
on the lower.

**Two choices a reader of `probes.md` will notice.** First, the two raw runs
predate MTH-021 and labelled hedging as `verbosity` under PRESERVING; the map
relabels them so every row sets its threshold over the same 256 preserving
pairs. That moves a few RoBERTa and embedding cells by two to four points from
the stored `results_global` (quantifier 55% to 58%, name swap 59% to 56%; unit
36% holds). Second, the shipped rows come from the normalised run and the
replication and embedding rows from the raw ones, because that is where each was
measured; each row prints its run id. Mixed provenance in one figure is a cost,
accepted over dropping the rows that show checkpoint dependence (MTH-017) and
the rejected channel (MTH-011).

**Consequence:** the figure is quotable in the paper and the README now carries
it. A regenerated figure that disagrees with the test is a changed input file or
a drifted recomputation, never a new finding.
**Evidence:** `results/blind_spot_map.json` (every cell with its denominator,
interval, threshold and source run); `docs/figures/blind_spot_map.svg`.
**Reopen if:** the probe suite is re-run on the normalised pair set with the
second checkpoint and the embeddings, which would remove the mixed provenance
and should replace the raw rows rather than sit beside them.

## STD-009 — AMENDMENT (dated append, 2026-10-04): the second choice is reversed

The entry above accepted mixed provenance across the grid: shipped rows from the
normalised run, replication and embedding rows from the raw runs. The local
session rejected that on an argument the entry had missed, and the argument is
right.

MTH-019 measured that normalisation buys detection. Putting a normalised DeBERTa
row in the same grid as a raw RoBERTa row therefore flatters DeBERTa against
RoBERTa by an amount that has nothing to do with the model, and a reader of a
grid reads across; a run id per row is a pointer, not a warning. The entry also
missed that DeBERTa is measured in both raw runs, so the grid never needed the
normalised run at all.

**As drawn now:** every grid row comes from the raw pair set, which the two raw
runs share byte for byte (832 pairs, same order; the DeBERTa contradiction
scores are identical across the two files). The shipped configuration, DeBERTa
after normalisation, sits below the grid as its own block, labelled as a
different run and not read across. The gap between the raw DeBERTa rows and the
shipped rows is MTH-019 made visible: omission on the upper tail 92% to 98%,
unit 83% to 100%, quantifier 89% to 100%.

The first choice, relabelling the raw runs, stands, with the reconciliation the
local session asked for written as a dated append under MTH-017.

## STD-010 — First two rows of the matrix: prose transfers across three domains, JSON fails in two of them
**Date:** 2026-10-05
**Finding:** Six cells recorded and analysed, `granite4.2:8b` (digest
`f586c02fdecdf151`), F5 stale view over the four readable shapes, n=40, k=6,
q=0.10, per-input activation as ground truth. 240 triples per cell, 4,320
samples, zero errored. Analysis run `20261005T145729Z` (hospitality-extraction
`...730Z`), commit `26345e7`.

| cell | activated | flagged | true positives | realised FDR | recall |
|---|---|---|---|---|---|
| banking-summary | 17/40 | 19 | 15 | 0.21 | 0.88 [0.66, 0.97] |
| logistics-summary | 14/40 | 11 | 11 | 0.00 | 0.79 [0.52, 0.92] |
| hospitality-summary | 21/40 | 21 | 18 | 0.14 | 0.86 [0.65, 0.95] |
| banking-extraction | 11/40 | 0 | 0 | — | 0.00 [0.00, 0.26] |
| logistics-extraction | 23/40 | 11 | 11 | 0.00 | 0.48 [0.29, 0.67] |
| hospitality-extraction | 25/40 | 0 | 0 | — | 0.00 [0.00, 0.13] |

**Summary row: transfer across all three domains.** Pooled recall 44/52 =
0.85 [0.72, 0.92] with no threshold tuned to any domain. Claimed at exactly
that width: one fault class, one model, one output format. Three systems
succeeding bound the per-system success rate below at 0.29 (Clopper-Pearson,
95%, MTH-008).

**Extraction row: the failure is format-shaped.** Logistics caught 11/23 with
zero false; banking flagged nothing on 11 activated (near the floor, sizing
miss not excluded); hospitality flagged nothing on 25 activated, well above
the floor. **Diagnosis not run**: `diagnose_channels.py` needs the NLI model
on the GPU machine, which is recording the agent row. Recorded as a measured
hole, not explained.

**FDR: not yet decidable.** Two summary cells over budget (0.21, 0.14), one at
0.00; pooled 7/51 = 0.14 [0.07, 0.26], which contains 0.10. At ~20 flags per
cell this is indistinguishable from an honest 0.10 and from a miscalibration.
Needs the agent row.

**Channels:** mode_share 57 and novel_mode 61 flags across the six cells;
nli_contradiction 10 (logistics-summary only); nli_directional 0; embedding
skipped. Not a contradiction of MTH-013: the probes measure a judging model
on single pairs, the cells measure which statistic separates clouds under a
fault that changes which answer is given; the NLI predicate still underlies
the clustering. Contradiction's per-input mean over paired samples diluting a
partial change is a plausible, unmeasured reason.

**k=6, not 20.** Below the working minimum of MTH-018; every recall is a lower
bound on k=20 and mode_share takes seven values. Stated in the paper.
**Evidence:** `results/study/matrix.json`, the six `*.report.json`, the six
`*.jsonl` checkpoints and `*.activation.json` stores; `paper/draft.md` §8.
**Reopen if:** the agent row lands (completes the matrix and the FDR
question); the extraction diagnosis runs (names the hole); a second model
drives the cells (MTH-008 needs more systems than three per row).

## STD-010 — DIAGNOSED (dated append, 2026-10-05)

Two of the three reopen conditions above have fired.

**The extraction hole is resolution, not blindness.** Diagnosed by the local
session with `diagnose_channels.py` and the NLI model (HANDOFF §21, D25; the
diagnosis output itself was not committed). Separation is strong in both
silent cells. Best achievable cuts: 0.111 with one decoy at the top statistic
value in one cell, 0.176 with two decoys in the other, against q=0.10. At k=6
the mode-share statistic takes seven values, the decoys land on the same
seven, and a decoy on the top value puts the floor out of reach. Same shape as
ENG-007, from the other side.

**The fault is near-binary per input, measured here from the committed
activation stores.** Over the six analysed cells, 111 inputs were touched; 101
fired on five or six of their six samples and 96 on all six (distribution of
fired samples per touched input: 1:6, 3:2, 4:2, 5:1, 6:96, 7:4; the sevens are
preflight calls sharing an input id). Instrument: count `hit` keys per
`input_id` across `results/study/*.activation.json`, agent cell excluded. D25
quotes 104 of 111 for the same quantity; the three-input difference is
unresolved and does not change the reading. The k=20 power figures (MTH-018)
were measured on gradual mix shifts and do not transfer to this fault; what k
buys here is decoy resolution.

**Pre-registered (D25):** the summary row is re-recorded at k=20 as a
separate configuration (`run_study.py --k 20`). Prediction before the run:
recall moves modestly; realised FDR moves towards the budget. Full k=20
re-record only if that row's recall leaves the k=6 interval [0.72, 0.92].
**Evidence:** HANDOFF §21; the activation stores; `paper/draft.md` §8.
**Reopen if:** the k=20 summary row lands.

## STD-010 — SECOND APPEND (2026-10-05): the 101/104 discrepancy resolved

Shared instrument run on the committed stores: fired-sample counts per touched
input come out {1:6, 3:2, 4:2, 5:1, 6:96, 7:4}, 111 touched, 101 at five or
more. **The cloud session's 101 stands.** My 104 came from bucketing by
fired/total fraction over totals that included the artifact below.

The four seven-count inputs are the first input (`lookup-000`) of four cells,
carrying keys `#0` through `#6` where k is 6. Mechanism: the preflight probe
invokes the first invocation inside the same process, consuming the fault
wrapper's sample counter at 0; the six recorded samples then take 1 to 6. So
per-sample key numbering drifts by one for that input wherever a preflight and
the recording share a process.

**Per-input any-fired ground truth is unaffected**, so every recall and FDR
number stands. Canonical instrument from here: count fired keys per input id;
read per-sample distributions knowing input zero of a cell may carry one probe
key. A sentinel-id probe was tried and reverted: 64 tests failed, because
systems may key answers on the input id and a probe must stay answerable. The
right fix lives where the wrapper assigns indices, and is open, low priority.

## STD-010 — THIRD APPEND (2026-10-05): diagnosis artifacts, and two banking denominators corrected

**The diagnosis now traces to files.**
`results/study/hospitality-extraction.418a3438efcfbb12.diagnosis.json`:
mode_share best estimate 0.1111 at cut 1.0, 18 targets and 1 decoy above;
18 of 25 touched inputs sit at exactly 1.0, 0 of 15 quiet ones do, and the
single decoy at 1.0 is in the sorted decoy array. The first append cited
HANDOFF §21 for these numbers; cite the file.
`results/study/banking-extraction.7e1c3a40f5946fc8.diagnosis.json`:
mode_share best 0.1765 at cut 0.6667, 17 targets and 2 decoys above; 9 of 11
labelled-touched inputs at or above the cut, 0 of 9 labelled-quiet, and the
other 8 targets above are label-unknown (below).

**Two denominators in the table above are over labelled inputs, not over the
cell (BCH-018).** A resume bug erased earlier sessions' labels: banking-
extraction has 20 of 40 inputs labelled, banking-summary 35 of 40. Corrected
reading: banking-extraction, 11 touched of 20 labelled, 20 unknown; banking-
summary, 17 touched of 35 labelled, 5 unknown. Recall figures stand as recall
over labelled inputs. banking-summary's realised FDR of 0.21 (4 false of 19
flagged) is an upper bound until phase 2 is re-run with `findings` and the
four are split into known-quiet and unknown; the pooled summary FDR 7/51
inherits that. The other four cells are unaffected. The claim of the first
append, transfer across three domains on the summary row, stands: 15 of 17
labelled-touched in banking is unchanged by five unknown inputs.
**Evidence:** the two diagnosis artifacts; BCH-018; the activation stores
against the checkpoints' session fields.
**Reopen if:** phase 2 is re-run with findings (gives the banking-summary FDR
as a number again), or the k=20 summary row lands.
