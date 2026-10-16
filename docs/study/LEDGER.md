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

## STD-010 — FOURTH APPEND (2026-10-06): the banking-summary flags split; the FDR is a bracket, not a number

Phase 2 re-run on all six cells with the `findings` field (store-replacement
fix a47f340 in place, labels untouched by the re-run since it records
nothing). Every headline number is unchanged; the matrix rows now carry the
flagged input ids, which makes this split an offline join instead of a rerun.

**banking-summary, 19 flagged:** 15 flags are on labelled-touched inputs
(true positives). Of the 4 others, **1 is a confirmed false alarm** —
`banking-summary-evaluate-022`, labelled quiet — and **3 are unlabelled**:
`banking-summary-history-005`, `banking-summary-policy-002`,
`banking-summary-search-001`, all among the 5 inputs whose session-0 labels
were erased (BCH-018). Those 3 cannot be classified from data on disk; the
labels are gone, not pending.

So the realised FDR of this cell is a bracket: **[1/19, 4/19] = [0.05, 0.21]**,
the lower bound if all 3 unlabelled flags were true detections, the upper if
none were. The pooled summary row inherits it: **[4/51, 7/51] = [0.08, 0.14]**
against the 0.10 budget — the pooled point estimate can no longer be stated
as 0.14, only as inside a bracket that straddles the budget. Hospitality's 3
false of 21 and logistics' 0 of 11 are exact; their labels are complete.

The bracket collapses to a number only by re-recording the cell. The k=20
summary row scheduled 2026-10-06 23:00 records banking-summary fresh with the
fixed store code, so it answers the calibration question at k=20 regardless;
the k=6 bracket stays a bracket.
**Evidence:** `results/study/matrix.json` (rows with `findings`),
`results/study/banking-summary.60ac20518858cf53.activation.json` (35 labelled
inputs), the join of the two.
**Reopen if:** banking-summary is re-recorded at k=6, or a copy of the lost
label store surfaces.

## STD-011 — The agent row at k=6: nothing flagged in any domain, with the fault touching 25-26 of 40 inputs (2026-10-16)

Recorded 2026-10-06 (banking, restarted clean, HANDOFF §21 amendment) and
the night of 2026-10-15/16 (logistics resumed at 70 triples, hospitality from
zero); analysed in run 20261015T205514Z against the matrix code at `de23b8c`
with a dirty tree that held results only.

| cell | config hash | touched | flagged | distinct samples after normalisation | predicate calls | detection |
|---|---|---|---|---|---|---|
| banking-agent | `04b75acf8f69d4ec` | 26 of 40 | 0 | 785 of 944 | 2,300 | 67 s |
| logistics-agent | `4bc58937db555622` | 25 of 40 | 0 | 674 of 956 | 1,955 | 66 s |
| hospitality-agent | `2cea59ca300a6358` | 26 of 40 | 0 | 824 of 958 | 2,666 | 80 s |

Every channel reports zero in every agent cell: mode_share, dispersion,
novel_mode, nli_contradiction, nli_directional; embedding skipped with no
embedder supplied, as in all nine cells. Labels are complete in all three
(the BCH-018 fix predates every agent session; banking-agent was restarted
clean for exactly this).

**What the finding is.** At six samples the detector is silent on the agent
format in three of three domains, so the format effect that STD-010 found on
extraction (two of three silent) is complete on agent: five of the six
non-prose cells report nothing. The transfer question for this format is
unanswered at k=6, not answered negatively: a zero-flag cell means no check
found a threshold it could justify at the budget, and STD-010's diagnosis
showed that this can be decoy resolution rather than blindness.

**What the data on disk suggests, untested.** Agent outputs are far more
diverse after normalisation than the other formats: 70 to 86 percent of a
cell's samples are distinct, against 35 to 62 percent for the summary and
extraction cells (`cost.distinct_after_normalisation` in the matrix rows).
With six samples per cloud and most samples unique, the share-of-answers and
new-answer statistics carry almost no mass per mode and the decoy scores crowd
the same few values, which is the STD-010 mechanism in a harsher regime. This
is a hypothesis until `scripts/diagnose_channels.py` is run on the three
cells; it needs the NLI model and no system under test. Also unexplained: 944,
956 and 958 of 960 samples entered clustering in the three cells, against 960
in every summary and extraction cell; the diagnosis should say which samples
were dropped and why.

**Evidence:** `results/study/matrix.json` rows 7 to 9; the three `.jsonl`
checkpoints and `.activation.json` stores named by the hashes above;
`logs/chain.log` (uncommitted) for the timings.
**Reopen if:** the diagnosis is run on the agent cells (expected to reclassify
this as resolution, blindness or wide decoys); or an agent cell is recorded at
k=20; or a second model drives the agent format.

## STD-011 — FIRST APPEND (2026-10-16): the NLI diagnosis is blocked on the cloud instance; the two side questions settled without it; a decision-level reading on record

Written on the Claude Code cloud instance. Its network policy answers 403 to
CONNECT for `huggingface.co`, `cdn-lfs.huggingface.co`, `hf-mirror.com` and
`download.pytorch.org`; `pypi.org` and `files.pythonhosted.org` are open. The
pinned stack installs from PyPI in a few minutes (torch 2.14.0 PyPI build,
transformers 5.17.0, 5.5 GB, CPU) and `scripts/diagnose_channels.py` then
fails at `AutoTokenizer.from_pretrained` with no model on disk and no cache.
**The three agent `.diagnosis.json` files are therefore not written by this
append, and the classification (resolution / blindness / wide decoys) stays
open.** Two ways to close it, the owner's choice: add `huggingface.co` and
`cdn-lfs.huggingface.co` to the cloud environment's allowed domains and rerun
task 1 of `docs/study/cloud-trial-tasks.md`; or on the GPU machine

    python scripts/diagnose_channels.py results/study/banking-agent.04b75acf8f69d4ec.jsonl
    python scripts/diagnose_channels.py results/study/logistics-agent.4bc58937db555622.jsonl
    python scripts/diagnose_channels.py results/study/hospitality-agent.2cea59ca300a6358.jsonl

about a minute each with the model loaded, and commit the three files.

**Side question 1, settled: the missing samples are errored calls, dropped by
`Recording.clouds`.** `recorder.Recording.clouds` keeps a sample only when
`error is None`. `load_checkpoint` keeps the last write per (triple, arm) and
drops only triples where all three arms errored (ENG-008); a triple with one
or two errored arms is complete, and its errored arm contributes no sample.
The agent cells are the only cells with errored calls: banking-agent 12 live
errored samples (A 4, A′ 3, B 5), logistics-agent 3 (one per arm),
hospitality-agent 2 (both B). `cost.samples_clustered` counts A in both arm
pairs, so the shortfall is 2·A + A′ + B: 2·4+3+5 = 16 → 944; 2+1+1 = 4 → 956;
2 → 958. Six, three and two inputs ran on clouds of four or five
(`Report.short_clouds`). The errors are the serving process's: `HTTP Error
500` (banking 10 of 21 raw records, logistics 3, hospitality 2), `WinError
10061` connection refused (banking 10; the stop without a logged cause,
`docs/knowledge/environment.md`), one `WinError 10054` reset. banking-agent's
checkpoint holds 729 records: triples `lookup-036#5`, `search-037#0` and
`search-037#1` died with all three arms errored in session 0 (2026-10-06) and
were recorded again in session 1, the dead-triple path working as built;
21 − 9 = 12 errored samples remain live inside triples that had a good arm.
Ten further samples (banking 5, logistics 3, hospitality 2) came back empty
with no error (`finish_reason: length`, one `max_steps`); they enter
clustering as the empty string and form a mode of their own.
`finish_reason: max_steps` on 79, 157 and 282 of 720 live samples: the agent
hit its step cap and the output is whatever it had, the format's behaviour as
kept (paper §6, "What the first live run found"). Median call latency 62.7 s,
15.4 s and 16.1 s against 4.0 s for banking-summary.

**Side question 2: distinctness is the regime, not a coincidence, and the
judge's merging is the only resolution these cells have.** Three readings,
all without the judge; instrument `scripts/agent_decision_variation.py`,
output `results/study/<cell>.<hash>.decisions.json` for the three agent cells
(committed with this append).

1. *Exact distinctness bounds modes from above.* 785 of 944, 674 of 956 and
   824 of 958 clustered samples are distinct after normalisation (83, 71, 86
   percent) against 35 to 62 percent in the six other cells (matrix rows);
   within a cloud of six, mean distinct fraction 0.89, 0.76, 0.90
   (`exact_match.within_cloud_distinct_fraction_mean`).
2. *With no predicate the decoys saturate.* The shipped exact-match
   configuration (`detect(predicate=None)`) puts mode_share and novel_mode
   decoys at the top value 1.0 on 22, 17 and 25 of 40 inputs; best achievable
   estimates 0.852, 0.720, 0.812, all at cut 1.0
   (`exact_match.channels.*`). The same instrument on banking-summary and
   hospitality-extraction: 4 and 5 of 40 decoys at the top value (run, not
   committed; the decision block is void for a non-agent cell). Under exact
   matching the two baseline runs share no answer on about half the agent
   inputs, so every bit of resolution the shipped detector has here is the
   NLI predicate merging paraphrases. How far it merged: the greedy clustering
   makes between m(m−1)/2 + (d−m) and m(m−1)/2 + (d−m)·m predicate calls for
   d distinct strings ending in m modes, so the recorded `predicate_calls`
   (2,300 / 1,955 / 2,666 over 80 clusterings, d known per clustering from
   the checkpoint) is consistent with 3.5 to 7.7, 3.1 to 6.8 and 3.9 to 8.3
   modes per clustering of twelve samples, against 1.9 to 4.6 for
   banking-summary and 2.9 to 5.1 for hospitality-extraction (derived, not
   measured; the diagnosis files will carry the measured partition).
3. *At the decision level the decoys are as wide as the targets.* Decision
   token (APPROVE / DECLINE / ESCALATE, first occurrence, case-sensitive)
   scored with `stats.tv_distance`, candidate vs baseline (target) and
   baseline vs second baseline (decoy): decoy median 0.1667 in all three
   cells, max 0.8333 / 0.6667 / 0.6667; target-on-fired median 0.1667 /
   0.1667 / 0.25, max 0.80 / 0.6667 / 0.8333; decoys at exactly 0: 17 / 19 /
   15 of 40; best achievable 0.667 / 0.50 / 0.40. Majority decision differs
   A vs A′ on 7 / 7 / 8 of 40 inputs; A vs B on 3 of 26, 11 of 25, 9 of 26
   fired inputs and 2 of 14, 5 of 15, 1 of 14 quiet ones. In banking-agent
   the fault changed the decision less often than the system changed its own
   between two identical runs. This is the docstring's third class, measured
   on the one part of an agent's output that needs no judge; the rationale
   text is the judge's question and stays open.

**Expectation on record before the diagnosis runs.** Decoys spread as wide
as the fired targets on mode_share and novel_mode (the system's own
variation of the fault's size), best estimate well above 0.10 with several
decoys above the best cut, unlike STD-010's single decoy on the top value. If
instead the fired targets stand above the decoys at a cut the budget cannot
justify, the reading is STD-010's and k=20 is the remedy.

**Evidence:** the three `.decisions.json` files;
`scripts/agent_decision_variation.py` and `tests/test_agent_decision_variation.py`;
`results/study/matrix.json` rows 7 to 9; the three checkpoints (error and
`finish_reason` fields; the duplicated triples).
**Reopen if:** the diagnosis files are written (STD-011's first reopen
condition stands); the agent prompt is changed to put the decision first
(paper §6 says it is kept as it is, so the decision-level reading would be a
new instrument reading a new system).

## STD-010 — FIFTH APPEND (2026-10-16): the "all six" count was 100 of 111, not 96; the nine-cell figures are 188 / 168 / 165

Found while recomputing the firing fractions for the nine-cell paper
section. The first append's "96 on all six" counted inputs whose activation
keys sum to exactly six. The first input of a cell carries seven keys, `#0`
to `#6` (second append: the preflight re-invokes it in-process and the store
numbers that invocation too), and in the four cells where that input was
touched (logistics-summary, hospitality-summary, logistics-extraction,
hospitality-extraction) all seven keys are true, so the input fired on all
six recorded samples and an exact-six count dropped it. Correct count over
the six recorded keys, the seventh set aside: **100 of 111 on all six**; the
101 on five or six of six is unaffected (a seventh true key cannot move an
input across that line). The three touched inputs with fewer than six keys
(label loss, BCH-018: banking-summary 1, banking-extraction 2) cannot be
judged either way and are in neither numerator.

Nine cells, same convention: 188 touched; 168 fired on five or six of six;
165 on all six (agent row 77 / 67 / 65; per cell all-six: 15, 14, 21, 9, 19,
22, 21, 20, 24). The paper's section 8 carries 188 / 168 / 165; its earlier
draft carried 111 / 101 / 96 and is superseded. Instrument: for each touched
input take the keys sorted by index, drop `#0` when there are seven, require
six keys, count trues; `docs/study/METHODS.md`, "Known data traps".
**Reopen if:** an activation store is found with seven keys on an input that
is not the cell's first, or with a `#0` that is not the preflight.

## STD-012 — The claim surface, expanded after results and declared as such: the two-question paper (2026-10-16)

Ratified by the owner 2026-10-16, after a nine-agent framing audit (full
paper, full HANDOFF and ledgers, the FDR code, the completed matrix; four
adversarial critics). Prompted by STD-011: with the agent row silent in all
three domains, domain explains almost none of the matrix's variance and
output format plus k explain nearly all of it (summary 3/3 detected,
extraction 1/3, agent 0/3, tracking distinct-sample share 35-62 percent
against 70-86). The pre-registration froze the fault taxonomy and the
protocol, not the claim surface, so this expansion is legal; this entry is
what keeps it honest, by declaring it dated and after the data.

**The paper keeps its pre-registered question and gains a second, declared
post hoc.** First question, as registered (STD-005): does label-free
regression detection transfer across domains? Answered at its honest width:
yes on the summary format, three of three domains, per-system success
bounded below at 0.29; unresolved below the certification floor on the other
two formats at k=6. Second question, generated by this study and labelled so
wherever it appears: certifiable difference-information per sample is
governed by output format (through mode diversity) and by k, not by domain.
Its confirmatory arm is the k=20 summary row, pre-registered under D25 with
the prediction filed before the run. The k=6 sizing slip (HANDOFF §21: the
matrix recorded below the paper's own stated minimum through an undocumented
choice) is disclosed in the paper body, not only here.

**What was considered and rejected:** retitling the paper to the deeper
question — how much information about a system, and about differences
between systems, can be mined from outputs alone. Rejected on three grounds:
the between-systems half has zero measurements (all nine cells run one
model, and the decoy arm calibrates within-system variance only — an
A-vs-B null needs a B-prime arm that does not exist); the question as posed
has no failure condition; and swapping a registered question after results
is the pattern this project's rails exist to prevent. That question is the
designated thesis of a second study, whose required instruments are a
cross-model cell with a proper null and the resolution surface over (k, n,
dispersion, q). MTH-025, frozen the same day and before the agent diagnosis,
is the guard that keeps "resolution, not blindness" falsifiable in the
meantime.

**Evidence:** the matrix variance partition (results/study/matrix.json rows
1-9 with STD-010/STD-011); the framing audit's four critic reports
(2026-10-16, session artifacts); the owner's ratification.
**Reopen if:** the k=20 summary row contradicts the format-and-k reading; a
second model inverts the format gradient; or the second study's cross-model
null design shows the within-system decoy arm was carrying more of the
argument than this entry assumes.
## STD-011 — SECOND APPEND (2026-10-16): the diagnosis, run on the GPU machine; all three agent cells classify as resolution-limited under MTH-025, with the decoy width the first append expected

Run locally because the cloud instance cannot reach the model hosts (first
append). `scripts/diagnose_channels.py` unmodified since the MTH-025 freeze;
the three `.diagnosis.json` artifacts are committed beside their checkpoints
with this entry.

Per MTH-025, taking each cell's lowest best-achievable estimate:

| cell | best channel(s) | best estimate | targets/decoys above | separation | classification |
|---|---|---|---|---|---|
| banking-agent | mode_share, novel_mode | 0.250 at cut 1.0 | 4/0 | +0.120, +0.158 | resolution-limited |
| logistics-agent | mode_share, novel_mode, nli_contradiction | 0.250 | 4/0 | +0.13 to +0.20 | resolution-limited |
| hospitality-agent | mode_share | 0.375 at cut 0.833 | 8/2 | +0.126 | resolution-limited |

Rule 1 (blindness) fails in every cell: mode_share and novel_mode order a
subset of touched inputs above every decoy. Rule 2 applies: the best
estimates (0.25, 0.25, 0.375) all exceed q = 0.10. No cell is a selection
defect.

**The decoy width, reported as MTH-025 requires, is where these cells differ
from the extraction pair.** Extraction's near-miss had 17-18 targets above
1-2 decoys (estimates 0.111-0.176). Here decoys span 0 to 0.833 in banking
and logistics and the full 0 to 1.0 in hospitality, covering the fired-target
range except the top grid value — so only 4 to 8 of 25-26 fired inputs
separate at all, and the floor needs ten clean of every decoy. The first
append's expectation (decoys as wide as the fired targets, the system's own
variation) is confirmed for the majority of inputs; the frozen precedence
still lands on resolution-limited because rule 1 requires that NO channel
separates, and two do, on a minority. Both readings are in the artifacts.
The nli_directional channel carries nothing here (banking 0.72 with negative
separation; hospitality 40 targets and 40 decoys above its best cut).

Consistent with the first append's decision-level reading: the fault moves
the agent's decisions about as much as the system moves its own between two
baseline runs, and the text-level separation that does exist lives on a
minority of inputs.

**Expectation for an agent cell at k=20, filed before any such run exists:**
the grid refines from 7 to 21 values, which should pull the 0.833-decoys off
the top and improve the estimates; whether ten or more fired inputs separate
cleanly is the open question, because the binding count here is separating
inputs, not grid fineness. If a k=20 agent cell still cannot reach budget,
that is a statement about information per agent output at this fault, not
about k.
**Evidence:** the three committed `.diagnosis.json` artifacts;
`results/study/<cell>.<hash>.decisions.json` (first append); MTH-025.
**Reopen if:** an agent cell is recorded at k=20, or a second model drives
the agent format.

## STD-011 — THIRD APPEND (2026-10-16): the hospitality row's 8/2 was a float-tie artefact; 5/1 at the top value, estimate 0.4; classification unchanged; what the GPU machine owes

Written on the cloud instance, no model. ENG-010: `fdr.best_achievable` and
`fdr.select` compared raw floats, and `tv_distance` puts the same value 5/6 on
two adjacent floats depending on cloud composition, so at the upper float
every score on the lower one counted as below the cut. The second append's
hospitality row (0.375 at cut 0.833, 8 targets above 2 decoys) is that
artefact: the committed file's own arrays hold, at or above 5/6, 9 fired and 4
quiet targets and 9 decoys. Value-consistent, that cut is 13 above 9, estimate
0.769, and the best cut is 1.0 with 5 targets (3 fired, 2 quiet) above 1
decoy, estimate 0.4, which ties `novel_mode` exactly. The other two agent
cells and hospitality-extraction re-derive unchanged; banking-extraction's
file cannot be re-derived (arrays hold 20 of 40 targets, METHODS "Known data
traps"). MTH-025 amendment carries the corrected table; **all three agent
cells stay resolution-limited** (rule 1 fails on positive separation, rule 2
applies at 0.25, 0.25, 0.40 against q = 0.10).

Corrected sentences of the second append: "only 4 to 8 of 25-26 fired inputs
separate at all" reads 4, 4 and 0 fired inputs above every decoy, hospitality's
best cut admitting 3 fired and 2 quiet inputs against one decoy at the top
value; the paper's §8 sentence "places 8 touched inputs above all but 2
decoys, an estimate of 0.375" is superseded and is the reader seat's to
rewrite once the rerun lands. The decision-level reading (first append):
hospitality-agent's `.decisions.json`, regenerated by the same instrument with
the fix and committed with this append, reads best 0.6 at cut 0.667 (5
targets above 2 decoys) where it read 0.4 (5 above 1); the first append's
"0.667 / 0.50 / 0.40" is therefore 0.667 / 0.50 / 0.60; banking-agent and
logistics-agent regenerate byte-identical. The reading itself (decoys as wide
as the fired targets at the decision level) is unchanged.

Instrument for the re-derivation, run from the repo root with the fixed
`fdr.py`, no model:

    python - <<'EOF'
    import json, sys; sys.path.insert(0, "src")
    import numpy as np; from aprime.fdr import best_achievable
    d = json.load(open("results/study/hospitality-agent.2cea59ca300a6358.diagnosis.json"))
    for name, ch in d["channels"].items():
        if "skipped" in ch: continue
        b = best_achievable(np.array(ch["targets_fired"] + ch["targets_quiet"]), np.array(ch["decoys"]))
        print(name, round(b.estimate, 4), round(b.cut, 6), b.targets_above, b.decoys_above)
    EOF

**What the GPU machine owes, and what each can change.** Every number below
can only move one way (ENG-010): flagged counts fall or hold, best estimates
rise or hold, so nothing silent becomes loud.

1. The five `.diagnosis.json` files, about a minute each with the model
   loaded, `python scripts/diagnose_channels.py results/study/<cell>.<hash>.jsonl`
   for banking-agent `04b75acf8f69d4ec`, logistics-agent `4bc58937db555622`,
   hospitality-agent `2cea59ca300a6358`, banking-extraction `7e1c3a40f5946fc8`,
   hospitality-extraction `418a3438efcfbb12`. Expected: only hospitality-agent
   `mode_share` moves, to 0.4 at 1.0 with 5/1; banking-extraction is the one
   file this append could not pre-check.
2. The nine `report.json` files and `results/study/matrix.json`: the k=6
   analysis stage, which the 05:00 task already runs in a few minutes
   (`scripts/run_study.py`). Per-stratum `select` is the live path with the
   defect, so the summary row's recall (0.88 / 0.79 / 0.86) and
   logistics-extraction's 0.48 can fall and cannot rise; the five silent cells
   stay silent; banking-summary's realised-FDR bracket [0.05, 0.21] is to be
   recomputed from the new flagged set (STD-010 fourth append's method).
   Thresholds will print at nine places.
3. Optional, dated evidence rather than live numbers: the 2026-09-29/30
   single-cell artifacts (`results/cell_detection_*.json`) behind ENG-007 and
   MTH-024 ("9 above zero decoys, one short of ten") were produced at k=6 on
   the same grid and may carry the same split; `scripts/diagnose_channels.py`
   on `results/cell_detection_20260929T231931Z.jsonl` would say.

The paper waits on item 1 for its §8 hospitality sentence and on item 2 for
its section 8 table and Appendix F; the abstract's result was already waiting
on the k=20 row. Nothing in the k=20 recording is affected: the checkpoints
are raw samples and the estimator runs at analysis time.

**Evidence:** ENG-010 and `tests/test_fdr_ties.py`; the committed
hospitality-agent diagnosis arrays; the regenerated
`results/study/hospitality-agent.2cea59ca300a6358.decisions.json`; MTH-025
amendment; the command above.
**Reopen if:** item 1 or 2 lands with a number outside the directions stated
here, or banking-extraction's rerun moves its best estimate across q.

## STD-011 — FOURTH APPEND (2026-10-16): the GPU reruns are done; the matrix does not move

Everything the third append listed as owed is run and committed. The five
diagnosis files: only hospitality-agent moved (mode_share and novel_mode to
0.400 at the top value, 5 targets above 1 decoy), and the other four
regenerated byte-identical — banking-extraction included, the one file that
could not be pre-checked offline. The ENG-007/MTH-024-era single-cell
artifact re-derives its committed 0.111 at 9 targets over 0 decoys, so the
pre-study floor story carried no tie split. The k=6 phase 2 re-ran on the
tie-consistent estimator: **every cell's flag count is unchanged** (19, 11,
21, 0, 11, 0, 0, 0, 0), so the summary-row recalls, logistics-extraction's
0.48, the FDR brackets and every MTH-025 classification stand as committed.
The third append's warning that recalls could fall resolves to: they held.
No live selection ever sat on a split tie; the defect's committed damage was
one diagnosis tally and the README demo, both already corrected.
**Evidence:** `results/study/matrix.json` and the nine report files at this
commit (tie-consistent run ids); the six regenerated diagnosis artifacts
(f56af52); the merge 7832307.
**Reopen if:** the k=20 reports, analysed on the same estimator, disagree
with their recordings' committed k=6 counterparts in a way ENG-010 would
explain.
