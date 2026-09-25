# Probe suite — current state

What each detection channel can and cannot resolve. Read before changing any
channel, threshold, or stratification rule.

Run: `python scripts/run_probes.py` (`--dry-run` builds pairs without models).
Results land in `results/probes_<run_id>_<config_hash>.json`.

## What the suite is

896 pairs: 16 seeds x 4 subject domains x 4 output shapes x 14 perturbation
categories. 256 preserving, 512 breaking, 128 register. 30-152 words per arm.

Both arms of every pair come from the same renderer and the same seed, so the
only difference is the intended one. **Preserving perturbations change the
rendering and hold the facts fixed; breaking perturbations change the facts and
hold the rendering fixed.** That asymmetry is not a stacked deck — it is the
production situation, where a model swap rewrites the surface of every output
and changes the substance of a few.

| Preserving (facts and stance fixed) | Breaking (a fact changed) | Register (stance changed) |
|---|---|---|
| paraphrase (full template rewrite) | polarity (verdict word inverted) | hedging (qualifier added) |
| reorder (independent facts swapped) | negation (syntactic, per-seed) | overconfidence (certainty added) |
| format (prose to bullets, JSON compacted) | number, unit, temporal, entity | |
| synonym (exactly one phrase) | quantifier, omission | |

### Why register is a third class rather than a verdict

Hedging changes no fact, so labelling it BREAKING makes that bucket
inhomogeneous — every other member is "a fact changed". But labelling it
PRESERVING would call a documented fault class a non-event: **F9 in the frozen
taxonomy is persona and sycophancy drift**, and GPT-4o's case was exactly this,
a register change with no accuracy change where every labelled eval passed.

So it is excluded from both the 5% false-alarm budget and the detection rate,
and reported on its own. Two directions are included, because stance drifts both
ways and the dangerous one is the confident direction.

An earlier version labelled hedging as preserving. The NLI predicate refused to
merge those pairs 80% of the time, which was the first sign the label was doing
work it could not support (MTH-021).

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

## Findings

Embedding channels: run `20260924T022150Z`, config `eb95f0b802c4660a`.
NLI channels: run `20260924T031004Z`, config `592763f4f2a8c4d7`.

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

### Directional entailment closes the omission gap

Run 20260924T031004Z added a second NLI direction and a second checkpoint.

Entailment asymmetry — P(A entails B) minus P(B entails A) — detects dropped
material conditions at **95.3%** [0.87, 0.98], **AUC 0.995**, and is highly
*specific*: 0-3% on every other breaking category. Contradiction and directional
entailment are complementary rather than overlapping. Contradiction carries
seven of eight categories and misses omission completely; directional carries
omission and almost nothing else. **The union covers all eight.**

Both come from one pair of forward passes, so the second channel is
computationally free.

**Signed, not absolute.** The unsigned variant drops omission to 78.1% and picks
up a 25% false-alarm rate on `verbosity` — adding a hedge is also an information
change, in the benign direction. We care about loss, so the sign carries meaning.

### The NLI result is a property of the checkpoint, not of NLI

RoBERTa-large-MNLI reproduced the *direction* of every finding and **none of the
magnitudes**:

| | DeBERTa-v3-base | RoBERTa-large |
|---|---|---|
| contradiction, pooled AUC | 0.938 | 0.897 |
| unit | 84% | **36%** |
| quantifier | 92% | **55%** |
| polarity | 98% | 77% |
| number / temporal | 100% | 84% |
| paraphrase false alarms | 0% | **12%** |
| directional, omission | 95.3% | 65.6% |

Per-category gaps run to 48 points. **The pinned checkpoint is a first-order
design variable**, and this opens a sibling question the study is not built to
answer: the headline claim is that detection transfers across *domains*, and we
now have evidence that it degrades measurably across *instrument checkpoints*.
Say so rather than letting a reader assume otherwise.

### Omission and contradiction — the original finding, now corrected

DeBERTa's contradiction channel detects **0%** of dropped caveats (AUC 0.535,
chance). The structural reason holds: a text with a condition removed is
*entailed* by the original, not contradicted by it.

**But "no NLI model will fix this" was too strong and is now falsified in part.**
RoBERTa detects 28.1% [0.19, 0.40], AUC 0.687 — weak, but above chance. The
original claim generalised a single-checkpoint result into a property of
entailment. Embeddings catch 33%, and only via length.

**The consequence runs against an argument we liked.** This section previously
concluded that structural conformance must carry the omission class alone, and
noted with some satisfaction that the one unoccupied mechanism in the landscape
was also the one the blind-spot map said was load-bearing. Directional
entailment removes that justification. Structural conformance keeps its other
coverage — schema violations, field cardinality, enum domain, language drift,
parse failure, the F7 charset signature — and remains unoccupied per STD-003.
It is no longer the only thing standing between us and a whole fault class, and
the contribution narrative should stop saying it is.

### False alarms worth knowing

Reformatting prose as bullets trips NLI on **18.8%** of pairs — and format
changes are among the most common consequences of a model swap. Paraphrase
trips MiniLM on 20.3%, reorder trips BGE on 17.2%.

### The signed directional channel is two-tailed (MTH-022)

Thresholds from the preserving distribution at 2.5% per tail (lower -0.055,
upper +0.096):

| group | n | median | above upper | below lower |
|---|---|---|---|---|
| preserving | 256 | 0.000 | 2.7% | 2.7% |
| breaking excl. omission | 448 | 0.000 | 1.8% | 4.0% |
| omission | 64 | +0.957 | **98.4%** | 0% |
| hedging | 64 | -0.758 | 0% | **100%** |
| overconfidence | 64 | -0.848 | 0% | **100%** |

One statistic, two tails, two fault classes, and the sign says which: positive
means information was removed, negative means it was added.

`directional_abs` is therefore redundant *and worse* — the absolute value
conflates the tails, fires on both, and distinguishes neither. Dropped.

Caveat that must travel with this: it is **not** a stance detector. Both
register directions go negative because both add a clause, so what is measured
is directional information volume. Whether it separates stance addition from
factual addition is untested.

### Relabelling register recovered a signal

The false alarms previously attributed to `verbosity` were never false alarms —
the channel was correctly detecting a change the suite had mislabelled as a
non-change. Relabelling also fixed the clustering fit: the argmax moved from
0.05 to 0.65 and peak balanced accuracy rose from 0.909 to 0.956, converging on
the threshold that had been chosen by argument alone (MTH-020 append).

## Consequences for the design

1. Channel ordering inverts. NLI is the workhorse; embedding displacement is a
   conditional add-on, not the primary triage. Recorded in HANDOFF §5.
2. The embedding channel needs a style-stability gate before it may contribute.
3. Shape-stratified thresholds are mandatory, not an optimisation.
4. Two NLI channels, one pair of forward passes. Their union covers all eight
   breaking categories; neither does alone.
5. Structural conformance is no longer the sole cover for omission, and the
   contribution narrative must stop claiming it is.
6. The pinned checkpoint is a reportable design variable, not a detail.
7. Format normalisation before scoring is the obvious next engineering step —
   it is the shared 19% false-alarm source across both NLI channels.
8. Cost rises: a bidirectional cross-encoder is far more expensive per
   comparison than a bi-encoder, which strengthens the case for distilling the
   NLI-based mode clustering once it is the demonstrated bottleneck.

## Known limits of the suite itself

- Perturbations are synthetic and single-fact. Real regressions are messier and
  often combine several.
- Two NLI checkpoints, and they disagree by up to 48 points per category. The
  embedding result is the more robust of the two, replicating across three
  families.
- The 5% budget is a convention, not a derived operating point.
- Seeds are English and template-generated. Nothing here speaks to other
  languages or to free-form generation.
