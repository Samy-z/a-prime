# Pool refresh research, 2026-10-16 — commissioned by the owner

Question: has a 2026 open-weight model branded or renowned for agentic/tool
work emerged, in the 7-9B class, worth adding to the D10 pool? Four
web-grounded sweeps (releases, Ollama ecosystem, benchmarks, credibility)
plus a synthesis. Bars: agentic branding or measured tool-use lead; 7-9B;
fits ~6.8 GB at Q4 on the 8 GB RTX 4060 under Ollama; reputable org; clean
license; independent of pool members; popular enough that a flag reads as
"difference detected", not "bad product shamed".

**Finding: no candidate clears every bar.** Two near-misses, each failing a
different hard one.

## Ornith 1.0/1.5 9B (DeepReinforce, MIT, 2026-06/08)

The loudest agentic-branded 9B of the year: 631K Ollama pulls in ~3.5 months
(https://ollama.com/library/ornith), vendor SWE-bench Verified 69.4. Fails
two bars. (1) Independence: its own card says the family builds on Qwen3.5
and Gemma4 (https://huggingface.co/ornith-ai/Ornith-1.5-9B); the community
GGUF repack names the Qwen3.5-9B base — it would correlate with qwen3.5:9b
on exactly the axes the matrix treats as independent. (2) Our serving stack:
documented Ollama tool-call breakage — chat template hard-raises on message
order, Hermes-style XML via a parser Ollama lacks, HTTP 400
(https://github.com/ollama/ollama/issues/16988). Unreliable tool emission
makes harness noise indistinguishable from injected faults. All benchmark
figures vendor-run; no independent reruns found.

## LFM2.5-8B-A1B (Liquid AI, 2026-05-28) — the nearest miss

Clears branding (Ollama: "built for fast, reliable tool calling", 5.2 GB,
213.9K pulls, https://ollama.com/library/lfm2.5), size, fit, org, and
independence (own sparse-MoE architecture — would be the pool's first MoE).
Fails the measured bar: independent BFCL v4 49.7, below granite4.2:8b's 52.4
and far below qwen3.5:9b's ~66 (https://benchlm.ai/benchmarks/bfcl-v4), and
vendor Tau2-Telecom 88.07 against an independent listing of 16
(https://www.llmreference.com/model/lfm-2.5-8b-a1b) — an unresolved 72-point
gap. Flagging its inconsistency invites "you picked a weak product".
Secondary frictions: LFM Open License v1.0 (Apache-derived, $10M revenue
cap — study-safe, footnote); built-in reasoning trace needing a
command-verified off switch under the think=False rail.

## Everything else fails faster

NVIDIA Nemotron 3 Nano / 3.5 Lightning: the strongest agentic branding of
the period, but 30-32B MoE, ~17-20 GB resident at Q4 — all weights load even
when few are active. Gemma 4 E4B: first Apache-2.0 Gemma with native
function calling, but ~4B effective (capability-axis size), weak multi-step
tool use (tau2 57.5 vs 86.4 for its 31B sibling), and documented Ollama
template breakage. xLAM-2 / Hammer2.1: CC-BY-NC, pre-2026. LFM2.5-2.6B,
MiniCPM5-2B, tev1: capability-axis size.

## Pool health

Nothing obsoletes the ratified pool: qwen3.5:9b remains the 8 GB-tier agent
default in 2026 guides (BFCL v4 ~66, tau2 79.1); Qwen3.6 ships no 9B;
granite4.2 is current.

## Noted in passing

The LFM2.5 vendor-vs-independent 72-point Tau2 gap is exactly the class of
dispute a label-free detector arbitrates — a future comparator case study,
not a pool admission.

## Reopen if

A 2026-Q4+ release clears all bars (watch: a dense 7-9B from NVIDIA's
Nemotron line, a Qwen3.6 9B, an LFM2.5 revision with independent tool-use
scores); or the GPU budget changes, which re-admits the 30B-A3B MoE class.
