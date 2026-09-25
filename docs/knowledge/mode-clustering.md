# Mode clustering and normalisation — current state

`src/aprime/normalize.py`, `src/aprime/clustering.py`.
Fit the threshold with `python scripts/fit_clustering.py`.

Every statistic in `stats.py` treats an output cloud as a distribution over
modes. A mode used to be an exact string — correct for structured output,
useless for prose, where two paraphrases of one answer count as two modes and a
system that merely rewords looks like a system that changed. This is what
unblocks free text.

## Normalisation

Runs before scoring and before clustering. Strips markdown structure, list
markers and emphasis; unifies quotes, dashes and whitespace; canonicalises JSON
by sorting keys.

**The line to hold: remove presentation, never content.** Anything more
aggressive erases the differences the detector exists to find, and that failure
is invisible — it shows up as a clean report, not an error.

JSON that fails to parse is **not** silently repaired. It falls through to text
normalisation, because an output that stopped being valid JSON is a real
regression (F3) and belongs to the structural channel, not to a fixer.

### What it actually bought (MTH-019)

`format` false alarms fell from 18.8% to 1.6% on contradiction and 18.8% to 0%
on directional. But the total false-alarm rate is **pinned at 5% by the
threshold definition** — it did not fall, it relocated, to `synonym` (0% to
14.1%) and `paraphrase` (0% to 6.2%).

The gain is detection at a fixed budget: unit 84.4% to 100%, quantifier 92.2% to
100%, omission-on-contradiction 0% to 18.8%, pooled AUC 0.938 to 0.945.

Report it that way. "Normalisation cut false alarms by 17 points" is false, and
it is the kind of false that survives review because it sounds right.

Carry the caveat too: the residual false alarms moved to minimal lexical change,
which is harder to normalise away than formatting.

## Clustering

Two outputs are the same mode when **each entails the other** above a threshold
— the bidirectional test from the semantic-entropy literature. Both directions
are required: a text with a condition removed is entailed by the original in one
direction only, and merging on one-way entailment would undo MTH-016 outright.

### The relation is not transitive, and that is handled rather than hidden

A may be equivalent to B and B to C while A and C are not, so the partition
depends on the order strings are considered in. Two mitigations: strings are
ordered deterministically (most frequent first, ties lexical), and each
candidate is compared only to cluster *representatives*.

Clouds being compared are **clustered jointly**. Clustering separately would
produce two unrelated label spaces and make mode-share distance meaningless.

### Cost

The predicate is a cross-encoder forward pass and it is the dominant cost of the
detector. Normalisation collapses k samples to a handful of distinct strings
first, and only distinct strings are ever compared; comparison is against one
representative per cluster, not every member. `ClusterResult.predicate_calls`
records what was actually spent — that number is the justification for
distilling the predicate later, so it is measured rather than asserted.

### Threshold: 0.7, chosen on an asymmetry argument (MTH-020)

Fitted against 320 equivalent and 512 different probe pairs. Pooled balanced
accuracy peaks at 0.05 (0.909) and is flat to 0.65 (0.893), so the argmax sits
inside the noise — and it is driven by `verbosity`, a preserving category whose
label is arguable, since adding a hedge does change what is claimed.

Merge rates at 0.7:

| Preserving (want high) | | Breaking (want low) | |
|---|---|---|---|
| format | 100% | negation, number, temporal | 0% |
| paraphrase | 98% | polarity, entity, quantifier | 0% |
| synonym | 95% | unit | 3% |
| reorder | 75% | **omission** | **9.4%** |
| verbosity | 20% | | |

**Why lean high.** The two error types do not cost the same thing. Wrongly
*splitting* a preserving pair inflates the noise floor — but it inflates the
decoy arm's floor identically, so the threshold compensates and validity
survives; only power is lost. Wrongly *merging* a breaking pair is systematic
blindness that applies to targets and decoys alike, and nothing absorbs it.
Validity outranks power, so the threshold leans high. At the argmax, 40.6% of
omission pairs merge.

**This is an argument, not a measurement.** The proper resolution is end-to-end
detection power across thresholds on a free-text system under test. Replace it
when that exists.

## Known limits

- `reorder` plateaus near 76% merged across the entire threshold grid. Swapping
  two independent sentences changes entailment for this model about a quarter of
  the time, and no threshold fixes it.
- `verbosity` at 20% merged is arguably the model being right and our label
  being wrong. Worth revisiting the probe label rather than the threshold.
- One checkpoint. MTH-017 showed NLI findings do not carry magnitudes across
  checkpoints, and nothing here has been re-fitted on the second one.
- The predicate has not yet been run inside the detector on real clouds, so the
  cost figures are structural expectations rather than measurements.
