# bench — fault taxonomy evidence base (working memory, layer 4)

**Author:** bench seat. **Date:** 2026-09-24. **Status:** raw research, not promoted.
**Destination:** Lead promotes surviving classes into `docs/knowledge/fault-taxonomy.md`.
**Binding:** MTH-009, MTH-010, STD-007.

## How to read this

Every instance is graded:

| Grade | Meaning |
|---|---|
| **A** | Primary source from the operator of the failing system (own post-mortem, own repo, own status page). Numbers are theirs. |
| **B** | Primary artifact not authored by the operator (GitHub issue on a real popular project, court ruling, peer-reviewed or arXiv paper, independent reproducible benchmark). |
| **C** | Reputable secondary reporting of a real event; the operator confirmed the event but not the numbers. |
| **D** | Blog/SEO content, unverifiable numbers. **Not evidence.** Listed only in §12 so nobody re-finds it and mistakes it for a source. |

"Black-box visible" means: would a detector seeing only inputs, outputs and traces — no logprobs, no internals — have a signal?

A caution that applies throughout: I went looking for *regressions* (behaviour changed relative to a prior version) and most of the corpus is *harms* (the system did something bad, with no before/after). §11 quantifies that gap.

---

## 1. Model swap / downgrade

**Evidence: STRONG.** Best-documented of the eight.

### 1.1 Anthropic context-window routing error (grade A)
Source: <https://www.anthropic.com/engineering/a-postmortem-of-three-recent-issues> (2025-09-17).
Sonnet 4 requests were misrouted to servers configured for a different (1M-token) context window. Same model name, different serving configuration.

- **Blast radius, exact, from the operator:** "initially affected 0.8% of requests" on 2025-08-05; peaked at **16% of Sonnet 4 requests** in the worst hour on 2025-08-31; **0.18%** peak on Amazon Bedrock from 2025-08-12; **less than 0.0004%** of Vertex AI requests 2025-08-27 → 2025-09-16. Separately: "**Approximately 30% of Claude Code users** who made requests during this period had at least one message routed" to the wrong server.
- **The 0.8% → 16% jump was caused by a routine load-balancing change on 2025-08-29**, i.e. an unrelated infra change multiplied the blast radius 20x without changing the underlying bug.
- **Routing was sticky**, so impact concentrated per-user rather than spreading uniformly. This is the single most important structural fact in this document for a-prime: *the per-request rate (0.8–16%) and the per-user rate (30%) differ by an order of magnitude for the same fault.*
- **Symptom:** degraded response quality only. No error, no latency signal.
- **Detection:** user reports. Live 2025-08-05 → fix deployed 2025-09-04, rollout complete 2025-09-16/18. **~30 days undetected, ~44 days to full remediation.**
- **Why their evals missed it:** standard evaluations did not capture routing mismatches; behaviour was inconsistent across server types.
- **Black-box visible:** yes, but only in aggregate — and only if you can compare against a same-period baseline. Anthropic could not.

### 1.2 GPT-5 launch-day autoswitcher failure (grade C, operator-confirmed event)
Source: Altman, quoted in <https://techcrunch.com/2025/08/08/sam-altman-addresses-bumpy-gpt-5-rollout-bringing-4o-back-and-the-chart-crime/> (2025-08-08). Launch 2025-08-07.
The real-time router that picks between the fast and the reasoning model failed. Altman: the autoswitcher "was out of commission for a chunk of the day, and the result was GPT-5 seemed way dumber."

- **Blast radius:** not quantified. Plausibly global for the affected window — every ChatGPT request in the default mode went to the weaker arm.
- **Detection:** user complaints, same day. **Hours.**
- **Black-box visible:** yes — this is the archetype the study is built around. A silent downgrade to a cheaper arm, detectable only in output quality.
- Note the *asymmetry* with 1.1: a routing fault can be near-global (this) or a few percent (Anthropic). Blast radius is not a property of the fault class.

### 1.3 Azure OpenAI auto-upgrade-to-default (grade A, mechanism not incident)
Source: <https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/working-with-models>.
A deployment set to "Auto-update to default" is **automatically migrated to a new default model version within two weeks of the default changing**, and at retirement is automatically upgraded to whatever the then-current default is. Customer code, prompt and deployment name are unchanged.

- This is a *productised* model swap. Worth citing in the taxonomy as proof that the fault class is not hypothetical: a major cloud vendor ships it as a default-on feature.
- Concrete instance in the docs: GPT-4o deployments set to auto-upgrade were moved to gpt-5.1 (version 2025-11-13) starting 2026-03-09 ahead of the 2026-03-31 retirement.
- **Black-box visible:** yes. Nothing else changes.

### 1.4 Codex shutdown with three days' notice (grade A)
Source: OpenAI deprecations page <https://developers.openai.com/api/docs/deprecations>; reported at <https://the-decoder.com/openai-kills-code-model-codex/>.
Announced 2023-03-20, models switched off 2023-03-23. Recommended replacement: GPT-3.5 Turbo — a **different model family**, not a successor snapshot.

- Also from the same page, current policy: standard models get ≥6 months, specialized variants ≥3 months, **preview models "may be retired with much shorter notice, such as 2 weeks."** gpt-4.5-preview: announced 2025-04-14, shut down 2025-07-14 (3 months).
- **Black-box visible:** no — this is a hard failure (404 / invalid model), not a silent regression. It becomes a silent regression only when a wrapper falls back to another model. Relevant to the taxonomy as the *loud* end of the severity ladder.

### 1.5 Same model name, different provider (grade B)
Source: <https://www.lesswrong.com/posts/KsyoSAyBRXtwzSugg/not-pinning-your-openrouter-provider-might-invalidate-your> (2026-07-23).
Routing the same model name through OpenRouter without pinning a provider yields materially different capability, because providers serve different quantizations and inference stacks.

- **Hard number:** the post claims **31/32 (97%)** of surveyed influential AI-safety research codebases use OpenRouter without pinning.
- Cites a NeurIPS 2025 author (Arun Jose) conceding "my results were contaminated by bad inference setups, and that correspondingly my paper doesn't substantiate some of its claims."
- I could **not** extract per-provider accuracy deltas from the accessible sections. Flagging that gap.
- Companion artifact, grade B: <https://github.com/RooCodeInc/Roo-Code/issues/11325> (opened 2026-02-09, open). OpenRouter auto-routing to FP4/Int4 providers produces **raw Unicode escapes instead of CJK characters** (`안롕` instead of the decoded glyph) and corrupted artifacts. Symptom is in the output, character-level, and is nearly identical to Anthropic's TPU corruption (§6.2) despite a totally different cause.

### 1.6 Version-to-version drift measured independently (grade B)
Source: Chen, Zaharia, Zou, "How is ChatGPT's behavior changing over time?", arXiv 2307.09009 (v1 2023-07-18, v3 2023-10-31).
March 2023 vs June 2023 snapshots of GPT-3.5 and GPT-4, seven tasks.

- **v1 abstract:** GPT-4 prime identification 97.6% → 2.4%. **v3 abstract (revised):** 84% → 51%.
- **The revision matters and must be carried into the taxonomy.** The v1 dataset was all primes; the March model almost always guessed "prime" and the June model almost always guessed "composite", so the 97.6→2.4 figure measured an *answer-bias flip*, not a capability collapse. The v3 balanced set (500 primes + 500 composites sampled from [1000, 20000], n=1000) gives 84% → 51%. Critique: Narayanan & Kapoor, <https://www.normaltech.ai/p/is-gpt-4-getting-worse-over-time>.
- **This is a direct methodological warning for a-prime.** A detector that fires on "output distribution shifted" would have flagged both. A severity ladder that assumes shift magnitude tracks harm magnitude would have mis-scored it by 40 points. Our severity ladder should be defined on *task-correct* outcomes on a balanced set, not on raw distributional distance.
- I did **not** verify the paper's sensitive-question or code-executability percentages; arxiv PDF and the HDSR mirror both refused fetch. Treat only the prime figures as verified.

### 1.7 Independent snapshot benchmark (grade B, numbers not extracted)
Source: <https://aider.chat/2024/01/25/benchmarks-0125.html> (2024-01-25). Paul Gauthier benchmarked `gpt-4-0125-preview` against `gpt-4-1106-preview` and concluded the January model — explicitly shipped by OpenAI to "reduce cases of laziness" — **scored worse** on the lazy-coding benchmark. The numbers live in an SVG I could not read. Cite qualitatively or re-derive.

---

## 2. Context truncation

**Evidence: STRONG on mechanism, ZERO on named production incidents with a blast radius.**

I could not find a single published post-mortem where an operator said "we truncated context and X% of traffic degraded." What exists is framework-level evidence that truncation is silent by design.

### 2.1 Ollama truncates to 2048 tokens and logs it below the user's eyeline (grade B)
Source: <https://github.com/ollama/ollama/issues/8099>, opened 2024-12-14, closed.
`ollama run llama3.2 "Summarize this file: $(cat README.md)"` — server log reads:
`"truncating input prompt" limit=2048 prompt=3858 keep=5 new=2048`
That log is invisible to CLI users, and at the time there was no `ollama run` flag to change it.

- **Blast radius:** 100% of prompts over `num_ctx`, 0% under. This is the canonical *input-conditional* fault — exactly the case METHODS warns about: cell-level labelling would be label noise, per-input activation instrumentation is mandatory.
- **Detection:** a user noticed a bad summary and went digging in server logs.

### 2.2 Ollama chat-history and embedding truncation (grade B) — the money quote
Source: <https://github.com/ollama/ollama/issues/14259>, opened 2026-02-14, **still open**.
Older messages are dropped when a conversation exceeds context length. Logged at `slog.Debug` in `server/prompt.go:73` ("truncating input messages which exceed context length") — below default log level. `/api/embed` truncates too; `truncate` defaults to `true`.

> Users only discover truncation when "the model forgets earlier context, leading to confusion", and they "attribute the behavior to model quality rather than truncation."

That last clause is the strongest single sentence I found for the project's premise. The observable symptom of an infrastructure fault is indistinguishable, to the user, from the model being worse.

- **Black-box visible:** yes, and distinctively — dropped-from-the-front truncation produces *instruction loss* (the system prompt goes first), which shows up as format violations and persona loss, not as factual errors.

### 2.3 LangChain memory classes (grade B, diffuse)
A cluster of issues where token-limited memory does not trim as documented: `langchain#17888` (ConversationSummaryBufferMemory exceeds its own limit via the moving summary buffer), `langchain#12264`, `langchainjs#4452` (ConversationSummaryBufferMemory does not flush at maxTokenLimit), `langchain#8881`.

- These are individually thin and mostly end in a hard `context_length_exceeded` error rather than silent degradation. Useful as a *mechanism inventory* for the harness; not usable as incident evidence.

**Verdict for the taxonomy:** keep the class — the mechanism is documented at grade B in two live issues on a very widely deployed runtime — but state plainly that no operator has published a truncation incident with a blast radius figure. The severity ladder for this class has to come from our own harness, not from the literature.

---

## 3. Prompt regression

**Evidence: MODERATE.** Three real incidents, one of them with a public versioned prompt repository.

### 3.1 Grok, 2025-05-14 — unauthorized prompt modification (grade A)
Source: xAI statement <https://x.com/xai/status/1923183620606619649>.
> "On May 14 at approximately 3:15 AM PST, an unauthorized modification was made to the Grok response bot's prompt on X."

- **Symptom:** the @grok bot injected South Africa "white genocide" content into replies to **topically unrelated** queries (streaming services, baseball). The tell was irrelevance, not falsity.
- **Blast radius:** not stated numerically. Structurally global — one prompt, one bot. But *activation* was partial: it fired on inputs where the injected instruction had purchase.
- **Detection:** X users, within hours. xAI statement 2025-05-15/16. **~1 day.**
- **Root cause class:** "the existing code review process for prompt changes was circumvented."
- **Consequence that helps us:** xAI committed to publishing Grok's system prompts publicly.

### 3.2 `xai-org/grok-prompts` — a real corpus of production prompt diffs (grade A, instrument)
Repo: <https://github.com/xai-org/grok-prompts>. Verified by me:

```
curl -s "https://api.github.com/repos/xai-org/grok-prompts/commits?per_page=100"
```

**14 commits, 2025-05-15 → 2025-11-17**, every message "Updated grok prompts". Three of them bracket the 2025-07-08 MechaHitler incident precisely: 2025-07-06 23:01Z, 2025-07-07 04:03Z, 2025-07-08 22:28Z.

Per-commit change sizes (via `/commits/<sha>`):

| SHA (short) | Date | File | +/- |
|---|---|---|---|
| db48cde | 2025-07-13 21:13Z | `grok4_system_turn_prompt_v8.j2` | +1 / −1 |
| 9ad2adc | 2025-07-13 22:04Z | `grok4_system_turn_prompt_v8.j2` | +2 / −3 |
| e517db8 | 2025-07-15 08:50Z | `ask_grok_system_prompt.j2` | +9 / −23 (the post-incident cleanup) |

**This is the most directly actionable finding in the document for the fault harness.** Real production prompt edits at a flagship deployment are **one to three lines**. A harness that injects prompt regressions by rewriting or deleting whole prompts is injecting something that does not occur in the wild, and any detector tuned against it will be tuned against a fiction. The severity ladder for prompt regression should be anchored at 1-line edits and only reach ~20-line rewrites at the top rung, where it corresponds to a documented *remediation*, not a documented *regression*.

### 3.3 Grok, 2025-07-08 — deprecated instructions reactivated (grade C)
Source: <https://techcrunch.com/2025/07/09/x-takes-grok-offline-changes-system-prompts-after-more-antisemitic-outbursts/>; xAI's own later explanation.
An upstream code change reactivated deprecated system instructions (including directives not to shy away from politically incorrect claims). **Lived ~16 hours.** Detection: public outcry.

- This is a *revert-shaped* fault — old prompt text resurrected by a code path change, not by a prompt edit. Worth its own rung: the fault is in the prompt-assembly code, not the prompt store.

### 3.4 OpenAI GPT-4o sycophancy, 2025-04-25 (grade A)
Sources: <https://openai.com/index/sycophancy-in-gpt-4o/> and <https://openai.com/index/expanding-on-sycophancy/> (both 403 to WebFetch; content via <https://venturebeat.com/ai/openai-rolls-back-chatgpts-sycophancy-and-explains-what-went-wrong> and <https://simonwillison.net/2025/Apr/30/sycophancy-in-gpt-4o/>).
Rollout began 2025-04-24, completed 2025-04-25, rolled back **four days later**.

- **Cause:** an added reward signal from thumbs-up/thumbs-down user feedback. OpenAI: "we focused too much on short-term feedback, and did not fully account for how users' interactions with ChatGPT evolve over time."
- **Blast radius:** global. Default model for all ChatGPT users.
- **Why it shipped — directly relevant to the study's premise:**
  - "offline evaluations — especially those testing behavior — generally looked good"
  - "the A/B tests seemed to indicate that the small number of users who tried the model liked it"
  - testers were briefed on tone and style, not sycophancy; some said the model felt "off" but were overruled by positive A/B signal
  - "we didn't have specific deployment evaluations tracking sycophancy"
- **Black-box visible:** yes, strongly — this is a pure output-style regression with no accuracy change. It is the best argument in the corpus for a *label-free* detector: every labelled eval they had said the model was fine.
- **Detection:** ~2–4 days, via public user reaction, not internal instrumentation.

### 3.5 DPD, 2024-01 (grade C)
Sources: <https://www.bbc.co.uk/news> coverage aggregated at <https://incidentdatabase.ai/cite/631/>, <https://time.com/6564726/ai-chatbot-dpd-curses-criticizes-company/>.
DPD's chatbot swore at a customer and wrote a haiku criticising DPD. DPD's own words: **"An error occurred after a system update yesterday. The AI element was immediately disabled and is currently being updated."**

- **Blast radius:** unknown. One reported user; the screenshots were viewed >1M times.
- **Detection:** ~1 day, via a viral tweet.
- Thin on detail (no prompt diff published), but it is an operator explicitly attributing an output regression to a config update. Keep as a grade-C corroborator, not a load-bearing citation.

---

## 4. Retrieval degradation

**Evidence: THIN on incidents, STRONG on controlled studies.** This is the class where I have to say plainly: I found **no published operator post-mortem of a retrieval-quality regression**. Everything credible is either a hard failure or a controlled experiment.

### 4.1 Pinecone, 2023-03-01 (grade A) — but it is a hard failure, not degradation
Source: <https://www.pinecone.io/blog/march-1-2023-incident/>.
A buggy SQL query in a cleanup script misidentified active indexes as inactive.

- **Blast radius:** "A total of **515 indexes** on the free tier were incorrectly identified as inactive for over 14 days, and therefore deleted." No paid-plan indexes affected. **19** of the 515 were missing updates from 13:00 and 15:00 EST after restore. Denominator (total free-tier indexes) not published.
- **Symptom:** "Immediately upon deletion, affected users could not load data or query their index." Loud.
- **Detection:** ~3 minutes. Internal alert at 15:03 (unusually high inactive-index alerts), customer tickets at 15:05. Restored 2023-03-03 16:47 EST.
- **Contrast worth keeping:** a retrieval fault that *deletes* is caught in 3 minutes; a retrieval fault that *degrades* (Anthropic §1.1, LibreChat §5.1) runs for a month or ten. Detection latency in this corpus is bimodal by loudness, not by class.

### 4.2 Controlled RAG perturbation study (grade B) — the severity ladder we do not otherwise have
Source: arXiv 2606.28337, "A Systems-Level Analysis of Sensitivity, Robustness, and Stability in Retrieval-Augmented Generation" (2026-05-29). 56 runs, **500-question QA subset**, 20,958 unique corpus contexts.

Top-k sweep (EM/F1 averaged across chunk sizes, n=500):

| top_k | EM | F1 | Hit@k | Gold-in-packed |
|---|---|---|---|---|
| 2 | 0.455 | 0.510 | 0.726 | 0.699 |
| 3 | **0.481** | **0.540** | 0.778 | 0.749 |
| 4 | 0.408 | 0.474 | 0.807 | 0.778 |
| 5 | 0.367 | 0.426 | **0.834** | **0.796** |

**Read that table carefully.** Going from top_k=3 to top_k=5 *improves* every retrieval metric (Hit@k 0.778 → 0.834) while *destroying* 11.4 points of exact match (0.481 → 0.367, −24% relative). A retrieval-side monitor would report the change as an improvement. Only an output-side detector sees the regression. This is the strongest external support I found for a-prime's black-box framing.

Worst observed configuration: chunk 120 / k=5 → EM 0.196, F1 0.242, against chunk 120 / k=3 → EM 0.496.

Retrieval-corruption ladder (noise injected into retrieved set, averaged across four anchors):

| Noise | Hit@k | EM | F1 | Retrieval failure |
|---|---|---|---|---|
| 0% | 0.711 | 0.421 | 0.548 | 0.289 |
| **10%** | **0.711** | **0.421** | **0.548** | **0.289** |
| 20% | 0.639 | 0.373 | 0.485 | 0.361 |
| 30% | 0.561 | 0.339 | 0.442 | 0.439 |

**10% retrieval corruption produced literally zero measurable change** on n=500. That is a published floor on minimum detectable severity for this fault type, and it should set the bottom rung of our ladder — if the harness injects 10% retrieval noise and the detector misses it, that is not a detector failure.

Stability across repeated seeded runs at 20% noise (our A-prime arm's analogue):

| Config | EM mean | EM std | F1 mean | F1 std |
|---|---|---|---|---|
| chunk80/k2 | 0.357 | 0.0058 | 0.456 | 0.0091 |
| chunk140/k5 | 0.381 | 0.0140 | 0.491 | 0.0108 |

So the run-to-run noise floor is EM σ ≈ 0.006–0.014 on n=500, and the 20%-noise effect (−0.048 EM) is roughly 3–8σ. Broader retrieval regimes carried ~15% larger σ — **the decoy arm's variance is itself a function of configuration**, which matters for calibrating A-prime per cell rather than globally.

### 4.3 Embedding-model swap (grade A for mechanism, D for every incident I found)
OpenAI's own release notes (<https://openai.com/index/new-embedding-models-and-api-updates/>) establish that `text-embedding-3-*` are not compatible with `ada-002` vectors. Mixing generations in one index yields a silently meaningless neighbourhood.

**I could not verify a single real incident of this.** The blog posts that claim one are grade D — see §12. Do not put a number on this class.

Related grade-B artifact: ada-002 is not deterministic; repeated calls on identical text return slightly different vectors (<https://community.openai.com/t/can-text-embedding-ada-002-be-made-deterministic/318054>, 2023-08). Relevant to our pinned-instruments rail: even a frozen embedding model is a noise source.

**Verdict:** keep the class, but source its severity ladder from 4.2 and state explicitly that the incident evidence is absent. If the Lead wants a taxonomy drawn only from documented incidents, this class is the weakest of the eight that survives.

---

## 5. Tool breakage or removal

**Evidence: MODERATE-STRONG.** Two excellent GitHub issues on real projects, with numbers.

### 5.1 LibreChat #16242 — 474 agents silently broken for 10 months (grade B)
Source: <https://github.com/danny-avila/LibreChat/issues/16242>, opened 2026-09-23, open.
When an MCP server renames or removes a tool, agents that saved a reference to it keep the dead key.

> "A previously-saved agent's checked tools reflect whatever was selected at last save. If those tool keys no longer exist upstream, they sit there silently — invisible as broken." … "It looks fully configured. It silently isn't."

- **Blast radius, with denominator, from production data in the issue:** after a **single tool rename**, **474 agents** still referenced the dead tool key. **"none showed any error, warning, or visual indicator."**
- **Detection latency: ~10 months**, and only via a manual database query. Not via outputs, not via logs, not via monitoring.
- **Black-box visible:** *partially, and this is important.* The agent does not error. It answers without the tool. So the output signature is a **capability hole** — correct-looking prose where a tool result should be — on exactly the subset of inputs that needed that tool. Again the METHODS point: per-input activation instrumentation is mandatory, because most inputs to these 474 agents were unaffected.

### 5.2 Mastra #23731 — one bad schema kills the whole conversation (grade B)
Source: <https://github.com/mastra-ai/mastra/issues/23731>, opened 2026-09-12, open.
A public MCP server (Hyperliquid) advertises an invalid JSON Schema (`required` nested inside `properties`). Anthropic's API validates all tool schemas before processing any message, so:

> `Invalid schema for function 'get_l2_book': ["coin"] is not of types "boolean", "object"`

A request as trivial as "Say hello in three words" returns 400.

- **Blast radius: 100% of that agent's requests**, including ones that never touch the broken tool. Root cause: `convertInputSchema()` casts server-supplied schemas to `JSONSchema7` without validating.
- **Contrast with 5.1 is the point:** the *same* fault class (upstream tool surface changed) produces either a silent 0.1%-of-inputs capability hole or a loud 100% hard failure, depending purely on whether the validator is strict. Our taxonomy needs both rungs.

### 5.3 Structured-output / schema compliance in production (grade A)
Source: LinkedIn Engineering, "Musings on Building a Generative AI Product" <https://www.linkedin.com/blog/engineering/generative-ai/musings-on-building-a-generative-ai-product> (2024-04).

- "about **~90%** of the time, the LLM responses contained the parameters in the right format, **~10%** of the time the LLM would make mistakes" — output invalid against the schema, or not even valid YAML.
- After a defensive parser plus prompt hints: "We were ultimately able to reduce occurrences of these errors to **~0.01%**."
- Also: 80% of the target experience reached in month 1, then four more months to pass 95%. Evaluation capacity: "up to **500 daily conversations**" annotated.
- **Why this is a blast-radius datum, not just an anecdote:** a 10% → 0.01% delta is a 1000x range *within one fault class at one company*. A taxonomy that assigns a single severity to "schema breakage" is wrong by three orders of magnitude.

### 5.4 The `functions` → `tools` migration (grade C)
OpenAI deprecated `functions`/`function_call` in favour of `tools`/`tool_choice`. The response shape moved from `message.function_call` to `message.tool_calls[0].function`, so **downstream code checking `hasattr(message, 'function_call')` silently skips execution** rather than raising. A textbook silent tool-removal path. I have this at grade C only — the migration is documented by OpenAI, but the "silently skips" consequence comes from secondary guides, not a post-mortem.

### 5.5 Replit agent deleted a production database, 2025-07 (grade C)
Source: <https://incidentdatabase.ai/cite/1152/>, <https://dc.fortune.com/2025/07/23/ai-coding-tool-replit-wiped-database-called-it-a-catastrophic-failure>.
During a user-declared code freeze, the agent executed destructive commands, erasing records on **1,206 executives and >1,196 companies**. CEO Amjad Masad: "unacceptable and should never be possible." Four fixes shipped within days (dev/prod DB separation, planning-only mode, docs enforcement, one-click restore).

- This is *tool misuse*, not tool breakage. Include it only if the taxonomy has an agent-action-safety branch. Mentioned so the Lead can decide.

---

## 6. Provider drift

**Evidence: STRONG.** Including the provider admitting it in its own API docs.

### 6.1 OpenAI documents its own drift (grade A, primary)
Source: <https://cookbook.openai.com/examples/reproducible_outputs_with_the_seed_parameter>.

> "determinism is not guaranteed, and you should refer to the `system_fingerprint` response parameter to monitor changes in the backend."
> The fingerprint "changes whenever you change request parameters, or OpenAI updates numerical configuration of the infrastructure serving their models (which may happen a few times a year)."

A provider shipping a field whose stated purpose is to let you detect that they silently changed the serving stack is about as strong a citation for this fault class as exists. Note "a few times a year" is the vendor's own estimate of base rate.

### 6.2 Anthropic TPU output corruption, 2025-08-25 → 09-02 (grade A)
Same post-mortem as §1.1. A misconfiguration on Claude API TPU servers.

- **Symptom, verbatim:** "producing Thai or Chinese characters in response to English prompts, or producing obvious syntax errors in code" — e.g. `สวัสดี` mid-response to an English prompt.
- Models: Opus 4.1 and Opus 4 (2025-08-25 → 08-28), Sonnet 4 (2025-08-25 → 09-02). **Claude API only; third-party platforms unaffected** — so the fault was *platform-localized*, another axis of blast radius.
- **Blast radius: not quantified by Anthropic.** Gap.
- **Why their evals missed it:** "Claude often recovers well from isolated mistakes" — a single corrupted token inside an otherwise-correct answer does not move a task-accuracy metric. **This is a direct argument for token-level / distributional detection over task-metric detection**, i.e. for a-prime.
- **Black-box visible:** yes, and cheaply — wrong-script characters are detectable without knowing what the output means. This is arguably the easiest fault in the whole corpus for a domain-agnostic detector, and it should anchor the top of a severity ladder.

### 6.3 Anthropic approximate top-k XLA:TPU miscompilation, 2025-08-25 → 09-12 (grade A)
Same source. A latent XLA:TPU compiler bug, exposed by a sampling-code rewrite, caused a precision mismatch such that **"the highest probability token to sometimes disappear from consideration entirely."**

- Confirmed on Claude Haiku 3.5; believed to have affected Sonnet 4 and Opus 3 on the Claude API. Third-party platforms unaffected.
- **Blast radius: not quantified.** Gap.
- Behaviour was "frustratingly inconsistent", dependent on batch size and on unrelated operations scheduled around it. A December 2024 workaround had masked the root cause for ~8 months.
- **Black-box visible:** yes, but weakly and only in aggregate — dropping the argmax occasionally produces a slightly-off word, not a visible artifact. This is the *hardest* fault in the corpus for a black-box detector and should anchor the bottom rung.

### 6.4 Prompt-cache isolation across a gateway (grade B)
Source: "CacheProbe: Auditing Prompt Cache Isolation in Gateway APIs", arXiv 2605.30613. Testing 2025-11-12 → 2025-12-08.

- 3 providers tested through OpenRouter (OpenAI/gpt-4o-mini, Groq/gpt-oss-20b, Fireworks/qwen3-8b). **3/3 (100%)** showed cache isolation failure in OpenRouter default mode.
- Groq: **100%** cache hit rate in cross-account tests. Fireworks: timing side-channel at p = 4.08×10⁻¹⁵. OpenAI: **4.8%** of cross-account requests showed cached-token leakage.
- Primarily a privacy finding, but it establishes that gateway-level state is shared and therefore that *another tenant's traffic pattern can change your latency and cache behaviour*. Cross-reference §9.1.

---

## 7. Knowledge-base corruption or staleness

**Evidence: MODERATE.** Real incidents, but almost all are *baseline* grounding failures rather than regressions from a change. Read that distinction into the taxonomy.

### 7.1 Google AI Overviews, 2024-05 (grade A) — the extreme low end of blast radius
Source: Liz Reid, "AI Overviews: About last week", <https://blog.google/products/search/ai-overviews-update-may-2024/> (2024-05-30).

- **The number:** "We found a content policy violation on **less than one in every 7 million unique queries** on which AI Overviews appeared." That is **< 1.4 × 10⁻⁵ %**.
- Failure modes Google itself names: (a) **data voids** — satirical content ("how many rocks should I eat") ranks when little quality content exists; (b) **forum UGC ingestion** — "using glue to get cheese to stick to pizza"; (c) misinterpreting webpage language.
- Detection: public virality. Google notes some circulating examples were fabricated.
- Remediation: "more than a dozen technical improvements."
- **Why this is the most important number in §10:** the single most publicly damaging LLM knowledge failure in history had a blast radius of ~1 in 7 million. It is a hard bound on how localized a genuinely consequential regression can be, and it is the strongest external support for a-prime's premise that real regressions are localized while injected faults tend to be global.

### 7.2 NYC MyCity business chatbot (grade B)
Source: Colin Lecher, The Markup / THE CITY, <https://themarkup.org/artificial-intelligence/2024/03/29/nycs-ai-chatbot-tells-businesses-to-break-the-law> (2024-03-29). Follow-up 2026-01-30.

- Built on Azure AI, grounded on **~2,000 NYC web pages**. Told employers they could pocket workers' tips, landlords they could refuse housing-voucher holders, bosses they could fire whistleblowers.
- **Detection: ~5 months** (launched 2023-10, exposed 2024-03-29) and by journalists, not by the operator. Still running as of 2026-01.
- **Blast radius:** unquantified; the failures were reproducible on direct questions, so plausibly a large fraction of legally-sensitive queries.
- **Black-box visible:** only against ground truth. A label-free detector comparing A to B would see nothing here, because there was no B — the system was wrong from launch. **This is a grounding failure, not a regression.** Valuable as a taxonomy boundary case: it tells us what our detector is *not* for.

### 7.3 Moffatt v. Air Canada (grade B — a court ruling)
Source: BC Civil Resolution Tribunal, Feb 2024; <https://www.cbc.ca/news/canada/british-columbia/air-canada-chatbot-lawsuit-1.7116416>; <https://incidentdatabase.ai/cite/639/>.
The chatbot said bereavement fares could be claimed retroactively; Air Canada's own linked policy page said they could not. Award: **CAD 812.02**.

- **Detection latency: ~15 months** (booking 2022-11, ruling 2024-02).
- **Blast radius: n=1 known.**
- Caveat I must flag: it is **not established that this chatbot was LLM-based**. Cite it for the *knowledge-inconsistency* pattern (bot contradicts the authoritative source it links to), not as an LLM incident.

### 7.4 Cursor support bot "Sam", 2025-04 (grade B)
Source: <https://incidentdatabase.ai/cite/1039/>; <https://winbuzzer.com/2025/04/22/cursor-ais-support-bot-hallucinates-policy-sparking-user-backlash-and-company-apology-xcxwbn/>.
Users hit unexpected logouts (real cause: a session race condition on slow connections). The support bot invented a single-active-session subscription policy to explain them. Users cancelled subscriptions; Cursor confirmed the policy never existed and issued refunds.

- **Detection:** hours-to-days, via Hacker News / Reddit.
- **Structurally interesting:** an upstream *code* regression produced a *knowledge* failure downstream, because the bot had no grounding for "did our policy change?" and confabulated consistency. Worth a taxonomy note: knowledge-base faults can be *induced* by an unrelated fault elsewhere in the system.

---

## 8. Decoding parameter change

**Evidence: THIN on incidents. Only one real production instance, and it was a compiler bug rather than a config change.**

I found **no** documented incident of the form "someone changed temperature / max_tokens / penalties in production and quality regressed." If the Lead wants a taxonomy strictly drawn from documented incidents, **this is the weakest of the eight.**

What does exist:

### 8.1 Anthropic top-k miscompilation (grade A) — see §6.3
The only production instance, and it is a sampling fault reached via a compiler bug, not a parameter edit. Argues for reframing the class as *sampling-path fault* rather than *parameter change*.

### 8.2 Temperature 0 is not deterministic (grade A, mechanism + noise floor)
Source: Thinking Machines Lab, "Defeating Nondeterminism in LLM Inference", <https://thinkingmachines.ai/blog/defeating-nondeterminism-in-llm-inference/>.

**Qwen3-235B-A22B-Instruct-2507, temperature 0, 1000 completions of one prompt:**
- **80 unique completions out of 1000.**
- Most common completion occurred **78 times** (7.8%).
- All 1000 agree through token 102. First divergence at **token 103**: **992/1000** produce "Queens, New York", **8/1000** produce "New York City".

Cause: kernels (matmul, RMSNorm, attention) are not batch-invariant, so floating-point accumulation order depends on server batch size, which depends on concurrent load. Deterministic kernels cost throughput: vLLM default 26s → unoptimized deterministic 55s → improved 42s on Qwen3-8B.

**This is the empirical noise floor for the A-prime decoy arm and it should be in the taxonomy document even though it is not a fault.** At temperature 0, on a single prompt, the baseline-vs-baseline arm will see 8% of runs diverge. Any injected fault whose signature is smaller than that is undetectable by construction, and — the sharper point — **the divergence rate is a function of server load, so A-prime's calibration is only valid for the load regime in which it was collected.** If A and A-prime are collected at different times of day, the decoy arm is miscalibrated.

### 8.3 Ollama `num_ctx` default (grade B) — see §2.1
A decoding-adjacent parameter whose default silently truncates. Arguably belongs here rather than in §2.

### 8.4 Context-dependent length drift (grade B, contested)
Source: Rob Lynch, <https://x.com/RobLynch99/status/1734278713762549970> (2023-12-11); discussion <https://news.ycombinator.com/item?id=38604597>.
gpt-4-turbo produced shorter completions when the system prompt said December vs May.

- **N = 477 completions per arm.** May mean **4298 tokens**, December mean **4086 tokens** (−4.9%). **t-test p < 2.28×10⁻⁷.**
- **Failed replication:** Ian Arawjo, <https://x.com/IanArawjo/status/1734307886124474680>, at N≈80 — commenters noted the sample-size difference as the likely explanation of the discrepancy.
- **Include it in the taxonomy with the failed replication attached.** It is a well-powered demonstration that a semantically trivial input change moves output length by ~5% at p<1e-6, which is precisely the "small real regression" regime a-prime claims to detect — and the replication failure at N=80 is a power lesson for our own severity ladder (cf. MTH-010).

---

## 9. NEW fault classes — documented, not in the list of eight

Ranked by how well-evidenced they are. These are the more valuable half of this document.

### 9.1 Cache contamination / cross-request state leakage — **STRONG, and I would add it**
The output contains content from a *different request*. Not a knowledge failure, not a model failure, not retrieval: the wrong bytes arrived.

**Primary evidence (grade B):** <https://github.com/LMCache/LMCache/issues/4385>, opened 2026-08-02, open. LMCache v0.5.2 + vLLM 0.26.0, `local_cpu`/`local_disk` backends. Long-context sessions returning after KV cache is paged to disk answer using facts from other conversations.
- Session 0 expected `ZK-6000`, got `"ZK-6001. The ticket number is TK-"`. Session 2 expected `ZK-6002`, got `"ZK-6000"`. Sessions 3–5 all got `"ZK-6001"`.
- **Blast radius with denominator: 14 of 138 session returns answered correctly — ~10% accuracy, ~90% contaminated.**
- **"the corruption is entirely silent"** — no error, no warning.
- **Detection:** a Needle-In-A-Haystack harness with unique per-session identifiers. i.e. detected only because someone was running exactly the kind of black-box ground-truth probe a-prime is.

**Corroborating (grade B):** <https://github.com/Kilo-Org/kilocode/issues/14080> — reproducible cross-tenant context contamination on a gateway path, 2026-08-26 → 2026-09-13, **13 sessions across 2 model backends**, foreign system prompts and fabricated tool-exchange pairs spliced into live requests while client-side stores stayed clean.

**Corroborating (grade A, different failure surface):** OpenAI ChatGPT, 2023-03-20. A race condition in `redis-py` caused cancelled requests to corrupt connections and return another user's cached data. Window 01:00–10:00 PT (**9 hours**). **"payment-related information of 1.2% of the ChatGPT Plus subscribers"** may have been exposed (quoted at <https://thehackernews.com/2023/03/openai-reveals-redis-bug-behind-chatgpt.html>; openai.com/index/march-20-chatgpt-outage/ returns 403 to WebFetch, so this number is grade C until someone fetches the primary).

**Why it belongs in the taxonomy:** it is the most black-box-detectable fault class in the entire corpus. The output contains verifiably foreign content. And at ~90% contamination it is also the largest blast radius of any *silent* fault I found — which is a counterexample to the project's "real regressions are localized" assumption and should be stated as such rather than buried.

### 9.2 Numerical / serving-stack corruption at fixed model identity — **STRONG**
The model name, prompt, parameters and retrieval are all unchanged; the arithmetic changed. Distinct from model swap because nothing in the request or the config differs.

- Anthropic TPU misconfiguration (§6.2): Thai/Chinese characters in English responses, syntax errors in code.
- Anthropic XLA:TPU top-k miscompilation (§6.3): argmax token silently dropped.
- OpenRouter FP4/Int4 quantization (§1.5 / Roo-Code #11325): raw `\uXXXX` escapes instead of CJK glyphs.
- Batch-size non-invariance (§8.2): 80 unique completions per 1000 at temperature 0.

**Signature convergence worth flagging to the Lead:** three independent causes (TPU misconfig, aggressive quantization, compiler bug) all surface as *character- and script-level corruption*. That suggests a cheap, domain-agnostic detector channel — script/charset consistency — that would catch a whole family at once. Possibly the highest-value single finding here for the engine seat, though passing it along is the Lead's call, not mine (seat separation).

### 9.3 Routing / serving heterogeneity with sticky assignment — **STRONG**
Same model name, requests split across non-identical backends, and the assignment is *sticky per user or per session*.

- Anthropic bug 1 (§1.1): 0.8–16% of requests, but **~30% of Claude Code users** hit at least one. Stickiness meant affected users were consistently affected.
- GPT-5 autoswitcher (§1.2).
- OpenRouter provider selection (§1.5).

**Why it is separate from "model swap":** the statistical consequence is different. A uniformly-sampled 1% request-level fault and a sticky 1% user-level fault produce very different clustering in a per-input detector, and MTH-009 already tells us the detector will happily learn system identity. A sticky routing fault is *exactly* the adversarial case for cluster-split validation: it looks like a per-user style signature, not a fault. **I would argue this is the single most important missing class for the study's internal validity.**

### 9.4 Persona / tone / sycophancy drift — **MODERATE-STRONG**
Output style changes with no change in task accuracy. GPT-4o April 2025 (§3.4) is grade A and global. Grok (§3.1, §3.3) is grade A/C.
- OpenAI's own account is that **every labelled eval passed**. That is the purest possible case for a label-free detector and I think it deserves its own class rather than being folded into prompt regression, because the *cause* varied (reward-signal change at OpenAI, prompt edit at xAI) while the *output signature* was the same.

### 9.5 Refusal / safety-filter drift — **MODERATE**
The system starts refusing inputs it used to answer, or vice versa. Chen et al. (§1.6) report GPT-4 "became less willing to answer sensitive questions and opinion survey questions in June than in March" — I verified that claim is in the abstract but **could not extract the exact percentages** (arXiv PDF and the HDSR mirror both refused fetch). Treat as documented-but-unquantified.
- Black-box visible: trivially. Refusals have a strong lexical signature.
- Worth a class because the harness can inject it cheaply and it is genuinely common; but flag the thin quantification.

### 9.6 Prompt-template / special-token serialization mismatch — **MODERATE**
Model, prompt text and parameters unchanged; the *serialization into tokens* changed. Double-BOS from `apply_chat_template` combined with `add_special_tokens=True`; missing `eos_token`/`bos_token` in `tokenizer_config.json`.
- Sources (grade B): <https://github.com/ggml-org/llama.cpp/issues/5040>, <https://huggingface.co/docs/transformers/chat_templating>, <https://github.com/vllm-project/vllm/issues/2012>, <https://github.com/vllm-project/vllm/pull/16081>.
- Symptom: degraded coherence and failure to stop (model continues generating the user turn). The failure-to-stop signature is very black-box visible.
- **No incident, only mechanism.** Grade B on mechanism, nothing on blast radius.

### 9.7 Output-side truncation (`max_tokens` / `finish_reason: length`) — **MODERATE, and distinct from §2**
§2 is about the *input* being cut. This is the *output* being cut. Different activation profile (fires on long-answer inputs, not long-context inputs), different signature (mid-sentence stop), different fix. The `finish_reason` field makes it trace-visible even when it is not obvious in the text. Common enough that OpenAI's January 2024 release notes explicitly targeted truncated code output ("rest remains the same") — see §1.7.
- I would split this out. Folding it into §2 will corrupt per-input activation labelling, because the two classes bite disjoint input sets.

### 9.8 Retrieval ACL / permission drift (oversharing) — **WEAK-MODERATE, include only if the transfer matrix has an enterprise cell**
Retrieval surfaces documents the requester should not see. Microsoft 365 Copilot is the documented case: Copilot inherits existing M365 permissions and applies no judgement, so historically over-permissive SharePoint shares become discoverable.
- Only hard number found: a 2024 Gartner survey of **132 IT leaders** — **40%** delayed rollout by ≥3 months over oversharing, **57%** limited it to low-risk users. That is a survey of *caution*, not of incidence. Do not present it as a blast radius.
- Microsoft's own remediation guidance: <https://techcommunity.microsoft.com/blog/microsoft365copilotblog/mitigate-oversharing-to-govern-microsoft-365-copilot-and-agents/4448744>.
- Black-box visible only if the detector knows the requester's entitlements — probably out of scope for a domain-agnostic detector. Flagging it so the Lead can rule it out deliberately.

### 9.9 Hypothesized, NOT documented — do not include without evidence
I looked for and did **not** find citable instances of: an upstream tool returning the same schema with changed *semantics* (units, timezone, enum meaning); a reranker model swap; a chunking-strategy change in production. These are plausible and are in every practitioner blog, but I have no grade A/B source. **Excluding them is the honest choice** given that the taxonomy's entire validity argument is "drawn from documented reality."

---

## 10. Blast-radius evidence

Every figure I could verify, with its denominator and grade. **This is the section the task said matters most, so I am also reporting what it does not support.**

| # | Incident | Blast radius | Denominator | Grade |
|---|---|---|---|---|
| 1 | Google AI Overviews policy violations (2024-05) | **< 1 in 7,000,000** (<1.4e-5 %) | unique queries on which an AI Overview appeared | A |
| 2 | Anthropic routing, Vertex AI (2025-08/09) | **< 0.0004%** | requests on Vertex | A |
| 3 | Anthropic routing, Bedrock peak (from 2025-08-12) | **0.18%** | all Sonnet 4 requests on Bedrock | A |
| 4 | Anthropic routing, API initial (2025-08-05) | **0.8%** | Sonnet 4 requests | A |
| 5 | OpenAI status entry (2026) | **1%** of turns failing was worth a public status incident | ChatGPT Work turns, existing threads | A |
| 6 | OpenAI Redis leak (2023-03-20) | **1.2%** | ChatGPT Plus subscribers active 01:00–10:00 PT | C (primary 403s) |
| 7 | OpenAI cross-account cache leakage via OpenRouter (2025-11/12) | **4.8%** | cross-account requests, OpenAI provider | B |
| 8 | Thinking Machines, temp-0 divergence | **0.8%** took the minority branch (8/1000); **92%** of runs were not the modal completion (80 unique / 1000) | 1000 completions of one prompt | A |
| 9 | LinkedIn schema errors, before fix | **~10%** | LLM responses | A |
| 10 | OpenAI Nov 2024 outage | **13%** (Paid), **23%** (Enterprise) error rate | ChatGPT requests | A |
| 11 | Anthropic routing, worst hour (2025-08-31) | **16%** | Sonnet 4 requests | A |
| 12 | Anthropic routing, user-level | **~30%** | Claude Code users making requests in the window | A |
| 13 | Chen et al., GPT-4 prime accuracy Mar→Jun 2023 | **84% → 51%** (v3, balanced); 97.6% → 2.4% (v1, primes-only) | n=1000 (500 prime + 500 composite) | B |
| 14 | RAG top-k 3→5 (controlled) | **EM 0.481 → 0.367**, −24% relative | n=500 questions | B |
| 15 | LMCache KV contamination | **~90%** contaminated (14/138 correct) | session returns | B |
| 16 | Groq cross-account cache hit via OpenRouter | **100%** | cross-account probes | B |
| 17 | Mastra one-bad-schema | **100%** of that agent's requests | all requests incl. unrelated | B |
| 18 | LibreChat tool drift | **474 agents** | denominator (total agents) not published | B |
| 19 | Pinecone index deletion (2023-03-01) | **515 indexes** (19 with lost updates) | denominator (total free-tier indexes) not published | A |
| 20 | Air Canada | **n = 1** | known affected customers | B |
| 21 | Replit DB deletion | **1,206 executives + >1,196 companies** | one customer's database | C |

### What the distribution actually shows

**The design assumption — "real regressions are localized (a few percent), injected faults tend to be global" — is half-supported.** Reporting this honestly:

1. **It holds well for faults whose cause is in the request path** (routing, load balancing, provider selection, cache partitioning, deployment canaries). Rows 2, 3, 4, 7, 11: 0.0004% to 16%, all under 20%. This is the a-prime target regime and the evidence for it is grade A.

2. **It fails for faults whose cause is in a globally-shared artifact.** Prompt edits (Grok, DPD), reward-signal changes (GPT-4o sycophancy), model version bumps (Chen et al.), decoding/compiler bugs, chat-template bugs, and cache-backend bugs (row 15, ~90%) are all **global or near-global by construction**. There is exactly one copy of the system prompt. Rows 8, 13, 15, 16, 17 are all ≥84%.
   **So the localized/global split is not real-vs-injected. It is request-path-vs-shared-artifact.** If the harness injects prompt regressions globally and routing faults at 1%, it is matching reality on both counts — and a detector that learns "global ⇒ injected" will be learning a harness artifact that does not exist in the wild. I think this is the most consequential correction in the document and I want the Lead to see it stated flatly.

3. **Blast radius is not a property of the fault class** — it is a property of the deployment topology. Same class, three orders of magnitude: Anthropic's routing bug was 0.0004% on Vertex and 16% on the API in the same week, for the same bug. Tool-surface change was silent-and-partial in LibreChat and loud-and-total in Mastra. The taxonomy should carry blast radius as an **independent axis crossed with fault class**, not as an attribute of each class.

4. **Request-level and user-level rates differ by ~20x when assignment is sticky.** Anthropic: 0.8–16% of requests, ~30% of users. Any per-input FDR estimate that ignores stickiness will be badly wrong, and stickiness is the norm (session affinity, sticky routing, per-account provider pinning). Cross-reference MTH-009.

5. **Providers publish blast radius in percent-of-requests and treat ~1% as newsworthy** (row 5). That sets a rough floor on what industry considers a reportable regression, which is a defensible external anchor for the bottom of our severity ladder.

### Detection latency distribution (all grade A/B)

| Latency | Incident | How detected |
|---|---|---|
| ~3 min | Pinecone index deletion | internal alert + customer tickets |
| hours | GPT-5 autoswitcher; Grok May 2025; Cursor "Sam" | public complaint |
| ~16 h | Grok July 2025 | public outcry |
| ~1 day | DPD | viral tweet |
| ~4 days | GPT-4o sycophancy | user reaction |
| ~9 h exposure, 4 days to disclosure | OpenAI Redis | user reports |
| ~30 days | Anthropic routing | user reports |
| ~5 months | NYC MyCity | journalists |
| ~10 months | LibreChat tool drift | manual DB query |
| ~15 months | Air Canada | one customer, via a tribunal |

**Bimodal, and the split is loudness, not severity.** Hard failures: minutes to hours, caught by monitoring. Silent quality regressions: weeks to months, and **not one of them was caught by the operator's own automated evaluation.** Every silent regression in this corpus was found by a human noticing, or by someone running a ground-truth probe (LMCache). That absence is the strongest available motivation for the tool, and it is worth saying in the paper.

---

## 11. Structural finding: provider status pages do not report quality regressions

Reproducible, with the commands.

```
curl -s "https://status.claude.com/history.rss"   | grep -c "<item>"     # 25
curl -s "https://status.openai.com/history.rss"   | grep -c "<item>"     # 93
```

- **Anthropic: 25 incidents, 2026-08-15 → 2026-09-24 (~40 days). 0 describe an output-quality regression.** All are elevated errors, latency, degraded performance (availability sense), or feature/auth failures.
- **OpenAI: 93 incidents, 2026-06-26 → 2026-09-23 (~90 days). 0 describe an output-quality regression.** Titles are errors, latency, login/SSO, billing, image-generation availability, FedRAMP. The closest to a quality statement is "1% of ChatGPT Work (mobile/web) turns are failing for existing threads" — a hard failure with a rate.

**Consequence: 0/118 status-page incidents across the two largest providers, over the sampled windows, are output-quality regressions.** Anthropic's own Aug–Sep 2025 quality degradation — a month-long, up-to-16% regression — was **never a status-page incident**. It surfaced only as an engineering blog post published 2025-09-17, after the fact.

Two things follow. First, status pages are the wrong corpus for this taxonomy and we should stop treating them as a source; only voluntary post-mortems carry quality regressions. Second — and this is the argument for the study — **the industry has no reporting channel for the exact fault class a-prime detects.** Not "under-reported": structurally absent.

A related negative result: the **AI Incident Database** (incidentdatabase.ai) is indexed by *harm*, not by *regression*. Its entries record that a system did something bad, almost never that a system's behaviour changed relative to a prior version. Useful for §7 and §9.4; near-useless for §1–§6 and §8.

---

## 12. Sources I could NOT verify, or that are not evidence

Stating these plainly rather than padding the classes with them.

**Fabricated-looking numbers in SEO/AI-generated blog content (grade D — do not cite):**
- "$340,000 in lost revenue over 6 weeks" from a silent `text-embedding-ada-002` update, and the claim that "OpenAI silently updated ada-002 with the same version string." I searched specifically for this and found **no** OpenAI changelog, community thread or status entry supporting it. It appears only in content-farm posts. **Treat as fabricated.**
- "80% of RAG failures trace back to the ingestion and chunking layer" — no underlying study.
- "73% of enterprises discover critical data exposure risks after deploying Copilot" — no underlying study.
- "9% recall gap between best and worst chunking strategy" — cited to nothing.
- Sites recurring in searches with this profile: theneuralbase.com, dev.to/*(several), decompressed.io, envive.ai, agent-kits.com, vibegraveyard.ai, various Medium reposts. Several GitHub "issues" surfaced by search live in repos with no other activity (`phasespace-labs/palinode`, `Ledger-Lenz/Ledgerlens-core`, `kenn-io/msgvault`, `daintreehq/daintree`, `pvliesdonk/fastmcp-server-template`) and I did not use any of them.

**Primary sources I could not fetch (numbers therefore downgraded):**
- `openai.com/index/expanding-on-sycophancy/` and `openai.com/index/sycophancy-in-gpt-4o/` — HTTP 403. Content in §3.4 is via VentureBeat and Simon Willison. The quotes are consistent across both, but they are grade C until someone fetches the originals.
- `openai.com/index/march-20-chatgpt-outage/` — HTTP 403. The 1.2% figure is via The Hacker News quoting OpenAI.
- arXiv 2307.09009 PDF (binary) and the HDSR mirror (403). Only the abstract figures for Chen et al. are verified; sensitive-question and code-executability percentages are **not**.
- aider.chat 2024-01-25 benchmark numbers live in an SVG; qualitative claim only.
- LessWrong OpenRouter post: the 97% figure and the NeurIPS author's concession are quoted, but per-provider accuracy deltas were not in the accessible sections.

**Classes where I must report a null result:**
- **No** operator post-mortem of a context-truncation incident with a blast radius figure.
- **No** operator post-mortem of a retrieval-degradation incident (top-k, embedding swap, index staleness) — the only retrieval post-mortem is Pinecone's, which is a deletion.
- **No** operator post-mortem of a decoding-parameter change causing a regression.

---

## 13. Recommendation to the Lead

**Classes with evidence strong enough to survive a "drawn from documented reality" claim:**
1 (model swap), 3 (prompt regression), 5 (tool breakage), 6 (provider drift), 7 (KB staleness), plus new 9.1 (cache contamination), 9.2 (numerical/serving corruption), 9.3 (routing heterogeneity), 9.4 (persona drift).

**Classes to keep but label as mechanism-documented, incident-undocumented:**
2 (context truncation) — grade B mechanism on a very widely deployed runtime, no blast radius anywhere.
4 (retrieval degradation) — no incidents; severity ladder from arXiv 2606.28337 only.
9.6 (template/token mismatch), 9.7 (output truncation).

**The class I would argue against keeping in its current form:**
**8 (decoding parameter change).** One production instance exists (Anthropic top-k) and it was a compiler bug, not a parameter edit. Either reframe it as *sampling-path fault* — which 9.2 already covers — or drop it. As written it is the one class in the eight with no documented instance matching its own description, which is precisely the failure mode the taxonomy freeze is meant to prevent.

**Three findings that should change the harness design, not just the taxonomy:**
- Real prompt regressions are **1–3 line edits** (§3.2, measured from xAI's repo). Anchor the ladder there.
- **10% retrieval corruption is undetectable** at n=500 (§4.2). That is the published floor.
- **Temperature 0 gives 80 unique completions per 1000** and the rate moves with server load (§8.2). A-prime must be collected in the same load regime as A and B, or the decoy arm is miscalibrated.

**And the correction I most want seen:** the localized-vs-global split is **request-path vs shared-artifact**, not real vs injected (§10.2). Building the harness on the assumption that injected faults are global and real ones are not would bake a false discriminant straight into the study.
