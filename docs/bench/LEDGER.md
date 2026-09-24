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
