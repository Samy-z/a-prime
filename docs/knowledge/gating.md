# Surface-drift gating and stratification — current state

`src/aprime/gating.py`, plus `select_stratified` in `src/aprime/fdr.py`.

## The embedding gate (MTH-012)

Embedding displacement is not merely weak — measured across three model families
it is **anti-correlated** with meaning change. A paraphrase moves the vector
about twenty times further than a changed number, date or negation, and pooled
separability sits at or below chance (MTH-011).

It recovers to AUC 0.54 / 0.61 / 0.82 when the comparison baseline is a minimal
surface change rather than a full rewrite. So the channel is usable exactly when
the candidate's surface style is stable, and **worse than useless when it is
not** — a channel below chance is worse than an absent one, because it will be
trusted.

`surface_drift()` measures that precondition: bag-of-words Jaccard distance
between the two clouds pooled. 0 is identical vocabulary, 1 is no shared words.
Deliberately crude, because its job is to measure the confound rather than the
signal, and it must be blind to meaning to do that honestly.

Two properties it has to have, both tested:

- **Reformatting alone registers zero drift.** Normalisation already handles
  presentation; double-counting it would gate the channel off for the wrong
  reason.
- **A one-phrase swap drifts strictly less than a full rewrite.** That ordering
  is the entire basis of the gate — it is the difference between the regime the
  channel survives and the regime it fails in.

**The 0.25 default threshold is provisional.** It has not been fitted against
the probe suite the way the clustering threshold was (MTH-020), and it should
be, by measuring where synonym-level pairs separate from paraphrase-level ones.
Until then it is a guess, and it is labelled as one.

## Shape inference and stratification

The measured 5%-FPR threshold for the NLI channel ranged from **0.011 to 0.888**
across four output shapes — a factor of eighty. One global threshold is badly
wrong for at least two of them.

A domain-agnostic detector is not told what shape its outputs are, so
`infer_shape()` derives it from structure alone: `json` (parses), `list` (two or
more list markers), `short` (<= 45 words), `prose`. JSON is tested first because
it is the only unambiguous case.

**Shape comes from the baseline arm, never the candidate.** MTH-004 forbids
stratifying on something derived from the quantity being measured, and there is
a sharper reason here: if the candidate's shape chose the stratum, then a
candidate that *changed shape* would move itself into a different bucket,
hiding the change inside a threshold picked to accommodate it.

`select_stratified()` then runs target-decoy selection within each stratum, with
its own threshold and its own decoys, so FDR is controlled inside each. Strata
below `min_stratum` (default 30) are pooled into one remainder group rather than
given a threshold estimated from too little data — a threshold fitted to fifteen
decoys is a guess wearing a number's clothes.

## Known limits

- The gate threshold is unfitted, as above.
- `surface_drift` is bag-of-words, so it is blind to reordering. Two outputs
  with identical vocabulary in a different order register zero drift. Whether
  that matters depends on whether reordering correlates with the regime shift,
  which is unmeasured.
- Shape inference has four buckets chosen by inspection, not by clustering the
  observed distribution. A system whose outputs straddle a boundary will
  stratify unstably.
- Neither has run inside the detector on real outputs.
