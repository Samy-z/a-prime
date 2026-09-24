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
