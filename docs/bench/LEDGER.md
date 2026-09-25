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
