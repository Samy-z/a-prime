# engine — METHODS

## Conventions

- The adapter is `input -> output + trace` and nothing more. Every request to
  widen it is a design smell; record the pressure in the LEDGER rather than
  widening quietly.
- Three arms always: A, A-prime, B. A-prime is not optional, and it is
  interleaved in time with B rather than batched before it — the point is to
  capture drift and ordering effects, which a batched decoy arm would miss.
- Nothing is compared before dedup.

## Induced conformance — the three-tier band

Rules are induced from the baseline's own output distribution, not authored.
Hand-written schemas are an override, not the default.

| Consistency across A and A-prime | Treatment |
|---|---|
| About 100% | Hard invariant. Enforced automatically, no human involved. |
| Middle band (about 60-99%) | Surfaced to the human: "holds 87% of the time — rule or variation?" |
| Rare or absent | Discarded. |

The decoy arm is what prunes coincidental invariants: a rule that holds in A but
breaks under an independent re-run of the same system was never structural.
This answers the Daikon over-generation failure mode — dynamic invariant
detectors classically emit far more candidates than a human can triage, and the
decoy arm plus the middle band cut that from both sides.

## Known traps

- Fixed cosine thresholds are invalid. Sentence embeddings are anisotropic;
  unrelated outputs routinely sit at 0.6-0.9 cosine. Either whiten using the
  global corpus of baseline outputs, or rely on permutation and decoy
  calibration — which is valid regardless of anisotropy and costs only power.
- The embedding channel is weak exactly where it matters most: negation,
  numbers, dropped caveats, swapped entities. The NLI channel exists to cover
  that flank. Never ship an embedding-only verdict.
- Templated, low-variety outputs degenerate the embedding channel and the noise
  floor simultaneously. Detect and flag that regime rather than reporting it as
  clean.
