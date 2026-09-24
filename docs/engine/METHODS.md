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
See `docs/knowledge/probes.md` and MTH-011 through MTH-014.

| Channel | Role | Status |
|---|---|---|
| NLI contradiction | **Primary.** Shape-stratified thresholds, mandatory. | Validated on one checkpoint (MTH-013) |
| Structural conformance | **Primary for omission-class**, which no semantic channel covers (MTH-014) | Not built |
| Embedding displacement | **Conditional.** Gated on measured surface stability | Gate not built (MTH-012) |
| Dispersion / mode-share | Collapse and explosion detection | Not built |

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
- Never ship a semantic-only verdict. Omission is invisible to contradiction by
  definition, not by weakness of the model, and structural conformance is the
  only channel that covers it.
- Reformatting is a false-alarm source, not a safe no-op: prose rendered as
  bullets tripped the NLI channel on 18.8% of preserving pairs, and format
  changes are among the most common consequences of a model swap.
- Templated, low-variety outputs degenerate the embedding channel and the noise
  floor simultaneously. Detect and flag that regime rather than reporting it as
  clean.
