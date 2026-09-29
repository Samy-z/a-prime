# What each check can and cannot see

This document reports, for each of a-prime's checks, which kinds of change it
notices and which it is blind to. Read it before changing any check or any
threshold.

To run the measurements yourself:

```bash
python scripts/run_probes.py            # the full measurement, downloads 4 models
python scripts/run_probes.py --dry-run  # build the test pairs only, no models
```

Results are written to `results/probes_<run_id>_<config_hash>.json`.

## How the measurement works

a-prime compares two versions of a system and reports which inputs changed
behaviour. To find out whether it is any good at that, we need cases where we
already know the answer. So the suite contains 896 **pairs of texts**, built by
hand, where we decided in advance what the relationship between the two texts is.

Each pair is generated from a template, and both halves come from the same
template with one deliberate difference. That means nothing varies except the
thing we intended to vary. There are three kinds of pair.

| Kind | What differs | What a good check should do |
|---|---|---|
| Preserving (256 pairs) | only the wording | ignore it |
| Breaking (512 pairs) | a fact | flag it |
| Register (128 pairs) | how confident the text sounds | reported separately, see below |

Concretely, a preserving pair might render the same facts as prose in one half and
as a bulleted list in the other. A breaking pair keeps the wording and changes
"42,000" to "47,000", or flips "approved" to "declined", or deletes a sentence
stating a condition. A register pair adds a hedge such as "based on the
information available at the time of review", which changes no fact but changes
how committed the text sounds.

The eight kinds of breaking change are: a flipped decision, an inserted
negation, a changed number, a changed unit, a changed date, a swapped name, a
changed quantifier such as "all" becoming "some", and a deleted condition. The
last of those is called omission, meaning content that was present in the old
output and is missing from the new one, and it turns out to be the hard case.

Pairs span 16 source templates, four subject areas (banking, logistics,
hospitality, technical operations) and four output shapes (a short answer, a JSON
object, a multi-sentence summary, a numbered list of reasoning steps). Text length
runs from 30 to 152 words.

### The asymmetry is deliberate

Preserving pairs change a lot of wording and no facts. Breaking pairs change one
fact and no wording. That is not a stacked deck in either direction: it is what
actually happens when you swap a model. The new model rewrites the surface of
every output and changes the substance of a few, and the whole difficulty is
telling those apart.

### Why register is a third category rather than a verdict

Adding a hedge changes no fact, so calling it "breaking" would make that group
inconsistent, since every other member of it is a changed fact. But calling it
"preserving" would be worse. A change in how confident a model sounds, with no
change in accuracy, is a documented real-world failure: when GPT-4o became
noticeably sycophantic in April 2025, every labelled test its developers ran
passed, and it was rolled back four days later after users complained.

So register pairs are measured and reported on their own, excluded from both the
false-alarm budget and the detection rate. Both directions are included, adding
hedging and adding unwarranted confidence, because confidence drift is the more
dangerous one.

An earlier version of the suite labelled hedging as preserving. The model we use
to judge text equivalence refused to treat those pairs as equivalent 80% of the
time, which was the first hint the label was wrong.

## Why the pairs have their own tests

`tests/test_pairs.py` checks that the pairs are built correctly, without
involving any of the detection machinery. This is not ceremony. On first assembly
it found four construction bugs, three of them silent:

- **The synonym substitution did nothing to JSON output.** Its target phrases only
  existed in the prose templates, so for JSON the two halves of the pair were
  identical.
- **The quantifier change did nothing to short answers.** That template never
  rendered the quantifier field at all, so there was nothing to change.
- **The formatting change did nothing to any prose.** It collapsed whitespace,
  which has no effect on text that was already on one line.

Any of those would have produced a clean, plausible result such as "this check
detects 0% of quantifier changes in short answers", and it would have been
recorded as a finding about the check. **A broken test pair and a blind check are
indistinguishable in the results table**, which is why the pairs are verified
separately. Every new kind of pair needs a test that it actually differs, before
any number derived from it is read.

A fourth test rejected the original design outright. The four output shapes
originally spanned only 1.7 times in length, which is too narrow to separate "the
check cannot see meaning" from "the check works but the change was diluted in a
long output". The shapes were widened to about 5 times, from 32 to 148 median
words, by giving summaries realistic filler that is identical in both halves.

## How to read the numbers below

Two figures recur.

**Detection rate** is measured at a fixed false-alarm budget. We set the
threshold at the point where the check wrongly flags 5% of preserving pairs, then
ask what share of breaking pairs it catches at that same threshold. This matters
because a check is deployed at a false-alarm budget, not at an operating point
chosen after seeing the answers.

AUC, area under the curve, is the probability that a randomly chosen breaking
pair scores higher than a randomly chosen preserving pair. 1.0 is perfect, 0.5 is
a coin flip, and **below 0.5 means the check scores meaning changes as more
similar than rewordings**, which is worse than useless.

Measurements come from two runs: embedding results from run `20260924T022150Z`,
and results from the text-inference models from run `20260924T031004Z`.

## Finding 1: comparing embeddings performs worse than chance

An embedding turns a piece of text into a list of numbers, positioned so that
texts with similar meaning sit close together. Comparing the distance between two
outputs is the obvious way to ask whether they differ, so it was the design's
original primary check.

Pooled AUC across all categories: 0.391 for MiniLM-L6, 0.440 for
BGE-base, 0.532 for E5-base. Three models from three different families, all
at or below a coin flip.

The worst categories are the ones that matter most. AUC per category, for the
three models in the same order:

| Change | MiniLM | BGE | E5 |
|---|---|---|---|
| changed date | 0.069 | 0.187 | 0.506 |
| changed quantifier | 0.144 | 0.104 | 0.209 |
| changed number | 0.157 | 0.266 | 0.584 |
| inserted negation | 0.228 | 0.304 | 0.375 |

The mechanism is mundane. Measured as median distances with MiniLM, rewording a
sentence moves it 0.0303, while changing a number, a date or a negation inside it
moves it 0.0018. Rewording moves the text roughly **twenty times further than
changing the fact**. Only two categories clear the noise: a swapped name at 59%
detection, and a deleted condition at 33%, and the latter only because deleting a
sentence changes the length.

### It recovers when the wording is stable, which makes it salvageable

The measurements above compare breaking pairs against all preserving pairs,
including full rewrites. If instead we compare them against only the mildest
preserving change, a single substituted phrase, the same models recover:

| Model | AUC against all preserving pairs | AUC against single-phrase changes only |
|---|---|---|
| MiniLM-L6 | 0.243 | 0.540 |
| BGE-base | 0.306 | 0.614 |
| E5-base | 0.449 | 0.818 |

So the honest conclusion is not that embeddings are useless. It is that comparing
embeddings separates meaning from wording only when the new system phrases things
much like the old one, and is worse than useless when it does not. That condition
is measurable rather than a matter of judgement, so the check now runs behind a
gate that measures it and switches the check off when it fails. The gate is
described in `docs/engine/METHODS.md`.

## Finding 2: contradiction detection carries seven of the eight fact changes

The replacement primary check uses a model trained on **natural language
inference**, the task of deciding whether one piece of text follows from,
contradicts, or is unrelated to another. We ask it whether the old output and the
new output contradict each other.

Using DeBERTa-v3-base-MNLI, pooled AUC is 0.938. At the 5% false-alarm
budget it detects seven of the eight breaking categories, 64 pairs each:

| Change | Detected |
|---|---|
| swapped name, inserted negation, changed number, changed date | 100% |
| flipped decision | 98.4% |
| changed quantifier | 92.2% |
| changed unit | 84.4% |

It holds up across output length, detecting 100%, 99.1%, 95.5% and 100% for short
answers, JSON, reasoning lists and summaries respectively. It also holds across
subject area: 96.4% for banking, 96.4% for hospitality, 98.2% for logistics and
96.4% for technical operations, 112 pairs each. That stability across subject
matter is the first evidence bearing on the project's central question, though it
covers one kind of system and four subjects, so on its own it settles nothing.

**Thresholds have to be set per output shape.** The threshold that produces a 5%
false-alarm rate ranges from 0.011 for summaries to 0.888 for reasoning lists, a
factor of eighty. A single threshold applied to everything would be badly wrong
for at least two of the four shapes.

## Finding 3: the eighth category needs a different question

Contradiction detection catches 0% of deleted conditions, at an AUC of 0.535,
which is chance. The reason is structural rather than a weakness of the model: a
text with a condition removed does not contradict the original, it simply says
less. Asking "do these contradict?" gets a truthful "no".

Asking a different question fixes it. Instead of contradiction, measure
**asymmetry in entailment**: how much more the old output implies the new one than
the reverse. On deleted conditions this detects 95.3%, with a 95% confidence
interval of 0.87 to 0.98 and an AUC of 0.995. It is also highly specific,
scoring 0 to 3% on every other breaking category.

The two questions are complementary rather than overlapping. Contradiction covers
seven categories and misses deletion entirely; entailment asymmetry covers
deletion and almost nothing else. Together they cover all eight. Both come from
the same pair of model calls, so the second question costs nothing extra.

**Use the signed value, not its magnitude.** Taking the absolute value drops
deletion detection to 78.1% and introduces a 25% false-alarm rate on added
hedging, because adding a hedge is also a change in information content, in the
opposite direction. The direction is the informative part.

### Read at both ends, one number names two different faults

Setting thresholds from the preserving pairs at 2.5% in each tail gives a lower
bound of −0.055 and an upper bound of +0.096:

| Group | Pairs | Median | Above upper | Below lower |
|---|---|---|---|---|
| preserving | 256 | 0.000 | 2.7% | 2.7% |
| breaking, excluding deletion | 448 | 0.000 | 1.8% | 4.0% |
| deleted condition | 64 | +0.957 | 98.4% | 0% |
| added hedging | 64 | −0.758 | 0% | 100% |
| added confidence | 64 | −0.848 | 0% | 100% |

A strongly positive value means information was removed. A strongly negative
value means it was added. The sign identifies which happened, which is exactly
what taking the absolute value destroyed.

One caveat has to travel with this result: it is not a detector for
confidence or tone. Both register directions score negative because both add a
clause, so what is being measured is the direction of information volume. Whether
it can separate an added hedge from an added fact is untested.

## Finding 4: these numbers describe a model, not a method

Substituting RoBERTa-large-MNLI, a different model trained for the same task,
reproduced the direction of every finding above and none of the magnitudes:

| | DeBERTa-v3-base | RoBERTa-large |
|---|---|---|
| contradiction, pooled AUC | 0.938 | 0.897 |
| changed unit | 84% | 36% |
| changed quantifier | 92% | 55% |
| flipped decision | 98% | 77% |
| changed number and date | 100% | 84% |
| false alarms on rewording | 0% | 12% |
| deletion, via entailment asymmetry | 95.3% | 65.6% |

Individual categories differ by as much as 48 percentage points. The judging
model is therefore a first-order design choice rather than an implementation
detail, and every figure in this document should be read as describing that
model.

It also raises a question the study is not designed to answer. The project's
central claim is about whether detection survives a change of subject domain, and
we now have direct evidence that it degrades measurably across a change of
judging model. That should be stated rather than left for a reader to notice.

One correction belongs here. An earlier version of this document claimed no model
of this type could ever detect deleted conditions via contradiction. RoBERTa
detects 28.1%, confidence interval 0.19 to 0.40, AUC 0.687. Weak, but above
chance, so the original claim generalised a single measurement into a property of
the technique. For comparison, embeddings catch 33% of deletions, and only by
noticing the change in length.

## Finding 5: known sources of false alarms

- **Reformatting prose as a bulleted list** trips contradiction detection on
  18.8% of preserving pairs. This is the most important one, because changing
  formatting is among the most common things a new model does.
- Rewording trips embedding comparison with MiniLM on 20.3% of preserving
  pairs, which is consistent with Finding 1.
- **Reordering two independent sentences** trips embedding comparison with
  BGE-base on 17.2% of preserving pairs.

## What these findings changed in the design

1. **The order of the checks inverted.** Text inference became the primary check
   and embedding comparison a conditional extra, which is the reverse of the
   original design.
2. **Embedding comparison only runs behind a gate** that measures whether the two
   systems phrase things similarly.
3. **Thresholds are set per output shape**, because the correct threshold varies
   by a factor of eighty across shapes.
4. **Two questions are asked of one pair of model calls**, contradiction and
   entailment asymmetry, because their union covers all eight fact changes and
   neither does alone.
5. **Rules inferred from output structure are no longer the only cover for
   deleted conditions**, which they were believed to be before entailment
   asymmetry was measured.
6. **The judging model is reported as a design variable**, not buried as a
   detail.
7. **Text is normalised before scoring**, since formatting differences were the
   largest shared source of false alarms.
8. **Cost rose.** A model that reads two texts together is far more expensive per
   comparison than one that encodes each separately, which strengthens the case
   for eventually training a smaller, cheaper stand-in.

Relabelling register pairs had an unplanned benefit. The false alarms previously
blamed on hedging were never false alarms: the check was correctly detecting a
change the suite had mislabelled as a non-change. Relabelling also improved the
fitted threshold for judging text equivalence, moving the best value from 0.05 to
0.65 and raising accuracy from 0.909 to 0.956, which converged on a value that
had previously been chosen by argument alone.

## Limits of this measurement

- **The changes are synthetic and each alters one thing.** Real regressions are
  messier and usually combine several changes at once, so these figures are
  probably optimistic.
- **Only two judging models were tested, and they disagree by up to 48 points per
  category.** The embedding finding is the more trustworthy of the two, because
  it replicated across three model families rather than one.
- **The 5% false-alarm budget is a convention, not a derived figure.** A
  different budget would move every detection rate in this document.
- **Everything is English and generated from templates.** Nothing here says
  anything about other languages, or about free-form text that no template
  produced.
