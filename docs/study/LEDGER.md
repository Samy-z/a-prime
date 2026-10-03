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
