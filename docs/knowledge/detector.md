# The detector — current state

`src/aprime/detect.py`. Everything composed into one comparison.
Demo: `python scripts/demo_detect.py`.

    record three arms -> dedup -> normalise -> cluster jointly
      -> score (mode-share, dispersion, novel-mode, NLI contradiction,
                NLI directional both tails, embedding if gated in)
      -> select per channel, stratified by baseline output shape
      -> check induced structural conformance
      -> assemble

## Two properties of the composition

**Every channel is scored against its own decoys.** A-vs-A_prime goes through
exactly the same clustering, normalisation and statistic as A-vs-B. A channel
that is noisy, mis-calibrated or outright broken produces noisy decoys too, so
its threshold rises and it reports nothing rather than reporting nonsense. That
is what makes it safe to add a channel whose behaviour is not fully understood —
and it is why the embedding channel, which is anti-correlated with meaning
change when ungated, cannot do real damage even if the gate is wrong.

**No channel votes.** Findings are reported per channel, never summed. Combining
would require weights; weights would be fitted; fitting them outside a
leave-one-system-out fold is what MTH-009 forbids. The reader sees which channel
fired and decides.

## Measured end to end

300 inputs, k=12, 30 genuinely changed, q=0.10, model-free path:

| | |
|---|---|
| flagged | 29 of 300 |
| realised FDR | **0.034** against a 0.10 budget |
| recall | **28/30 = 93%** |
| interleaving gap | 1 |
| conformance | 8 candidates, 7 hard, 1 discarded |

The dispersion channel found nothing and reported a threshold of `inf` — the
empty-selection behaviour working as intended. A channel with no qualifying
threshold says so rather than lowering its bar until it finds something.

## Deliberate behaviours worth knowing

- **Inputs missing an arm are dropped, not imputed.** A missing arm has no decoy
  and therefore no calibrated threshold, and a number without a threshold is
  worse than a gap.
- **Skipped channels say why.** "no NLI model supplied" appears in the report
  rather than the channel silently contributing nothing.
- **The embedding channel is suppressed wholesale** when surface drift exceeds
  the gate on more than half the inputs, and per-input where it exceeds on some.
- **A run crossing midnight UTC is called out** in the notes, because at least
  one common chat template interpolates the date into a hidden system prompt
  (BCH-009).
- **The directional channel is folded to its absolute value for selection**,
  because selection needs one tail — but the signed value is what appears in the
  finding, so the sign still names the fault (MTH-022).

## Known limits

- Never run against a real system. Every number above is from the stub.
- The stub's outputs are short strings, so every input stratifies as `short` and
  the stratification machinery is exercised but not stressed.
- Conformance is corpus-level only; the contract is a property of the system,
  not of an input.
- The embedding channel's cloud statistic is a centroid distance, which is the
  wrong summary for a multimodal cloud (MTH-005). It is kept because it is
  nearly free and because the decoy arm bounds the damage, not because it is
  right.
