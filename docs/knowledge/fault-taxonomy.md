# Fault taxonomy — FROZEN 2026-09-24

**Status: frozen.** Amendments are dated appends to the log at the foot of this
file. Never edit a class in place. Nothing may be tuned against this taxonomy
before the freeze commit, and any change after it is an amendment with a reason.

Every class here is drawn from a documented incident or a documented mechanism,
and each carries its evidence grade. **A class with no documented instance does
not belong in a taxonomy that claims to be drawn from reality** — one candidate
was dropped on that basis (see BCH-002 and the exclusions at the foot).

Evidence base: `.agents/bench-taxonomy-research.md` (layer 4, not committed).
Grades: **A** operator's own post-mortem; **B** primary artifact not authored by
the operator (issue on a real project, court ruling, paper); **C** reputable
secondary reporting of a confirmed event.

## What this document is and is not

It is the **class list and severity ladders** — shared by every seat, and
required reading for both `engine` and `bench`.

It is **not** the seed record. Which inputs receive which fault at which
severity in a given run stays with `bench` and is not visible to the seat
tuning the detector. The separation is about seeds, not about the catalogue;
see HANDOFF §2.

---

## Blast radius is an axis, not an attribute

The single most consequential correction from the research (BCH-001). The
design assumed real regressions are localized and injected faults are global.
The documented split is not real-versus-injected — it is **request-path versus
shared-artifact**.

| Code | Regime | Rate | Why |
|---|---|---|---|
| **B0** | Shared artifact | >=84%, usually 100% | There is one copy of the system prompt, the model version, the compiler path, the cache backend. Global *by construction*. |
| **B1** | Platform-localized | Varies by surface, 3+ orders of magnitude | Same bug, different deployment surface. Anthropic's routing error: 16% on the API, <0.0004% on Vertex, in the same week. |
| **B2** | Request-path, uniform | 0.0004%–16% | Routing, load balancing, provider selection, canaries. |
| **B3** | Request-path, sticky | request rate x ~20 at user level | Anthropic: 0.8–16% of requests, ~30% of users. Session affinity is the norm, not the exception. |

**Every fault class is injected across the applicable regimes, not at one
rate.** If the harness injects prompt faults globally and routing faults at 1%,
it matches reality on both — and a detector trained on anything else learns
"global implies injected", which is a harness artifact with no counterpart in
the wild.

B3 is adversarial for MTH-009. A sticky fault looks like a per-user style
signature rather than a fault, which is precisely what cluster-split validation
is trying to factor out. Treat it as the internal-validity stress case.

External anchor for the bottom of every ladder: providers publish blast radius
in percent-of-requests and treat **~1%** as worth a public status incident.

---

## Incident-evidenced classes

These have at least one grade A or B instance from a real deployment.

### F1 — Model swap / downgrade
Same request, different model or different serving configuration behind the
same name.

- **Evidence:** A. Anthropic context-window routing (2025-08-05 → 09-16);
  GPT-5 launch-day autoswitcher failure (grade C event, operator-confirmed);
  Azure OpenAI ships auto-upgrade-to-default as a *product feature*, so the
  class is not hypothetical; Chen et al. (arXiv 2307.09009) measured
  version-to-version drift independently.
- **Output symptom:** degraded quality only. No error, no latency signal.
- **Regimes:** B1, B2, B3.
- **Severity ladder:** silent config difference behind one name → snapshot
  version bump → cross-family substitution → hard retirement (loud, 404).
- **Activation:** all inputs, though effect concentrates on the hardest.
- **Detection in the wild:** ~30 days, via user reports. Anthropic's own
  evaluations did not capture it.

**Ladder warning.** Chen et al. revised GPT-4 prime accuracy from 97.6%→2.4%
(v1, primes-only) to **84%→51%** (v3, balanced, n=1000). The original figure
measured an answer-bias flip, not a capability collapse. A severity ladder keyed
to distributional shift would have mis-scored it by 40 points. **Ladders are
defined on task-correct outcomes over a balanced set, never on raw
distributional distance.**

### F2 — Prompt regression
The instruction text changed, or old text was resurrected by a code path.

- **Evidence:** A. Grok 2025-05-14 (unauthorized modification, "code review
  process for prompt changes was circumvented"); Grok 2025-07-08 (deprecated
  instructions reactivated by an upstream code change, ~16 hours);
  GPT-4o sycophancy 2025-04-25 (reward-signal change, rolled back in 4 days);
  DPD 2024-01 (grade C, operator attributes output regression to a system
  update).
- **Output symptom:** for injected instructions, the tell is **irrelevance, not
  falsity** — Grok injected unrelated content into replies about streaming
  services and baseball.
- **Regimes:** B0. One prompt, one copy.
- **Activation:** partial even under B0 — fires only on inputs where the
  changed instruction has purchase. Per-input activation instrumentation is
  mandatory here despite the global blast radius.

**Severity ladder, anchored on measured production diffs.** From
`xai-org/grok-prompts`, 14 commits 2025-05-15 → 2025-11-17:

| Rung | Change size | Real example |
|---|---|---|
| 1 | +1 / −1 line | `db48cde`, 2025-07-13 |
| 2 | +2 / −3 lines | `9ad2adc`, 2025-07-13 |
| 3 | ~+9 / −23 lines | `e517db8` — and note this is the post-incident **cleanup**, i.e. a remediation, not a regression |

**Real production prompt edits are one to three lines.** A harness that injects
prompt regressions by rewriting or deleting whole prompts is injecting something
that does not occur in the wild, and a detector tuned against it is tuned
against a fiction. Rung 3 is the ceiling and is already remediation-shaped.

### F3 — Tool surface change
An upstream tool is renamed, removed, or changes schema.

- **Evidence:** B. LibreChat #16242 — one tool rename left **474 agents**
  holding a dead key, "none showed any error, warning, or visual indicator",
  undetected ~10 months, found only by a manual database query.
  Mastra #23731 — one invalid upstream schema returns 400 on **100% of that
  agent's requests**, including "Say hello in three words".
  LinkedIn Engineering (grade A) — schema-compliance errors **~10% → ~0.01%**
  after a defensive parser.
- **Output symptom:** two completely different signatures from the same class.
  Silent version: a **capability hole** — fluent, correct-looking prose where a
  tool result should be. Loud version: total hard failure on unrelated inputs.
- **Regimes:** B0 (the tool surface is shared) but activation is narrow.
- **Severity ladder:** 0.01% → 0.1% → 1% → 10% → 100% of tool-requiring
  inputs. The LinkedIn range is a **1000x spread inside one class at one
  company**; a single severity for "schema breakage" is wrong by three orders
  of magnitude.
- **Activation:** only inputs that would have invoked the tool. Most of the 474
  agents' traffic was unaffected.

### F4 — Provider drift
The hosted endpoint's behaviour changes with no version change announced.

- **Evidence:** A, including the provider documenting it themselves. OpenAI
  ships `system_fingerprint` whose stated purpose is to let callers detect that
  "OpenAI updates numerical configuration of the infrastructure serving their
  models (which may happen **a few times a year**)" — the vendor's own base
  rate.
- **Regimes:** B0 within a platform, B1 across platforms.
- **Activation:** all inputs.
- **Consequence for us:** this is why the decoy arm doubles as a drift alarm
  (MTH-007). A large A-vs-A-prime signal means the baseline moved underneath
  the measurement.

### F5 — Knowledge-base staleness or corruption
The retrieved or memorised content is wrong or out of date.

- **Evidence:** A/B. Google AI Overviews (2024-05) — policy violations at
  **<1 in 7,000,000** queries carrying an overview, the extreme low end of the
  corpus; NYC MyCity business chatbot (~5 months undetected, found by
  journalists); *Moffatt v. Air Canada* (n=1, surfaced via tribunal, ~15
  months); Cursor support bot "Sam" (2025-04).
- **Regimes:** B0 for the corpus, narrow activation per document.
- **Activation:** only inputs whose retrieval touches the affected documents.
  Instrument per input; a corpus-level label is noise.

### F6 — Cache contamination / cross-request leakage
The output contains content from a *different request*.

- **Evidence:** B. LMCache #4385 — long-context sessions returning after KV
  cache paged to disk answered from other conversations: **14 of 138 session
  returns correct, ~90% contaminated**, and "the corruption is entirely
  silent". Detected only by a needle-in-a-haystack probe with unique per-session
  identifiers — i.e. by exactly the kind of black-box ground-truth check this
  project builds. Corroborated by kilocode #14080 (cross-tenant splicing, 13
  sessions, 2 backends) and OpenAI's 2023-03-20 Redis race (**1.2%** of Plus
  subscribers, grade C).
- **Output symptom:** verifiably foreign content. The most black-box-detectable
  class in the entire corpus.
- **Regimes:** B0 or B2 depending on cache topology.
- **Why it matters beyond itself:** at ~90% contamination while being entirely
  silent, it is a direct counterexample to "silent implies small". Record it as
  such rather than burying it.

### F7 — Numerical / serving-stack corruption at fixed model identity
Model name, prompt, parameters and retrieval all unchanged; the arithmetic
changed.

- **Evidence:** A. Anthropic TPU misconfiguration (2025-08-25 → 09-02) —
  "producing Thai or Chinese characters in response to English prompts, or
  producing obvious syntax errors in code"; Anthropic XLA:TPU approximate-top-k
  miscompilation (→ 09-12) — "the highest probability token to sometimes
  disappear from consideration entirely", masked for ~8 months by an earlier
  workaround; OpenRouter FP4/Int4 quantization emitting raw `\uXXXX` escapes
  instead of CJK glyphs (Roo-Code #11325).
- **Signature convergence, and this is the finding:** three unrelated causes —
  hardware misconfiguration, aggressive quantization, compiler bug — all surface
  as **character- and script-level corruption**. One cheap, wholly
  domain-agnostic check covers the family.
- **Regimes:** B1 strongly. Anthropic's corruption hit the Claude API only;
  third-party platforms were unaffected.
- **Why task metrics miss it:** Anthropic's own account — "Claude often recovers
  well from isolated mistakes". A single corrupted token inside an otherwise
  correct answer does not move a task-accuracy metric. This is a direct argument
  for distributional over task-metric detection.

### F8 — Sticky routing heterogeneity
Same model name, requests split across non-identical backends, assignment
sticky per user or session.

- **Evidence:** A. Anthropic routing — **0.8–16% of requests but ~30% of Claude
  Code users**, because stickiness meant affected users were consistently
  affected. A routine load-balancing change on 2025-08-29 multiplied the blast
  radius 20x without touching the underlying bug.
- **Kept separate from F1 deliberately.** The statistical consequence differs: a
  uniformly sampled 1% request-level fault and a sticky 1% user-level fault
  produce entirely different clustering in a per-input detector.
- **Regimes:** B3 by definition.
- **This is the internal-validity stress case for the whole study.** A sticky
  fault presents as a per-user style signature, which is what MTH-009's
  cluster-splitting is designed to factor out. If the harness has no B3 cells,
  the validation protocol is never tested against its hardest case.

### F9 — Persona / tone / sycophancy drift
Output style changes with no change in task accuracy.

- **Evidence:** A. GPT-4o, 2025-04-25, global, rolled back in four days.
- **Kept separate from F2** because the *cause* varied (reward-signal change at
  OpenAI, prompt edit at xAI) while the *output signature* was the same.
- **Regimes:** B0.
- **The purest case in the corpus for label-free detection.** OpenAI's own
  account: "offline evaluations — especially those testing behavior — generally
  looked good"; the A/B test said users liked it; testers who felt the model was
  "off" were overruled by positive signal; and "we didn't have specific
  deployment evaluations tracking sycophancy." Every labelled eval passed.

---

## Mechanism-evidenced classes

Real documented mechanisms on widely deployed software, but **no operator
post-mortem with a blast radius**. They stay in the taxonomy; the grading
appears in the paper, and their severity ladders come from our own harness or
from a controlled study rather than from the field.

### F10 — Input context truncation
- **Evidence:** B mechanism, zero incidents. ollama #8099 logs
  `truncating input prompt limit=2048 prompt=3858 keep=5 new=2048` below the
  user's eyeline; ollama #14259 (open) states users "attribute the behavior to
  model quality rather than truncation" — the single best sentence in the
  corpus for this project's premise.
- **Output symptom:** front-truncation drops the system prompt first, so it
  presents as **instruction loss** — format violations and persona loss — not as
  factual error.
- **Activation:** 100% of prompts over the limit, 0% under. The canonical
  input-conditional fault; cell-level labelling here is pure noise.

### F11 — Retrieval degradation
- **Evidence:** no operator post-mortem exists. The only retrieval post-mortem
  found (Pinecone 2023-03-01) is a deletion — 515 free-tier indexes, 19 with
  lost updates, **detected in 3 minutes** — i.e. a hard failure, not
  degradation.
- **Severity ladder from a controlled study** (arXiv 2606.28337, n=500):

  | Injected noise | Hit@k | EM | F1 |
  |---|---|---|---|
  | 0% | 0.711 | 0.421 | 0.548 |
  | **10%** | **0.711** | **0.421** | **0.548** |
  | 20% | 0.639 | 0.373 | 0.485 |
  | 30% | 0.561 | 0.339 | 0.442 |

  **10% corruption produced literally zero measurable change.** That is the
  published floor: if our harness injects 10% retrieval noise and the detector
  misses it, that is not a detector failure and must not be scored as one.

- **The top-k result is the strongest external support for black-box framing.**
  Moving top_k from 3 to 5 *improves* every retrieval metric (Hit@k 0.778 →
  0.834) while destroying 11.4 points of exact match (0.481 → 0.367, −24%
  relative). A retrieval-side monitor reports that change as an improvement.
  Only an output-side detector sees the regression.
- **Noise floor is configuration-dependent:** repeated seeded runs at 20% noise
  gave EM sigma 0.006 (chunk80/k2) to 0.014 (chunk140/k5), with broader regimes
  ~15% higher. The decoy arm must therefore be calibrated per cell, not globally
  — an independent arrival at MTH-015.
- **Embedding-model swap** is a documented mechanism (OpenAI's own notes:
  `text-embedding-3-*` vectors are incompatible with `ada-002`) with **no
  verified incident**. Put no number on it. Note also that ada-002 is itself
  non-deterministic across calls on identical text — even a frozen embedding
  model is a noise source.

### F12 — Output-side truncation
Split from F10 deliberately: the two bite **disjoint input sets**, so folding
them together would corrupt per-input activation labelling. F10 fires on
long-context inputs; F12 fires on long-*answer* inputs. Signature is a
mid-sentence stop, and `finish_reason: length` makes it trace-visible even when
the text does not obviously show it.

### F13 — Refusal / safety-filter drift
The system starts refusing inputs it used to answer, or the reverse. Documented
in Chen et al. (GPT-4 "became less willing to answer sensitive questions" in
June than March) but the percentages could not be verified from an accessible
source. **Documented but unquantified.** Trivially black-box visible — refusals
have a strong lexical signature — and cheap for the harness to inject.

### F14 — Prompt-template / token serialization mismatch
Model, prompt text and parameters unchanged; the serialization into tokens
changed. Double-BOS from `apply_chat_template` combined with
`add_special_tokens=True`; missing `eos_token` in `tokenizer_config.json`.
Grade B on mechanism (llama.cpp #5040, vllm #2012, #16081), nothing on blast
radius. Symptom is degraded coherence and **failure to stop** — the model
continues generating the user's turn — which is strongly black-box visible.

---

## Excluded, deliberately

Recorded so they are not rediscovered and quietly added.

| Candidate | Why excluded |
|---|---|
| **Decoding parameter change** (temperature, max_tokens) | **Zero documented instances** of a parameter edit causing a production regression. The only real case in the area is a compiler miscompilation of approximate top-k, which is F7. See BCH-002. |
| Retrieval ACL / permission drift | Black-box visible only to a detector that knows the requester's entitlements, which a domain-agnostic detector does not. The one available number (Gartner, 132 IT leaders, 40% delayed rollout) measures *caution*, not incidence. Reconsider only if the transfer matrix gains an enterprise cell. |
| Destructive agent action (Replit DB deletion) | Tool *misuse*, not tool breakage, and a safety question rather than a regression. Different problem. |
| Upstream tool with changed *semantics* (units, timezone, enum meaning); reranker swap; chunking-strategy change | Plausible, in every practitioner blog, and **no grade A/B source exists**. Excluding them is the honest choice given that this taxonomy's entire validity argument is that it is drawn from documented reality. |

---

## Two structural findings that motivate the study

**Status pages do not carry quality regressions. 0 of 118.** Reproducible:
`curl -s https://status.claude.com/history.rss | grep -c "<item>"` gives 25
incidents over ~40 days; the OpenAI equivalent gives 93 over ~90 days. None of
the 118 describes an output-quality regression — all are errors, latency,
availability, auth or billing. Anthropic's own month-long, up-to-16% quality
degradation was **never a status incident**; it surfaced only as an engineering
blog post after the fact. The industry does not under-report this fault class,
it has **no channel for it**.

Related: the AI Incident Database is indexed by *harm*, not by *regression* —
it records that a system did something bad, almost never that behaviour changed
relative to a prior version. Useful for F5 and F9, near-useless elsewhere.

**Detection latency is bimodal on loudness, not severity.** Hard failures: 3
minutes (Pinecone) to hours. Silent regressions: 4 days (sycophancy), 30 days
(Anthropic routing), 5 months (NYC MyCity), 10 months (LibreChat), 15 months
(Air Canada). **Not one silent regression in the corpus was caught by the
operator's own automated evaluation.** Every one was found by a human noticing,
or by someone running a ground-truth probe. That absence is the strongest
available motivation for the tool and belongs in the paper's opening.

---

## Amendment log

Append-only. Never edit a class above; amend here with a date and a reason.

- **2026-09-24** — Taxonomy frozen. 14 classes: F1–F9 incident-evidenced,
  F10–F14 mechanism-evidenced. Blast radius established as an independent axis
  (B0–B3) rather than a per-class attribute. Decoding-parameter change dropped
  for lack of any documented instance. Four classes added that were not in the
  original list of eight: F6 cache contamination, F7 numerical/serving-stack
  corruption, F8 sticky routing heterogeneity, F9 persona drift.
