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
