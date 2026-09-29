# Systems under test — current state

`src/aprime/systems/ollama.py`. The first adapter against a real serving stack.

## The pool (ratified 2026-09-29)

| Model | Lab | Architecture | Role |
|---|---|---|---|
| granite4.2:8b | IBM | hybrid Mamba-2 | primary agent model, best batched throughput |
| ministral-3:8b | Mistral | dense | include **with** the template mitigation below |
| qwen3.5:9b | Alibaba | dense | best single-stream, cannot batch at 8 GB |
| a 3B | — | dense | deliberate weak system |

All Apache-2.0, four labs, two architectures. Chosen for **family diversity, not
quality** — every 8B tested drove a chained two-step tool loop 12/12, so
capability does not discriminate at this size (BCH-007). MTH-017 is the
precedent: one instrument reproduced the direction of every finding and none of
the magnitudes, so a result that holds on one family is worth much less than one
that holds across several.

The 3B is a design choice, not a compromise. Its ~25% chaining failure rate
gives a high natural error floor, which tests that the detector reads "changed"
rather than "bad".

## Three things the adapter refuses

**An empty system message.** Omitting it does not mean "no system prompt" — it
means the vendor template supplies one. Ministral 3's Ollama template injects
roughly 540 tokens that interpolate `{{ currentDate }}`, so the system prompt
changes every midnight and an A arm on one date differs from a B arm on the next
by a prompt edit nobody made: F2 at global blast radius with a 24-hour period
(BCH-009). `system` is required with no default.

**Vendor sampling defaults.** They differ across the pool — temperature 1.0 for
one member, 0.15 for another. Comparing defaults compares sampling
configurations, not models. Every parameter is explicit and enters the request
fingerprint, so changing one is visible to the pin.

**An unpinned stack.** `pin()` captures server version, model digest and request
fingerprint; `verify_pin()` raises `PinMismatch` when any has moved. This is
D12's resolution: the observed incident was the Ollama client updating itself
0.32.5 → 0.34.4 unprompted mid-survey, which is F4 provider drift injected by
our own tooling. A study whose serving stack changed halfway through has two
baselines, and the decoy arm would absorb the difference as ordinary noise
rather than reporting it.

## One thing it detects rather than prevents

Qwen3.5 defaults `thinking` on and can spend an entire token budget reasoning,
returning empty content. That signature is **indistinguishable from the F12
output truncation the harness injects deliberately**, so an empty response with a
non-zero token count is flagged in the trace as `empty_with_tokens` instead of
passing through as a short answer. `think` is also explicit and defaults to off.

## Failures are samples, not exceptions

A transport error returns a Response with `trace.error` set rather than raising.
The recorder captures errored samples and carries on, because aborting a
multi-hour run over one transient refusal is worse than a gap the analysis can
see and exclude.

## Arms

`build_arms(baseline, candidate)` gives A, A_prime and B, where **A and A_prime
share one configuration object by identity**, not a copy. The decoy arm has to be
the same system; a copy could drift. Only B differs, and what differs is whatever
the caller changed — that is the thing under test.

## Known limits

- **Tested against a fake transport only.** Whether a real server behaves as the
  fake does is unverified. That is the next thing to check, and it needs a live
  server and therefore the GPU.
- Context size is explicit but **not yet calibrated**. D11 settled the sequence:
  build the cells, measure each one's peak token demand, then fix the cap.
  Guessing it first is how the agent cell spills to CPU.
- No GBNF constrained decoding through this API. If the structured-extraction
  cells need guaranteed schema adherence, that is the trigger for migrating to
  llama.cpp — the conditional half of D12.
- The template itself is not captured, only the server version and model digest.
  A template change within one Ollama version would slip past the pin.
