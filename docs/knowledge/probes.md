# Probe suite — current state

What each detection channel can and cannot resolve. Read before changing any
channel, threshold, or stratification rule.

Run: `python scripts/run_probes.py` (`--dry-run` builds pairs without models).
Results land in `results/probes_<run_id>_<config_hash>.json`.

## What the suite is

832 pairs: 16 seeds x 4 subject domains x 4 output shapes x 13 perturbation
categories. 320 meaning-preserving, 512 meaning-breaking. 30-152 words per arm.

Both arms of every pair come from the same renderer and the same seed, so the
only difference is the intended one. **Preserving perturbations change the
rendering and hold the facts fixed; breaking perturbations change the facts and
hold the rendering fixed.** That asymmetry is not a stacked deck — it is the
production situation, where a model swap rewrites the surface of every output
and changes the substance of a few.

| Preserving | Breaking |
|---|---|
| paraphrase (full template rewrite) | polarity (verdict word inverted) |
| reorder (independent facts swapped) | negation (syntactic, per-seed) |
| format (prose to bullets, JSON compacted) | number, unit, temporal, entity |
| synonym (exactly one phrase) | quantifier |
| verbosity (hedging clause added) | omission (material caveat dropped) |

## Why the suite has its own test file

`tests/test_pairs.py` verifies probe construction independently of any channel.
This is not ceremony. On first assembly it caught four construction bugs, three
of them silent:

- the synonym perturbation was a no-op on JSON (its targets only existed in
  prose templates)
- the quantifier perturbation was a no-op on short answers (that template never
  rendered the field)
- the format perturbation was a no-op on all prose (whitespace collapse does
  nothing to single-line text)

Each would have produced a clean, plausible "this channel detects 0% of
quantifier changes in short answers", and it would have gone into the
blind-spot map as a finding. **A broken probe and a blind channel are
indistinguishable in the results table.** Any new perturbation needs a test
that it actually perturbs, before its numbers are read.

A fourth test rejected the original shape design: the shapes spanned only 1.7x
in length, too narrow to separate "blind to meaning" from "diluted by length".
Widened to ~5x (32 to 148 median words) by giving summaries realistic framing
prose that is identical in both arms.

## Findings (run 20260924T022150Z, config eb95f0b802c4660a)

Detection rate is measured at the threshold where the channel false-alarms on
5% of meaning-preserving pairs. AUC is against the pooled preserving
distribution; below 0.5 means the channel scores meaning changes as *more
similar* than rewordings.

### Embedding displacement is anti-correlated with meaning change

Pooled separability AUC: MiniLM-L6 **0.391**, BGE-base **0.440**, E5-base
**0.532**. At or below chance, across three models from three families.

Per category, the worst cases are the ones that matter most (AUC, MiniLM /
BGE / E5): temporal 0.069 / 0.187 / 0.506, quantifier 0.144 / 0.104 / 0.209,
number 0.157 / 0.266 / 0.584, negation 0.228 / 0.304 / 0.375.

The mechanism, in medians (MiniLM): a paraphrase moves the embedding 0.0303; a
changed number, date or negation moves it 0.0018. **Rewording moves the vector
roughly twenty times further than changing the fact.** Only `entity` (59%
detection) and `omission` (33%) clear the noise, and omission only because
deleting a sentence changes length.

### ...but the failure is conditional on surface stability, and that is usable

Scored against a *minimal* preserving baseline — the synonym perturbation,
exactly one phrase changed — the same channels recover:

| channel | AUC vs pooled preserving | AUC vs synonym-only |
|---|---|---|
| MiniLM-L6 | 0.243 | 0.540 |
| BGE-base | 0.306 | 0.614 |
| E5-base | 0.449 | **0.818** |

So the honest statement is not "embeddings are useless". It is: **embedding
displacement separates meaning from surface only when the candidate system's
surface style is stable, and is worse than useless when it is not.** That is a
measurable precondition, not a matter of judgement, and the engine should gate
the channel on it rather than always running it. See ENG gate requirement in
`docs/engine/METHODS.md`.

### NLI contradiction is the primary channel

DeBERTa-v3-base-MNLI: pooled separability AUC **0.938**. At a 5% false-alarm
budget it detects seven of the eight breaking categories at 84-100%:

entity 100%, negation 100%, number 100%, temporal 100%, polarity 98.4%,
quantifier 92.2%, unit 84.4% (n=64 each, Wilson intervals in the results file).

It holds across output length — 100% / 99.1% / 95.5% / 100% for short_answer /
json / reasoning / summary — and across subject domain: 96.4% banking, 96.4%
hospitality, 98.2% logistics, 96.4% technical (n=112 each). That domain
stability is the first evidence bearing on the transfer question, though it is
one system type and four domains, and carries no weight for STD-005 on its own.

**Thresholds must be stratified by shape.** The 5%-FPR threshold ranges from
0.011 (summary) to 0.888 (reasoning) — a factor of eighty. A single global
threshold would be badly wrong for at least two shapes.

### Omission is invisible to contradiction, structurally

NLI detects **0%** of dropped caveats at the 5% budget (AUC 0.535, i.e. chance);
only the summary shape reaches 25%. This is not a weak model. It is what
entailment means: a text with a condition removed is *entailed* by the original,
not contradicted by it. No NLI model will fix this.

Embeddings catch 33% of omissions, and only via length.

**Dropped conditions are a realistic and dangerous regression class, and
neither semantic channel covers them.** This is independent motivation for
induced structural conformance (STD-003) — a field present in 99% of baseline
outputs and suddenly absent is exactly the signal that works here. The one
mechanism the landscape survey found unoccupied is the one the blind-spot map
says we need.

### False alarms worth knowing

Reformatting prose as bullets trips NLI on **18.8%** of pairs — and format
changes are among the most common consequences of a model swap. Paraphrase
trips MiniLM on 20.3%, reorder trips BGE on 17.2%.

## Consequences for the design

1. Channel ordering inverts. NLI is the workhorse; embedding displacement is a
   conditional add-on, not the primary triage. Recorded in HANDOFF §5.
2. The embedding channel needs a style-stability gate before it may contribute.
3. Shape-stratified thresholds are mandatory, not an optimisation.
4. Structural conformance has to carry omission-class regressions alone.
5. Cost rises: a bidirectional cross-encoder is far more expensive per
   comparison than a bi-encoder, which strengthens the case for distilling the
   NLI-based mode clustering once it is the demonstrated bottleneck.

## Known limits of the suite itself

- Perturbations are synthetic and single-fact. Real regressions are messier and
  often combine several.
- One NLI model. The NLI result should not be assumed to hold for other
  checkpoints; the embedding result is stronger because it replicates across
  three families.
- The 5% budget is a convention, not a derived operating point.
- Seeds are English and template-generated. Nothing here speaks to other
  languages or to free-form generation.
