# bench — model pool survey for the systems under test

Layer 4 working memory. Not committed. 2026-09-25.

Claim: `.agents/bench-worklog.md`, `[open] 2026-09-25 bench — model pool`.
Binding: MTH-008, MTH-018, BCH-001, BCH-004, F13, F14.

**Nothing here is settled until a BCH-### entry exists.** Grading convention
used throughout: **M** = measured by me on this box today, reproducible;
**P** = published measurement on comparable hardware; **S** = secondary
reporting, single source; **U** = unverified / vendor claim only.

---

## 0. The box, measured (M)

Instrument: `nvidia-smi`, 2026-09-25 05:40.

```
NVIDIA GeForce RTX 4060 Laptop GPU, WDDM
Driver 616.56, CUDA UMD 13.4
0 MiB / 8188 MiB, 90 W cap
```

- **Hard ceiling 8188 MiB.** Highest peak I drove it to without failure was
  7908 MiB. Treat **~7.9 GiB as the wall** and ~7.0 GiB as the safe operating
  band with a browser open.
- Laptop part, 128-bit bus, 90 W. Published "RTX 4060" figures are usually the
  desktop card. Do not inherit them.

Instrument: `ollama list` / `ollama show`. Already on disk before today:
`ministral-3:3b` (3.0 GB), `ministral-3:8b` (6.0 GB), `qwen3.5:9b` (6.6 GB),
`qwen3:14b` (9.3 GB — over budget), `nomic-embed-text`. I added
`granite4.2:8b` today.

**Incident to record: the Ollama client auto-updated itself 0.32.5 → 0.34.4
during the first `ollama list` of this session, unprompted.** It downloaded and
silently ran the installer. Not deliberate on my part. This matters: an
unpinned serving stack that upgrades itself mid-study is fault class **F4
(provider drift)** injected by accident at blast radius **B0**, and it is
exactly the thing the pinned-instruments rail exists to prevent. All numbers
below are on 0.34.4. See §7.

---

## 1. Throughput, measured on this box (M)

Instrument: `scratchpad/bench_throughput.py` — N concurrent HTTP requests to
`/api/generate`, `num_predict=150`, temperature 0.8, distinct seeds, model
pre-warmed so load time is excluded, VRAM sampled at 2.5 Hz throughout.
Aggregate = total output tokens / wall clock.

### 1a. Ollama's default config does not batch at all

Default server (`OLLAMA_NUM_PARALLEL` unset), `num_ctx=16384`:

| Model | conc 1 | conc 4 | conc 8 | peak VRAM |
|---|---|---|---|---|
| qwen3.5:9b | 28.26 t/s | 28.33 | 28.39 | 6365 MiB |
| ministral-3:3b | 87.70 t/s | 88.58 | 88.52 | 4831 MiB |

**Aggregate throughput is flat to within 0.5% across an 8x change in
concurrency, and mean per-request latency scales linearly (5.31 → 13.24 →
23.81 s).** That is pure serialization. Out of the box, Ollama 0.34.4 on this
machine runs one request at a time. Anyone scoping the study against
"batched serving is assumed" without checking this would be out by whatever
factor they assumed.

### 1b. Turning batching on at 16k context makes things worse

Second server, `OLLAMA_NUM_PARALLEL=4`, `num_ctx=16384`:

| Model | conc 1 | conc 4 | conc 8 | peak VRAM |
|---|---|---|---|---|
| ministral-3:3b | 28.19 t/s | 57.05 | 56.37 | **7908 MiB** |

Batching engages (2x), but single-stream collapses from 87.7 to 28.2 t/s and
the best batched number, 57 t/s, is **35% below the unbatched 88 t/s**. VRAM
sits at 7908 of 8188 MiB — at the wall. Four slots x 16k context of KV cache
pushes the model partly off the GPU and the offload cliff eats the batching
win.

### 1c. The context cap, not batching, is the throughput lever

Same server, `OLLAMA_NUM_PARALLEL=4`, `num_ctx=4096`:

| Model | conc 1 | conc 4 | conc 8 | peak VRAM | batch gain |
|---|---|---|---|---|---|
| ministral-3:3b | 89.22 | 187.83 | **222.18** | 7024 MiB | **2.5x** |
| granite4.2:8b | 23.45 | **65.77** | 58.90 | **6041 MiB** | **2.8x** |
| ministral-3:8b | 22.03 | 44.58 | **46.31** | 6223 MiB | **2.1x** |
| qwen3.5:9b | 41.28 | 41.52 | 41.58 | 7888 MiB | **1.0x — none** |

Dropping the context cap from 16k to 4k takes the 3B from 57 to 222 t/s — a
**3.9x swing**. This is the single most actionable number in the survey.

Same server, `OLLAMA_NUM_PARALLEL=4`, `num_ctx=16384`, for direct comparison:

| Model | conc 1 | conc 4 | conc 8 | peak VRAM | vs its own 4k best |
|---|---|---|---|---|---|
| granite4.2:8b | 7.30 | 20.68 | 21.38 | **6041 MiB** | **3.1x slower** |
| ministral-3:3b | 28.19 | 57.05 | 56.37 | 7908 MiB | 3.9x slower |

**Granite is the informative row, and it corrects the mechanism.** Its peak VRAM
is *identical* at 4k and 16k — 6041 MiB both times — so nothing was offloaded,
and yet throughput fell 3.1x. The context penalty is therefore **not only
KV-cache VRAM pressure**. For the dense transformers it is (they hit the wall
and spill); for the hybrid it is compute over the larger allocated attention
window in the 1-in-9 attention layers. Two different mechanisms, same
conclusion, which is stronger than one mechanism would have been:

> **Every model tested is roughly 3-4x slower at 16k than at 4k, and the reason
> differs by architecture.** The context cap is the throughput decision.

**Qwen3.5-9B cannot batch on this box.** At 7888 MiB it has no room for a
second slot, so Ollama silently runs it with one. It is the fastest
single-stream model tested (41.6 t/s) and the slowest in aggregate once anyone
else is competing for it.

**Granite 4.2 8B has the most headroom of any 8B-class model tested (6041 MiB)
and the best batched throughput (65.77 t/s).** That is the hybrid Mamba-2
architecture doing what IBM claims for it — a 9:1 Mamba-to-attention ratio means
the KV cache barely grows, which is exactly the resource this box runs out of
(S: IBM/InfoQ/VentureBeat claim >70% RAM reduction for long context and
concurrent batches; **M**: I measured 6041 MiB vs 7888 MiB for a same-class
transformer, which is consistent with it).

### 1d. Published comparison points (P)

localllm.in, RTX 3070 8 GB (desktop, 448 GB/s vs this laptop's ~272 GB/s), all
Q4_K_M @ 32k, single stream:

| Model | Peak VRAM | Decode | Layers on CPU |
|---|---|---|---|
| Qwen3.5-9B | 6.96 GB | 54.9 t/s | 0 |
| GLM-4.6V-Flash | 7.16 GB | 17.4 t/s | 4 |
| Nemotron Nano 12B v2 | 7.75 GB | 6.6 t/s | 19 |
| Gemma 3 12B | 10.02 GB | 4.3 t/s | 23 |
| Phi-4 14B | 11.22 GB | 1.8 t/s | 24 |

Their 54.9 t/s for Qwen3.5-9B vs my 41.6 t/s is the desktop/laptop gap, about
what the bandwidth ratio predicts. **Use ~0.75x on any published desktop-4060 or
3070 figure to get this machine.**

The 4-layer → 17.4 t/s row is the offload cliff: it is a 3x penalty for
*four* layers, not a gradient. Everything ≥12B is out on that basis alone, not
merely "slower".

---

## 2. Tool calling — measured, because it is not published (M)

**The published record is empty where we need it.** BFCL v4 (April 2026;
weights Agentic 40 / Multi-Turn 30 / Live 10 / Non-Live 10 / Hallucination 10)
has no entry I could find for Qwen3.5-9B — there is an *open request* to
evaluate it (OpenEuroLLM/Taskboard #384), which is direct evidence nobody has —
and none for Ministral 3 8B. What exists:

| Model | Score | Version | Grade |
|---|---|---|---|
| Granite 4.2 30B | 61.39 | v4 | S |
| Granite 4.2 8B | 52.39 *or* 50.29 | v4 | **S, two sources disagree** |
| Qwen3.5-122B-A10B | 72.2 | v4 | S |
| Granite 4.1 30B | 73.68 | v3 | S |
| Gemma-4-31B | 72.7 | v3 | S |
| Granite 4.1 8B | 68.3 | v3 | S |
| Llama 3.1 8B Instruct | 0.761 | pre-v4 | S, stale aggregator |

v3 and v4 are **not comparable** — the v4 reweighting dropped scores 10-20
points across the board. Any table mixing them is a category error, and most of
the secondary reporting above does exactly that.

So I measured it instead.

**Instrument: `scratchpad/toolprobe.py`.** A two-step *chained* agent loop, which
is the thing the brief says is the binding constraint. Two tools
(`get_transaction`, `get_account_balance`); the user asks for the balance of the
account a given transaction hit. Correct behaviour is: call tool 1 with the
transaction id, read `account_id` out of the result, call tool 2 with *that*
id, then state the balance. 3 transaction ids x 4 repetitions = **12 trials per
model**, temperature 0.2, real tool results returned to the model each turn, up
to 5 turns.

| Model | called t1 | t1 args right | called t2 | **t2 args right** | final answer right |
|---|---|---|---|---|---|
| granite4.2:8b | 12/12 | 12/12 | 12/12 | **12/12** | 12/12 |
| ministral-3:8b | 12/12 | 12/12 | 12/12 | **12/12** | 12/12 |
| qwen3.5:9b (think off) | 12/12 | 12/12 | 12/12 | **12/12** | 12/12 |
| **ministral-3:3b** | 12/12 | 12/12 | 12/12 | **9/12** | **9/12** |

**The 3B is where chaining breaks, and it breaks in exactly the informative
place.** It calls both tools every time and gets the *first* call's arguments
right every time; it fails 3/12 (25%) at carrying the returned `account_id`
into the second call. Single-shot tool use is solved at 3B; *chained* tool use
is not.

Denominator caveat: n=12 per model is a smoke test, not a benchmark. 12/12 gives
a 95% Clopper-Pearson lower bound of 0.74 — it rules out "broken", not "good".
Same MTH-008 logic as everywhere else in this project. Before the agent cells
are built this wants n≥100 and a harder task (parallel calls, a missing tool, a
tool that errors).

---

## 3. Two harness traps found by accident, both live on models already on disk (M)

These are F14 and F12 firing without anyone injecting them. Both are
reproducible in one command.

### 3a. Ministral 3 injects a hidden, date-varying system prompt

Instrument: `/api/chat`, identical user message `"Reply with exactly the word
OK."`, measured `prompt_eval_count`.

| Condition | prompt tokens |
|---|---|
| no system message | **560** |
| any system message supplied | **20** |

`ollama show ministral-3:3b --template` shows why. When the caller supplies no
system message the template injects ~540 tokens telling the model it is
"Ministral-3-3B-Instruct-2512 ... created by Mistral AI, a French startup
headquartered in Paris", that it powers "an AI assistant called Le Chat", that
its knowledge cutoff is 2023-10-01, plus web-browsing, multimodal and
tool-calling instruction blocks.

**The serious part: that injected block interpolates `{{ currentDate }}` and
`{{ yesterdayDate }}`.** The system prompt therefore **changes every day at
midnight**. A study whose A arm runs on one date and whose B arm runs on the
next has a silently different system prompt between the arms — fault class
**F2 (prompt regression) at blast radius B0**, injected by the harness, with a
24-hour period. If a single arm straddles midnight it is worse: the change
lands *inside* one arm and the A-vs-A-prime decoy will absorb it as baseline
noise, inflating the null and destroying power exactly the way MTH-007 warns a
drifting baseline does.

Mitigation is trivial once known: **always pass an explicit system message.**
It also drops prefill 28x on short prompts. But this must be a harness
invariant with a test behind it, not a convention.

### 3b. Qwen3.5 has thinking ON by default, and it silently eats the output budget

`ollama show qwen3.5:9b` reports `thinking: default true`. Measured, same
trivial prompt, `num_predict=40`:

| Setting | output tokens | went to `thinking` | visible content |
|---|---|---|---|
| default (think on) | 40 | 162 chars, all of it | **empty string** |
| `think: false` | 2 | none | `"OK"` |

**At the default, a 150-token generation budget can be consumed entirely by
reasoning and return an empty answer.** The observable signature — a
mid-generation stop with nothing useful emitted — is indistinguishable from
**F12 (output-side truncation)**, which is a class we intend to inject
deliberately. The harness would be unable to tell its own injected F12 from
Qwen's default configuration.

Also noted: default sampling parameters differ wildly per model
(`qwen3.5:9b`: temp 1.0, top_p 0.95, top_k 20, presence_penalty 1.5;
`ministral-3:3b`: temp 0.15; `granite4.2:8b`: temp 1.0, top_p 0.95). Cross-model
comparison on vendor defaults is comparing sampling configs, not models.
**Every sampling parameter must be set explicitly by the harness and recorded in
the config hash.** `granite4.2:8b` also advertises a `thinking` capability —
verify its default before use; I did not.

---

## 4. Candidate table

VRAM column: **M** = I measured peak on this box today at the stated context
with `OLLAMA_NUM_PARALLEL=4`; **P** = published on an 8 GB card; **U** =
unverified.

| Model | Params | Quant | Peak VRAM | ctx | Licence | Extract | Summary | Agent |
|---|---|---|---|---|---|---|---|---|
| **granite4.2:8b** | 8.8B | Q4_K_M | **6041 MiB (M)** | 4k x4 | Apache-2.0 (M, `ollama show`) | yes | yes | **yes (12/12 M)** |
| **ministral-3:8b** | 8B | Q4_K_M | **6223 MiB (M)** | 4k x4 | Apache-2.0 (M) | yes | yes | **yes (12/12 M)** |
| **qwen3.5:9b** | 9.7B | Q4_K_M | **7888 MiB (M)** | 4k x4 | Apache-2.0 (M) | yes | yes | yes (12/12 M) but cannot batch |
| ministral-3:3b | 3.8B | Q4_K_M | **7024 MiB (M)** | 4k x4 | Apache-2.0 (M) | yes | yes | **no — 9/12 chaining (M)** |
| granite4.2:3b | 3B | Q4_K_M | U | — | Apache-2.0 (S) | likely | likely | untested |
| gemma-4 E4B / E2B | eff. 4B / 2B | Q4_K_M | U | — | **Apache-2.0** (S — first Gemma to be) | U | U | U |
| phi-4-mini | 3.8B | Q4_K_M | U | — | MIT (S) | S: good JSON | U | **see §6 refusals** |
| llama-3.1-8b | 8B | Q4_K_M | ~5.6 GB (S) | — | Llama 3.1 Community (700M MAU) | yes | yes | S: BFCL 0.761 pre-v4 |
| mistral-7b-v0.3 | 7B | Q4_K_M | ~4.4 GB (S) | — | Apache-2.0 | S: strong | yes | weak (2024 model) |
| hermes-4-14b | 14B | Q4_K_M | ~8.5 GB est (U) | — | inherits Qwen3 base | — | — | **excluded, does not fit** |
| nemotron-nano-12b-v2 | 12B | Q4_K_M | 7.75 GB, 19 layers on CPU (P) | 32k | NVIDIA Open Model | — | — | **excluded, 6.6 t/s** |
| gemma-3-12b | 12B | Q4_K_M | 10.02 GB (P) | 32k | Gemma ToU (not OSI) | — | — | **excluded, does not fit** |
| phi-4 14B | 14B | Q4_K_M | 11.22 GB (P) | 32k | MIT | — | — | **excluded, does not fit** |
| llama-4-scout | 109B MoE | — | — | — | Llama 4 Community | — | — | **excluded — Meta has no small Llama 4** |

Notes on families the brief asked about that turned out not to be options:

- **Llama 4's smallest member is Scout at 109B total (16 experts).** There is no
  small Llama 4. The only Llama options are 3.1-8B / 3.2-3B, now ~2 years old,
  under a community licence with a 700M-MAU clause. Usable for research,
  strictly worse than the Apache-2.0 alternatives, and stale.
- **Hermes 4** ships at 14B (Qwen3-based), 36B, 70B, 405B. The 14B does not fit
  in 8 GB at any useful context. Nous's function-calling fine-tune is genuinely
  the relevant thing here — it trains JSON-schema adherence and malformed-object
  repair — but the smallest size is one tier too large. **Recommend dropping
  Hermes despite the owner naming it**, unless a 14B at Q3 with a 2k context is
  acceptable, which it should not be.
- **Gemma 4** (2026-04-02) is the first Gemma under **Apache-2.0**, in E2B, E4B,
  26B MoE and 31B dense. The E4B is the only plausible size and is **untested by
  me**. Worth a pull before the pool is frozen — it is the cheapest way to add a
  fifth lab.
- **Nemotron 3 Nano** (2026-04) is 30B-A3B — 3B active but **30B of weights
  resident**. MoE does not help when VRAM, not FLOPs, is the constraint. Out.
- **OLMo 3, Falcon H1/3, SmolLM3, Yi, InternLM** — I found no 2026 evidence
  putting any of them ahead of the four above on tool calling, and no measured
  8 GB VRAM figures. **Unverified rather than rejected.** OLMo's value here would
  be its fully open training data, which is a transparency argument, not a
  capability one.

---

## 5. Recommended pool (3-5 models, family diversity first)

The MTH-008 logic governs: **the unit of generality is the system, not the
input**, and MTH-017 just showed on NLI checkpoints that one instrument
reproduced the *direction* of every result and *none* of the magnitudes. A
model-pool finding that rests on one family is worth the same as that: almost
nothing. So diversity of lab and architecture beats quality, and it beats it by
a lot.

**Core three — different labs, different architectures, all Apache-2.0, all
measured on this box today:**

1. **`granite4.2:8b` (IBM, hybrid Mamba-2/transformer, Apache-2.0).**
   Best batched throughput measured (65.77 t/s), most VRAM headroom of any 8B
   (6041 MiB), 12/12 chained tool calling, the only published BFCL v4 number in
   the 8B class. The hybrid architecture is the one real architectural
   difference available at this size — everything else in the pool is a dense
   transformer — which is worth a lot for a transfer claim. **Primary agent-cell
   model.**

2. **`ministral-3:8b` (Mistral, dense transformer, Apache-2.0).**
   12/12 chained tool calling, batches 2.1x, 6223 MiB. European lab, different
   tokenizer, different chat-template conventions. **Carries a known F14 hazard
   (§3a) which is a reason to include it with the mitigation in place, not a
   reason to drop it** — a pool where every model has clean templates would not
   exercise the harness's own template discipline.

3. **`qwen3.5:9b` (Alibaba, dense transformer, Apache-2.0).**
   Fastest single-stream (41.6 t/s), 12/12 chained tool calling with thinking
   off, best general capability in class. **Cannot batch on 8 GB (measured).**
   Assign it to cells that are latency-tolerant and run it alone, or accept
   41.6 t/s as its ceiling. Its thinking default is a live F12 confound (§3b).

**Optional fourth and fifth, in priority order:**

4. **`granite4.2:3b` or `ministral-3:3b` as a deliberate weak system.** Not a
   quality choice — a *design* choice. The 3B's measured 25% chaining failure
   makes it a system whose agent cells have a high natural error floor, which
   is precisely what is needed to check that the detector is not merely reading
   "this system is bad" as "this system changed". And at 222 t/s it makes the
   high-volume summary and extraction cells affordable. **Use the 3B for
   extraction and summary cells, never for agent cells.**

5. **`gemma-4-e4b` (Google, Apache-2.0) — pull and test before freezing.** It is
   the cheapest available fifth lab. Untested by me; do not commit to it on
   vendor claims.

**Recommended freeze: 4 models — Granite 4.2 8B, Ministral 3 8B, Qwen3.5 9B,
and one 3B — with Gemma 4 E4B as a tested fifth if it clears the same probes.**
Four labs (IBM, Mistral, Alibaba, +Google), two architecture families
(hybrid-Mamba, dense transformer), one uniform licence (Apache-2.0), zero
licence encumbrance on publication.

**Format assignment across the 3 x 4 grid:**

| Format | Models | Why |
|---|---|---|
| Structured extraction | all four | cheapest format; constrained decoding via llama.cpp GBNF keeps format adherence from being the confound |
| Free-text summary | all four | no tool dependency; the 3B carries the volume |
| Multi-step agent | Granite 8B, Ministral 8B, Qwen 9B **only** | the 3B fails chaining 25% of the time (M) |

The agent format is the constraint the brief predicted, and it constrains by
*size*, not by family: every 8B-class model tested drives the loop; the 3B does
not.

---

## 6. What makes a model a bad choice here

- **Anything ≥12B.** Not "slower" — the offload cliff is 3x for four layers and
  30x for 24 (P). Gemma 3 12B, Phi-4 14B, Hermes 4 14B, Nemotron 12B all fail on
  this. MoE does not rescue it: Nemotron 3 Nano is 3B active but 30B resident.
- **Phi-4 family, for the banking cell specifically.** Phi-4-Multimodal's
  valid-prompt refusal rate is **26.4%** against Llama-3.2-3B at 15.6% and
  Phi-3.5-mini at 21.2% (S, Phi-4-mini technical report / secondary). Banking
  and finance prompts — disputes, fraud, AML, chargebacks — sit directly in the
  over-refusal blast zone. A system under test that refuses a quarter of valid
  domain inputs is injecting **F13 (refusal drift)** into the baseline, which
  contaminates both arms and any F13 we inject deliberately. MIT licence and
  good JSON do not compensate.
- **Gemma 3 and earlier: the Gemma Terms of Use are not an OSI licence** and
  carry a use-restriction schedule Google can update. Gemma 4 fixes this
  (Apache-2.0, S) but Gemma 3 should not go into a published study's system
  pool when Apache alternatives exist at the same size.
- **Llama 3.x Community Licence**: a 700M-MAU clause plus naming/attribution
  requirements. Harmless for research, but it means one row of the systems table
  has a different licence story than the rest for no capability gain, since
  Llama 3.1-8B is a 2024 model competing against 2026 ones.
- **NVIDIA Open Model Licence** (Nemotron): permissive but non-standard; moot
  here since the model does not fit.
- **Any model whose chat template injects a hidden or date-varying system
  prompt (§3a).** This is F14 by construction. Mitigable, but it must be tested
  for per model and the test must be in CI.
- **Any model with a reasoning mode defaulted on (§3b).** Confounds F12 and
  blows the token budget. Must be explicitly disabled and the disabling
  recorded in the config hash.
- **Ollama's own auto-updater.** See §7.

---

## 7. Serving recommendation

**vLLM: no, on this box.** Three independent reasons, only the first of which I
verified: (i) it is not natively supported on Windows and would need WSL2, which
takes a further slice of the 8 GB; (ii) it reserves VRAM up front
(`gpu_memory_utilization` 0.90 default), which on 8 GB collides with the exact
KV-headroom problem measured in §1c; (iii) its advantage is reported only at
32+ concurrent requests on datacenter GPUs (S), and **single-stream decode is
memory-bandwidth bound and therefore engine-independent** — a 4-bit 8B reads the
same weights per token whichever engine drives it. At the concurrency this card
can sustain (4, maybe 8), vLLM buys nothing it can pay for in VRAM. **llama.cpp
is the honest answer.**

**Recommendation: llama.cpp server directly, not Ollama.** Ollama is a wrapper
over llama.cpp and today it cost us three things: it serialized silently by
default (§1a), it auto-updated itself mid-session (§0), and it injected a
model's vendor persona without being asked (§3a). The study needs:

- `--parallel N` set explicitly and recorded
- `--ctx-size` set explicitly, per slot, and recorded
- **GBNF grammar-constrained decoding** for the extraction cells — this is the
  clean way to stop "the model emitted bad JSON" from confounding "the model's
  behaviour changed", and Ollama does not expose it
- a **pinned binary and a pinned model digest**, per the pinned-instruments
  rail. A serving stack that upgrades itself is an F4 injection.
- **prompt-cache reuse** across the three arms — see §8

If Ollama is kept for convenience, then at minimum: pin the version, disable the
updater, set `OLLAMA_NUM_PARALLEL` explicitly, always pass a system message, and
always set every sampling parameter.

**Operating point measured today: `OLLAMA_NUM_PARALLEL=4`, `num_ctx=4096`, 4-8
concurrent requests.** That is 222 t/s for a 3B and 59-66 t/s for an 8B.

**On the 16k cap in the brief: it was chosen to keep inference on the GPU, and
measured, it is the thing costing the most throughput.** For the dense
transformers it defeats its own purpose — four slots of 16k KV push the model
partly off the GPU (7908 MiB, §1b). For the hybrid Granite it does not spill at
all (6041 MiB at both 4k and 16k) and still costs 3.1x. Either way the penalty
is 3-4x. **Recommend 4k-8k per slot** and designing
the domain cells' knowledge packs to fit, rather than 16k. If some cell genuinely
needs 16k, run that cell alone at `--parallel 1` and budget it separately.

---

## 8. Throughput budget — what ~1M generations actually costs

Arithmetic, from measured aggregate throughput, 150 output tokens per
generation, **decode only**:

| Serving config | Aggregate | 1M x 150 tok | Wall clock, continuous |
|---|---|---|---|
| 3B @ 4k, parallel 4, conc 8 (M) | 222.2 t/s | 150 M tok | **7.8 days** |
| Granite 8B @ 4k, parallel 4, conc 4 (M) | 65.8 t/s | 150 M tok | **26.4 days** |
| Ministral 8B @ 4k, parallel 4, conc 8 (M) | 46.3 t/s | 150 M tok | **37.5 days** |
| Qwen 9B @ 4k, no batching (M) | 41.6 t/s | 150 M tok | **41.7 days** |
| 3B @ 16k, parallel 4 (M) | 56.4 t/s | 150 M tok | **30.8 days** |
| Qwen 9B @ 16k, default Ollama (M) | 28.3 t/s | 150 M tok | **61.3 days** |
| Granite 8B @ **16k**, parallel 4 (M) | 21.4 t/s | 150 M tok | **81.2 days** |

The last row is the cost of the brief's 16k cap stated plainly: the *best* 8B in
the pool, run the way the brief specifies, takes **81 days** for 1M generations
against **26 days** at 4k.

**Prefill is not in those numbers and is not negligible.** Estimated from the
warm-up records (wall minus load minus eval): ~2,900 t/s prefill for the 3B,
~455 t/s for the 9B on a 91-token prompt. Realistic domain prompts carrying a
knowledge pack will be 1-4k tokens. At 2k prompt tokens and ~1,200 t/s for an
8B, that is ~1.7 s of prefill per call — **another ~20 days over 1M calls**,
comparable to the decode cost. Grade **U**: estimated, not measured. It should
be measured before the study plan is fixed.

**Headline: ~1M generations of 150 tokens is 26-60 days of continuous compute on
this laptop for the 8B class, plus roughly as much again in prefill. It is not
affordable.**

**But the design does not need 1M.** From MTH-018, k=20 across three arms is
**60 calls per input**. 1M generations therefore buys 16,667 inputs. MTH-018's
own power envelope was measured at **400 inputs with 40 changed**, and power at
k=20 / severity 0.6 was 0.73 there. So:

```
9 cells x 600 inputs x 60 calls  =  324,000 generations
```

At 65.8 t/s (Granite, measured) that is **8.5 days of decode**, and with prefill
caching (below) the total lands in the low two weeks. **That is feasible. 1M is
roughly 3x more than the factorial actually requires.**

**The single biggest available saving is prompt-cache reuse, and it is free.**
The three arms (A, A-prime, B) replay the *same inputs*, and k=20 means 20
repeat generations per input per arm. All 60 calls for a given input share an
identical prompt prefix. With llama.cpp's prompt cache the prefill is paid
**once per input instead of 60 times** — a 60x cut on the prefill half of the
bill, taking it from ~20 days to hours. This needs the replay loop to group by
input rather than interleave, which is a scheduling decision that belongs to the
`engine` seat. **Flag it to them: the arm-interleaving order is a 20-day
decision, not a style preference.**

Recommended scoping to hand to `study`:

| Scope | Generations | Decode @ 65.8 t/s | Verdict |
|---|---|---|---|
| 9 cells x 400 inputs (MTH-018 parity) | 216,000 | 5.7 days | comfortable |
| 9 cells x 600 inputs | 324,000 | 8.5 days | **recommended** |
| 9 cells x 1000 inputs | 540,000 | 14.2 days | upper bound |
| "1M generations" as briefed | 1,000,000 | 26.4 days | not affordable |

All figures are continuous-compute days on a 90 W laptop GPU and assume it is
not being used for anything else. Real elapsed time will be worse. Thermal
throttling over multi-day runs is **unmeasured** — my longest run today was 85
seconds — and is the largest unquantified risk in this section.

---

## 9. Open items / not verified

- Granite 4.2 8B `thinking` default: advertised as a capability, default not
  checked. Check before use (§3b is the reason).
- Gemma 4 E4B: not pulled, not tested. The cheapest fifth family.
- granite4.2:3b: not pulled. May be a better weak-system than ministral-3:3b.
- Prefill throughput: estimated, not measured.
- Thermal sustain over hours/days: unmeasured, and it gates every number in §8.
- Tool probe n=12 per model: rules out "broken", not much else. Needs n≥100 and
  harder tasks (parallel calls, missing tool, erroring tool) before agent cells
  are built.
- OLMo 3, Falcon H1/3, SmolLM3, Yi, InternLM: no 2026 evidence found either way.
  Unverified, not rejected.
- BFCL v4 for any model in the recommended pool except Granite: does not exist.
- llama.cpp direct (vs Ollama): not benchmarked. The §7 recommendation rests on
  capability arguments (GBNF, pinning, prompt cache), not on a measured speed
  difference over Ollama — and there may not be one, since it is the same engine.
