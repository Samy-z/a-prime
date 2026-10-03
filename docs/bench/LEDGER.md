# bench — LEDGER

Append-only settled findings about systems under test and the fault harness.
Prefix `BCH-###`. Never edit an entry in place; correct it with a dated append
below. **Grep this file before investigating anything.**

Entry format: id, date, finding, consequence, evidence, reopen-if.

---

> No entries yet. The bench seat opens in week 0 with the fault taxonomy freeze.
>
> Constraints already binding this seat: MTH-009 (cluster-split by system),
> MTH-010 (real-regression holdout limits), STD-007 (base rates can fake a
> transfer result).

## BCH-001 — Blast radius is a deployment-topology axis, not a property of fault class
**Date:** 2026-09-24
**Finding:** The design assumed real regressions are localized (a few percent)
while injected faults are global, and treated that gap as the main threat to
label validity. Documented incidents show the split is not real-vs-injected but
**request-path vs shared-artifact**. Faults touching a shared artifact — a
system prompt, a model version, a compiler path, a cache backend — are >=84%
global by construction, because there is one copy. Faults on the request path
— routing, load balancing, provider selection — run 0.0004% to 16%. The same
Anthropic routing bug measured <0.0004% on Vertex and 16% on the API in the
same week, and ~30% at user level versus 16% at request level.
**Consequence:** Blast radius becomes an axis crossed with fault class in the
harness, not an attribute of a class. Inject shared-artifact faults globally and
request-path faults at 1-16%, or the detector learns "global implies injected"
— a harness artifact. User-level and request-level rates differ by roughly 20x
and must be reported separately.
**Evidence:** bench taxonomy research, 2026-09-24, with denominators, in
`.agents/bench-taxonomy-research.md`.
**Reopen if:** never — this is an observation about deployment topology.

## BCH-002 — Class 8 (decoding parameters) has no documented instances; two more are thin
**Date:** 2026-09-24
**Finding:** A search for operator post-mortems found zero documented cases of a
temperature or max-tokens edit causing a production regression. The only
production instance in that area is a compiler miscompilation of approximate
top-k, which is a serving-stack fault, not a parameter edit. Context truncation
has a grade-B mechanism but no post-mortem with a blast radius. Retrieval
degradation has no operator post-mortem at all; its severity ladder can only
come from a paper.
**Consequence:** Class 8 is dropped from the frozen taxonomy or reframed as
"sampling-path fault". Classes 2 and 4 stay but are marked as
mechanism-evidenced rather than incident-evidenced, and that grading appears in
the paper. A taxonomy that claims to be drawn from reality cannot carry a class
with no documented instance.
**Evidence:** bench taxonomy research, 2026-09-24.
**Reopen if:** a documented instance appears.

## BCH-003 — Fault taxonomy frozen
**Date:** 2026-09-24
**Finding:** 14 classes promoted to `docs/knowledge/fault-taxonomy.md` and
frozen. F1-F9 are incident-evidenced from grade A/B operator sources; F10-F14
are mechanism-evidenced with no post-mortem carrying a blast radius, and that
grading is carried into the paper rather than smoothed over. Four classes were
added that were not in the original list of eight — cache contamination,
numerical/serving-stack corruption at fixed model identity, sticky routing
heterogeneity, and persona drift — and one was dropped (BCH-002).
**Consequence:** The freeze commit is the pre-registration reference point.
Nothing may be tuned against the taxonomy from this commit forward. Amendments
are dated appends to the log at the foot of that file.
**Evidence:** `.agents/bench-taxonomy-research.md`; freeze commit on this date.
**Reopen if:** never as a whole. Individual classes change only by amendment.

## BCH-004 — Two severity floors are set by published evidence, not by us
**Date:** 2026-09-24
**Finding:** (a) Retrieval corruption at 10% produced *identical* Hit@k, EM and
F1 to 0% corruption on n=500 (arXiv 2606.28337). (b) Real production prompt
edits at a flagship deployment are 1-3 lines, measured across 14 commits of
`xai-org/grok-prompts`; the largest observed change (+9/-23) is a post-incident
remediation, not a regression.
**Consequence:** If the harness injects 10% retrieval noise and the detector
misses it, that is not a detector failure and must not be scored as one. And a
harness that injects prompt regressions by rewriting whole prompts is injecting
something that does not occur in the wild — the ladder tops out at ~20 lines and
that rung is already remediation-shaped.
**Evidence:** as cited, both reproducible.
**Reopen if:** a larger controlled study moves the retrieval floor, or a second
production prompt corpus shows materially larger routine edits.

## BCH-005 — Three unrelated serving-stack faults share one output signature
**Date:** 2026-09-24
**Finding:** Anthropic's TPU misconfiguration (Thai/Chinese characters in
English replies), Anthropic's XLA:TPU approximate-top-k miscompilation, and
OpenRouter FP4/Int4 quantization (raw `\uXXXX` escapes instead of CJK glyphs)
have three entirely unrelated causes and converge on the same observable:
character- and script-level corruption.
**Consequence:** one cheap, wholly domain-agnostic check covers the family.
Passed to the engine seat as a *fault signature* in the taxonomy, which is
bench's remit; what to build from it is engine's call, not bench's.
**Evidence:** Anthropic post-mortem 2025-09-17 (grade A); Roo-Code #11325
(grade B).
**Reopen if:** a fourth cause with a different signature appears, which would
weaken the convergence argument.

## BCH-006 — F8 split; the identity-aware no-fault cell is a control, not coverage
**Date:** 2026-09-24
**Finding:** Sticky *fault assignment* (infrastructure pins a session to a
backend) and *identity-aware behaviour* (the application varies by who is
asking) are orthogonal, and both produce per-user clustering in a per-input
detector. The second produces it **with no fault present**.
**Consequence:** Both are built, and the identity-aware-no-fault run is the
control arm. Without it, per-user clustering the detector picks up cannot be
attributed to a sticky fault rather than to ordinary personalization, and
MTH-009's cluster-splitting is never validated against the case it exists for.
At least one domain cell gains a user/session dimension, run in three
conditions.
**Evidence:** owner decision 2026-09-24, on the F8 class frozen the same day;
Anthropic routing figures (request 0.8-16% vs user ~30%) motivate F8a.
**Reopen if:** the control arm shows no per-user clustering at all in an
identity-aware system with no fault, which would mean the confound is not real
and F8b can collapse back into F8a.

## BCH-007 — Model pool measured, not read; capability barely discriminates
**Date:** 2026-09-25
**Finding:** The published record does not answer the question. There is no
BFCL v4 figure for Qwen3.5-9B (only an open request to evaluate it), none for
Ministral 3 8B, and the one 8B-class v4 number that exists appears as 52.39 in
one secondary source and 50.29 in another. So it was measured on this box.

Chained two-step tool loop, n=12 per model (call one tool, carry its returned id
into a second, answer): **granite4.2:8b 12/12, ministral-3:8b 12/12, qwen3.5:9b
12/12, ministral-3:3b 9/12**. The constraint binds by **size, not family** —
every 8B drives the loop; the 3B gets single-shot calls right 12/12 and fails
chaining a quarter of the time. 12/12 gives a Clopper-Pearson lower bound of
0.74, which rules out "broken", not "good"; n>=100 before agent cells are built.
**Consequence:** capability is not the discriminator at this size. Pick for
family diversity instead, per MTH-008 and the MTH-017 precedent where one
instrument reproduced every direction and no magnitude.
**Proposed pool (awaiting owner ratification):** granite4.2:8b (IBM, hybrid
Mamba-2 — the only real architectural difference available at this size),
ministral-3:8b (Mistral, dense), qwen3.5:9b (Alibaba, dense), plus a 3B as a
*deliberate weak system* whose high natural error floor tests that the detector
does not read "bad" as "changed". All Apache-2.0.
**Ruled out with reasons:** Hermes, which the owner named — smallest is 14B and
does not fit in 8 GB. Llama 4 — smallest is Scout at 109B, leaving only stale
3.1/3.2 under a 700M-MAU licence. Phi for the banking cell — over-refusal 26.4%
vs 15.6% for Llama-3.2-3B, and disputes/fraud/AML sit in that zone, so F13 would
contaminate both arms. Anything >=12B, including MoE: Nemotron 3 Nano is 3B
active but 30B resident.
**Evidence:** bench survey 2026-09-25, `.agents/bench-model-survey.md`,
reproducible from scratchpad scripts.
**Reopen if:** a larger n on tool chaining separates the 8B models.

## BCH-008 — The 16k context cap costs 3-4x and defeats its own purpose
**Date:** 2026-09-25
**Finding:** Measured aggregate throughput at 150 output tokens, concurrency
swept, VRAM sampled throughout:

| Model | 4k best | 16k best | penalty | peak VRAM |
|---|---|---|---|---|
| granite4.2:8b | 65.8 t/s | 21.4 t/s | 3.1x | 6041 MiB at both |
| ministral-3:3b | 222.2 t/s | 56.4 t/s | 3.9x | 7024 / 7908 MiB |
| qwen3.5:9b | 41.6 t/s | 28.3 t/s | 1.5x | 7888 MiB |

Two independent mechanisms, same conclusion. For dense transformers four slots
of KV at 16k push the model partly off the GPU (7908 of 8188 MiB) and the
offload cliff is a 3x step, not a gradient. For hybrid-Mamba Granite there is no
spill at all — identical VRAM at 4k and 16k — and it still costs 3.1x, from
attention-window compute.
**Also measured:** Ollama's default configuration does not batch. Aggregate
throughput was flat to within 0.5% across an 8x concurrency change while
per-request latency scaled linearly. And qwen3.5:9b cannot batch on 8 GB at all
— at 7888 MiB there is no room for a second slot.
**Consequence:** the 16k cap carried over from prior work is counterproductive
here. Recommend 4-8k per slot, with knowledge packs designed to fit. Owner
decision, since the constraint was theirs.
**Evidence:** bench survey 2026-09-25.
**Reopen if:** a model with materially different KV behaviour enters the pool.

## BCH-009 — Two models on this disk silently inject fault classes we intend to measure
**Date:** 2026-09-25
**Finding:** Both invisible until somebody counted prompt tokens.

**Ministral 3's Ollama template injects a hidden system prompt** — 560 prompt
tokens with no system message, 20 with one. The injected ~540 tokens interpolate
`{{ currentDate }}` and `{{ yesterdayDate }}`, so **the system prompt changes
every midnight**. An A arm on one date and a B arm on the next differ by a
prompt edit nobody made: F2 at blast radius B0 with a 24-hour period. If one arm
straddles midnight the decoy absorbs it as baseline noise and destroys power.

**Qwen3.5 defaults `thinking: true`.** At a 40-token budget it emitted 40 tokens
entirely into `thinking` and returned an **empty** content string. A 150-token
budget can be consumed by reasoning and return nothing — a signature
indistinguishable from F12, which the harness injects deliberately.

**The Ollama client auto-updated itself 0.32.5 to 0.34.4 unprompted** during the
survey. That is F4 provider drift at B0, injected by our own tooling, and it is
what the pinned-instruments rail exists to forbid.
**Consequence:** the harness must assert an explicit system message and explicit
sampling parameters for every system under test, rather than trusting vendor
defaults — default temperature alone differs 1.0 vs 0.15 across the pool, so
comparing defaults compares sampling configs, not models. `Recording.
spans_utc_date_boundary()` now flags the midnight case directly. Moving off
Ollama to a pinned llama.cpp is recommended on the auto-update alone.
**Evidence:** bench survey 2026-09-25, token counts measured.
**Reopen if:** never — these are demonstrated.

## BCH-010 — The 1M generation budget was roughly 3x what the design needs
**Date:** 2026-09-25
**Finding:** At 150 tokens per generation, decode only, Granite at 4k is 26.4
days and at 16k is 81.2 days; prefill adds roughly as much again (estimated).
But MTH-018 fixes 60 calls per input and measured its own power envelope at 400
inputs, so 9 cells x 600 inputs x 60 = **324,000 generations, about 8.5 days**
at the measured rate.
**Consequence:** budget rescoped to ~324k. Combined with input-grouped
scheduling (ENG-001) the prefill component drops from roughly twenty days to
hours.
**Unverified and it gates everything above:** thermal sustain over multi-day
runs. The longest measurement was 85 seconds.
**Evidence:** bench survey 2026-09-25.
**Reopen if:** thermal throttling is measured and changes the sustained rate.

## BCH-011 — Fault harness built; detector thresholds predate it, and git proves it
**Date:** 2026-09-25
**Finding:** `src/aprime/faults.py` implements seven injections mapped to
taxonomy classes, four blast-radius regimes (B0-B3), and per-input activation
logging. The injector **wraps** a system rather than reconfiguring it, so the
same baseline object serves the A and A_prime arms while only B is wrapped —
reconfiguring would put the fault in the system's own state and the decoy would
inherit it.
**Activation, not the cell label, is the ground truth.** A fault labelled at the
cell level is wrong for every input it never touched: truncation cannot truncate
four words, a schema break only bites JSON, a refusal only bites where the
system would otherwise have answered. Tests assert both that a fault finding
nothing records no activation, and that the detector is scored against
activation end to end.
**On seat separation (HANDOFF §2):** building the detector and the harness in
one session is a contamination risk. The auditable guarantee is **commit
order** — every detector threshold (MTH-013, MTH-016, MTH-018, MTH-020,
MTH-022) was fitted and committed before this module existed, against the probe
suite and the stub, neither of which contains an injected fault. That is
checkable in the git history rather than promised.
**Not implemented:** retrieval and knowledge-base faults (F5, F11) and prompt
regression (F2). All three need a system that retrieves or has a prompt to edit,
which is the Palworld adapter's job.
**Evidence:** `tests/test_faults.py`, 13 tests.
**Reopen if:** an injection is added that does not map to a frozen taxonomy
class, which would break the taxonomy's validity argument.

## BCH-010 — CORRECTION (dated append, 2026-09-29)
BCH-010 said the budget was "rescoped from 1M generations to ~324k, which is
what the factorial actually requires". **That conflated two different
calculations and the word "rescoped" was wrong.**

The two figures answer different questions:

| | cells | fault x severity combos | inputs | calls/input | total |
|---|---|---|---|---|---|
| earlier estimate | 9 | **12** | 150 | 60 | 972,000 |
| survey figure | 9 | **1** | 600 | 60 | 324,000 |

The survey's 324k assumes **one comparison per cell** — a single A-vs-B with no
fault grid. The earlier 972k assumed twelve fault-by-severity combinations per
cell. Neither is a rescoping of the other; the survey's number is smaller
because it drops the fault grid, not because it trims inputs. It actually uses
*four times more inputs per cell*.

**The real budget is 9 x F x N x 60**, where F is the number of fault-by-severity
combinations actually run and N the inputs per cell. With the frozen taxonomy
offering 14 classes x 3 severities x up to 4 blast regimes, F is a choice not yet
made, and it is the dominant term. That choice is the budget decision; input
count is not.
**Owner ratification recorded 2026-09-29:** model pool approved as proposed in
BCH-007 — granite4.2:8b, ministral-3:8b, qwen3.5:9b, plus a 3B as a deliberate
weak system. Hermes dropped at 14B.

## BCH-012 — Adapter verified against a live server; BCH-009 confirmed independently
**Date:** 2026-09-29
**Finding:** 29 checks, 4 models, **93 seconds of GPU time**, all passing. Server
0.34.4 on an isolated port; models unloaded per call via `keep_alive: 0`.

**The template injection is real and measured.** Prompt tokens for an identical
user message:

| Model | with explicit system | without | injected |
|---|---|---|---|
| ministral-3:8b | 21 | **554** | **~533** |
| ministral-3:3b | 21 | **554** | **~533** |
| granite4.2:8b | 30 | 16 | none |
| qwen3.5:9b | 30 | 11 | none |

BCH-009 was found by a survey agent; this confirms it independently on a live
server, and confirms the mitigation works — a mandatory explicit system message
takes the prompt from 554 tokens to 21. Both Ministral variants inject; neither
of the other two does.

**New: `think` is not a universal parameter.** Both Ministral models reject
`think=True` with **HTTP 400** rather than ignoring it. A study that set `think`
uniformly across the pool would fail every call on half of it. The adapter
records this as an errored sample, which is correct — an error is not an empty
response.

**Granite supports thinking**, which the survey had listed as unchecked: 57
characters of thinking with an empty content field at a 12-token budget. Qwen
likewise, 44 characters. Both are now flagged by `empty_output`.

**Seed reproducibility holds on all four models** — same seed, byte-identical
output. That is the evidence that the explicit sampling options actually take
effect rather than being ignored.

**Digests come back as bare hex**, not `sha256:`-prefixed.
**Two bugs found, both in our test doubles rather than the adapter.** The fake
transport invented a `sha256:` digest prefix that a live server does not use, and
a verification check conflated "empty response" with "errored response". The
adapter was correct in both cases. This is the argument for verifying against
reality: *tested against a fake* and *verified* are different claims, and the gap
between them was two wrong assumptions about what a real server returns.
**Evidence:** `scripts/verify_ollama.py`, run 2026-09-29.
**Reopen if:** the pinned server version changes — the pass must be re-run,
because these are statements about 0.34.4 and its bundled templates.

## BCH-013 — Eight-tool selection is a non-issue for the 8B pool; the schema cost is smaller than feared
**Date:** 2026-09-29
**Finding:** 16 single-tool requests, two phrasings per tool, plus 4 chained
requests, at temperature 0 with an 8192-token window. 548 seconds of GPU.

| Model | selection | chaining | tool schemas cost | prompt with tools |
|---|---|---|---|---|
| granite4.2:8b | **16/16** | 3/4 | 712 tokens | 759 |
| ministral-3:8b | **16/16** | 3/4 | 461 tokens | 499 |
| qwen3.5:9b | **16/16** | 3/4 | 751 tokens | 800 |
| ministral-3:3b | 15/16 | 1/4 | 461 tokens | 499 |

**Selection among eight tools is not a constraint.** All three 8B models picked
correctly every time. The precondition the nine domain cells were about to be
built on holds, and the owner's argument for eight tools over two costs nothing
in reliability.

**The 3B is weaker in exactly the way it is supposed to be.** 94% selection and
1 of 4 chains, against 100% and 3 of 4 for the 8B models. That is the point of
including it: a deliberate weak system with a high natural error floor, which
tests that the detector reports "changed" rather than "bad".

**Eight tool schemas cost 461 to 751 prompt tokens**, not the 1,200 to 2,000 the
design assumed. Paid on every call, so it is the floor under the context cap,
but an 8192-token window leaves roughly 7,400 tokens for the conversation. The
context budget is comfortable rather than tight, which settles the sizing half of
D11.

**The chaining figure is probably a defect in the test, not the models.** All
three 8B models, from three different families, failed the same one of four.
Independent capability failures would not agree like that. The most likely
culprit is the first chain, whose prompt supplies the account id directly, so
going straight to the second tool is arguably the correct behaviour and the test
scored it wrong. **The instrumentation did not record which chain failed**, which
is a gap: fix that before quoting the chaining number anywhere.
**Evidence:** `results/tool_selection.json`, `scripts/measure_tool_selection.py`.
**Reopen if:** the chaining test is corrected, at which point the 3/4 figure
should be re-derived rather than carried forward.

## BCH-014 — The first live run of the nine cells found four bench defects, three of them silent
**Date:** 2026-09-29
**Finding:** All nine cells run against `granite4.2:8b`, 4 inputs each, 36
invocations, 185 seconds of GPU time. The cells worked structurally: tools were
called, loops terminated, outputs came back. The content was another matter.

| | run 1, as built | run 2, after the fixes below |
|---|---|---|
| non-empty output | 30/36 | **36/36** |
| correct output shape, `extraction` + `summary` | 15/24 | **24/24** |
| correct output shape, `agent` | 1/12 | 3/12 |
| peak prompt tokens | 1723 | 1662 |

**Four defects, all in the bench, none caught by 159 unit tests.**

*A quarter of every corpus returned nothing.* The `compute` request asks for a
ratio from a principal's figures, and no tool exposed those figures: entities
were keyed by entity id and the principal-keyed read returned only prior
records. The model called four different tools hunting for an income number,
ran out of steps and the cell returned `""`. Two defects behind one symptom.
The principal-keyed read now carries the figures, and exhausting the step
budget now withdraws the tools and demands one final answer instead of
discarding the input.

*The model wrote its deliberation into the output*, closing it with `</think>`
though `think` was off and no opening tag ever arrived. This is the dangerous
one. How much a model thinks aloud is exactly the sort of thing that changes
when you swap models, so left in place it would have produced a strong and
entirely spurious regression signal. Stripped and flagged as `think_leak`.

*A quarter of outputs were truncated mid-sentence* at `num_predict=320`. Same
class of confound: a length difference the detector would read as the system
changing when it came from the cap. Raised to 512, with `finish_reason`
recording the cases where it still bites.

*The amount filter was underspecified.* "Show the transactions above 1000" made
the model call `max_amount=1000`, then spend 300 tokens arguing with itself
about the result. The schema said "optionally filtered by amount" and named no
direction. It does now.

**What this says about the test doubles.** Every one of these is a place where
a hand-written fake was more cooperative than reality. The scripted chat
function always terminated, so exhaustion was never exercised; no fake ever
emitted a `</think>` tag; no fake ever failed to find what it was looking for.
That is the fourth, fifth and sixth entry in a list that already had three
(`docs/knowledge/cells.md`). The standing fix, building doubles from captured
real responses, is now overdue rather than open.

**Peak prompt demand is 1,662 to 1,723 tokens against an 8,192 window**, so
roughly 6,500 tokens of headroom. Combined with the 461-751 token schema floor
of BCH-013, this settles the measurement half of D11: the context budget is
comfortable, not tight.
**Evidence:** `results/cells_smoke_before_fixes.json` (run 1),
`results/cells_smoke_corpus_only.json` (run 2), `scripts/smoke_cells.py`.
**Reopen if:** a different model is used as the cell driver. All four defects
were observed on one model, and the reasoning leak in particular is a
model-specific behaviour that others may express differently.

## BCH-015 — Agent mode is shape-distinct but not compliant, and three rounds of fixes bought three inputs
**Date:** 2026-09-29
**Finding:** Agent mode demands a short line beginning APPROVE, DECLINE or
ESCALATE. Compliance across three successive code states, 12 invocations each
(3 domains x 4 inputs, `granite4.2:8b`, seed 7):

| code state | agent compliance |
|---|---|
| as built | 1/12 |
| decision-framed request corpus | 3/12 |
| plus per-mode step budget, format rule restated at the end | 4/12 |

The other two modes went from 15/24 to **24/24** over the same changes, so the
fixes worked everywhere except here. **Stopping at three rounds was a
deliberate call.** The third round bought one input for roughly 40% more GPU
time, and continuing would have been tuning the bench until the number looked
right. That is the failure the bench and engine seats are separated to prevent,
and the absence of a detector does not make it a different mistake.

**Compliance was the wrong question anyway.** The grid is three domains by
three output formats and the detector fits a threshold per output shape. What
that needs is for the three formats to be genuinely different shapes, which is
not the same as each obeying its own format rule. Measured on the saved outputs
(`scripts/check_shape_distinctness.py`, no GPU):

| | agent | summary |
|---|---|---|
| decision token present | **10/12** | **0/12** |
| median words | 32.5 | 51.5 |
| three or more sentences | 7/12 | 12/12 |
| spread, words | 11-396 | 30-104 |

**The modes are shape-distinct.** A decision token appears in one and not the
other, separation 0.83, which is a far cleaner split than length gives. The
third arm of the grid is real.

**It is distinct without being compliant.** 10 of 12 outputs contain a decision
and only 4 lead with one: the model reasons in a paragraph and appends the
verdict. The instruction asks for the verdict first.

**The spread is the part that should worry us.** Agent outputs run from 11 to
396 words while summary runs 30 to 104. A shape-stratified threshold fitted on
a mode that varies by a factor of 36 has very little to hold on to, and this is
a better argument for changing something than the compliance count is.

**Agent mode costs 3.5x what summary costs**: 202 seconds against 57 for the
same 12 invocations, 51 tool calls against 19, peak 2,108 prompt tokens against
1,350. At the study's full corpus size this is the dominant term in the GPU
budget and it has not been costed.

**A first measurement misread this.** The initial verdict rule in
`check_shape_distinctness.py` compared median lengths against an invented 0.6
multiplier and ignored the decision token entirely, and it reported the two
modes as not distinct. It was wrong on the evidence in its own table. The rule
now leads on the token, which is the discriminative feature.
**Evidence:** `results/cells_smoke.json` (run 4, outputs saved),
`results/cells_smoke_before_fixes.json`, `results/cells_smoke_corpus_only.json`,
`results/cells_smoke_counts_only.json`, `scripts/check_shape_distinctness.py`.
**Reopen if:** a different model drives the agent cells. Compliance here is a
statement about one 8B model's instruction following, and a stronger model may
make the whole finding moot.

## BCH-016 — F2 is built on the frozen ladder, and its activation is exposure for five edits of six
**Date:** 2026-10-04
**Finding:** Prompt regression is injectable in all nine cells
(`src/aprime/cells/prompt_faults.py`). The mechanism is the retrieval faults':
change what the model is given, here the system prompt's lines, and let the
model write, so the output carries its own fingerprints. Six edits, each
shaped after a documented incident, declare their lines added and removed; a
test measures the real diff on every format, with and without identity, and
refuses an edit that outgrows its rung. The ladder is the frozen one: +1/−1,
+2/−3, +9/−23. `FaultSpec.severity` is the rung over three.

**The activation decision, stated so it is not mistaken for purchase.** The
taxonomy says F2 fires only where the changed instruction has purchase, and
that per-input instrumentation is mandatory despite B0. Purchase, whether the
instruction changed what the model wrote, is the detector's question. Deciding
it in the harness would need a paired clean invocation of every input, which
doubles recording, the binding constraint (MTH-024). So activation is: in the
blast radius, and the edited prompt differs from the clean one for this
invocation, and the model answered, and the edit's own purchase predicate
where it has one. `identity_dropped` has one (a requester was named). The
other five fire on every answered input, which is exposure.

**Which way that errs.** An input the model answered unchanged despite the
edit is counted as fired and the detector is scored as missing it. That
understates recall on F2; it never inflates it. The opposite convention,
counting only inputs whose output visibly changed, would be grading the
detector against its own answer.

**One consequence for the bench.** `Cell.system_prompt()` now builds lines and
joins them; the joined text is byte-identical to before, asserted in
`test_the_clean_prompt_is_byte_identical_to_before_the_lines_refactor`, so no
recording on disk is affected.
**Evidence:** `tests/test_prompt_faults.py`, 54 tests including the
parametrised ladder check; `docs/knowledge/faults.md`.
**Reopen if:** a study cell can afford the paired clean invocation, at which
point purchase becomes measurable and the five exposure-based edits should be
re-graded against it; or if a seventh edit is proposed, which must name its
incident and sit inside a rung.
