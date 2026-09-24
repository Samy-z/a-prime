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

## Channel ordering — measured, not assumed

The design originally treated embedding displacement as the primary triage
signal with NLI as a supporting flank. The week-0 probe suite inverted that.
See `docs/knowledge/probes.md` and MTH-011 through MTH-017.

| Channel | Role | Status |
|---|---|---|
| NLI contradiction | **Primary.** Carries 7 of 8 breaking categories. Shape-stratified thresholds, mandatory. | MTH-013, checkpoint-dependent (MTH-017) |
| NLI directional entailment | **Primary for omission**, 95.3% at AUC 0.995, and specific — near-zero on everything else. Signed, not absolute. | MTH-016 |
| Structural conformance | Schema, cardinality, enum domain, language drift, parse failure, F7 charset signature | Not built. No longer solely load-bearing for omission (MTH-014 correction) |
| Embedding displacement | **Conditional.** Gated on measured surface stability | Gate not built (MTH-012) |
| Dispersion / mode-share | Collapse and explosion detection | Not built |

Both NLI channels come from a **single pair of forward passes** — contradiction
is the max over directions, directional is the difference in entailment. Running
them as separate models would double the dominant cost for nothing.

The two are complementary, not redundant: contradiction misses omission
entirely, directional catches almost nothing *but* omission. Their union covers
all eight breaking categories in the probe suite.

**The embedding gate is a hard requirement, not a refinement.** Ungated, the
channel is anti-correlated with meaning change — it scores a reworded output as
more changed than a flipped date (MTH-011). The engine must measure surface
drift between baseline and candidate and refuse to let the channel contribute
above the level at which it was shown to work. A channel that is worse than
chance is worse than absent, because it will be trusted.

## Known traps

- Fixed cosine thresholds are invalid. Sentence embeddings are anisotropic;
  unrelated outputs routinely sit at 0.6-0.9 cosine. Either whiten using the
  global corpus of baseline outputs, or rely on permutation and decoy
  calibration — which is valid regardless of anisotropy and costs only power.
- Thresholds must be stratified by output shape. The measured 5%-FPR threshold
  for the NLI channel spanned 0.011 to 0.888 across four shapes, a factor of
  eighty. A single global threshold is wrong for at least two of them.
- Never ship a single-channel verdict. Contradiction alone misses omission
  entirely; directional entailment alone misses the other seven categories.
  Coverage is a property of the union, not of any one channel.
- Reformatting is a false-alarm source, not a safe no-op: prose rendered as
  bullets tripped the NLI channel on 18.8% of preserving pairs, and format
  changes are among the most common consequences of a model swap. It is the
  shared weak point of **both** NLI channels (19% each) and the obvious target
  for normalisation before scoring.
- The pinned NLI checkpoint is a first-order variable, not an implementation
  detail. A second checkpoint reproduced every direction and no magnitude, with
  per-category gaps up to 48 points (MTH-017). Do not treat a number measured on
  one checkpoint as a property of the channel.
- Templated, low-variety outputs degenerate the embedding channel and the noise
  floor simultaneously. Detect and flag that regime rather than reporting it as
  clean.
