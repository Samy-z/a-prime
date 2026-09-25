# engine — LEDGER

Append-only settled findings about the detector implementation. Prefix
`ENG-###`. Never edit an entry in place; correct it with a dated append below.
**Grep this file before investigating anything.**

Entry format: id, date, finding, consequence, evidence, reopen-if.

---

> Statistical constraints binding this seat are settled in
> `docs/methods/LEDGER.md`. Read MTH-002, MTH-005, MTH-006 and MTH-007 before
> writing any comparison code.

## ENG-001 — Replay is grouped by input, not by sample index
**Date:** 2026-09-25
**Finding:** All k*3 calls for one input share a prompt prefix, so a server with
prompt caching pays prefill once per input instead of once per call. On the
measured hardware that is the difference between roughly twenty days of prefill
and a few hours — larger than any other scheduling choice available (BCH-010).
**Why it does not weaken MTH-015:** that guarantee is about the *triple*. A,
A_prime and B for one sample must share conditions, and grouping puts them
closer together in time, not further apart. The triple stays atomic under both
schedules, with a test asserting it.
**What it does change:** grouped, an input's k samples come from one short
window rather than across the whole run, so the noise floor measures
short-timescale variability. That is acceptable because B for that input sits in
the same window and the comparison stays internally consistent — but the floor
no longer captures drift across the run.
**Mitigation:** every sample carries a wall-clock `ts`;
`Recording.wallclock_span_s()` reports how far apart the two timescales are, and
`spans_utc_date_boundary()` flags the specific case BCH-009 found, where a
template interpolates the date into a hidden system prompt.
**Consequence:** `group_by_input=True` is the default. `False` remains available
and costs the prefill.
**Evidence:** throughput measurements in BCH-008/BCH-010; scheduling tests in
`tests/test_resume.py`.
**Reopen if:** a serving stack without prefix caching is adopted, which removes
the benefit and restores the case for spreading samples across the run.

## ENG-002 — Exact-match clustering saturates on any text-modifying fault
**Date:** 2026-09-25
**Finding:** A severity titration over six injections at severities 0.10 / 0.25
/ 0.50 / 0.90 (120 inputs, k=12, q=0.10, realistic multi-sentence outputs)
returned **100% recall and 0% false alarms in every one of the 24 cells**,
including the lowest rung.

That is not a result, it is a saturated instrument. Under exact-match
clustering any injection that alters the output string produces a mode the
baseline never emitted, so mode-share distance and novel-mode mass both go to
1.0 regardless of how much text changed. The ladder measures whether the string
changed, never how much.
**Consequence, and it splits by output type.** For **structured output** this
behaviour is arguably correct — a schema is either honoured or it is not, and
"any change matters" is the right posture. For **prose** it is useless, and a
severity claim derived from the exact-match path would be an artifact of the
clustering rather than a property of the detector.

So: the exact-match path can validate FDR control, which it did (MTH-018), and
**cannot produce a minimum-detectable-severity figure**. BCH-004 requires those
figures, so they must come from the semantic path.
**Evidence:** `results/titration_20260925T043826Z_ac37a9c464904ea5.json`,
`scripts/titration.py`.
**Reopen if:** never for exact match. The semantic run is the measurement that
matters and is pending.

## ENG-003 — Clustering is recomputed three times per comparison; counted once
**Date:** 2026-09-25
**Finding:** `detect()` calls `cluster_jointly` once per statistic, so the same
partition is derived three times per comparison. With exact-match clustering
that is free. With the NLI predicate it triples the dominant cost of the entire
detector.

The reported cost counts only the first pass, because the three produce
identical partitions and counting all three would treble a figure the caller
incurs once conceptually. That makes the reported number honest about the work
that *needs* doing and silent about waste, which is the wrong way round.
**Consequence:** cluster once per (input, arm-pair) and pass the partition to
all three statistics. Recorded as pressure rather than fixed, because the fix
touches the detector's inner loop and the semantic titration currently running
would have to be re-run against the change.
**Measured meanwhile:** on the exact-match path over 300 inputs at k=12,
normalisation collapsed **14,400 samples to 1,580 distinct strings (11%)**.
That 9x reduction is what makes a cross-encoder predicate affordable at all,
and it is measured rather than hoped for.
**Evidence:** `scripts/demo_detect.py` cost line.
**Reopen if:** fixed — then this entry gets a dated append saying so.

## ENG-004 — Semantic clustering produces real gradation, and hides F7 entirely
**Date:** 2026-09-25
**Finding:** Re-running the titration with the NLI predicate (30 inputs, k=8,
q=0.10, realistic 152-word outputs) gave the gradation exact match could not
(ENG-002). All curves monotone, 0% false alarms throughout:

| fault | sev 0.10 | 0.50 | 0.90 | caught by |
|---|---|---|---|---|
| refusal | 100% | 100% | 100% | channels + conformance |
| output_truncation | 96.7% | 100% | 100% | channels + conformance |
| omission | 73.3% | 100% | 100% | channels |
| script_corruption | 0% | 50% | 86.7% | **conformance at every severity** |
| unicode_escape | 0% | 0% | 0% | **conformance at every severity** |
| verbosity | 0% | 0% | 0% | length rule only |

**Two things the channel column alone would have got wrong.**

First, the recall figure counts only per-input findings, and **conformance is
corpus-level** — it reports "the system broke this rule on N of M outputs", not
"input X changed". So `unicode_escape` reads 0% while `no_unicode_escape [F7]`
fired at every severity, and `script_corruption` reads 0% at the lowest rung
while `script_subset(('LATIN',))` fired there too. The detector was not blind;
the metric was looking in one of two places.

Second, and this is the designed division of labour working: **semantic
clustering actively hides F7**. Appending `\uC548\uB155` does not change what a
text entails, so the NLI predicate merges the corrupted output with the clean
one — correct semantically, useless operationally. Exact-match clustering caught
it trivially. Structural conformance is not a supplement here, it is the only
thing standing between the detector and a whole fault class, exactly as the
blind-spot map predicted.
**Consequence:** coverage must be assessed over channels **and** conformance
together. Reporting either alone misstates it in opposite directions.
**`verbosity` is genuinely near-invisible**, caught only incidentally by a tight
length bound. A 12-word hedge inside 152 words is diluted past the predicate's
resolution — the dilution effect the probe suite's shape ladder was built to
measure, now showing up in the detector.
**Evidence:** `results/titration_20260925T044050Z_2a7802f548686e8d.json`.
**Reopen if:** a semantic predicate is found that preserves charset sensitivity,
which would change the division of labour.

## ENG-005 — The stub's decoy arm is too clean to exercise rule pruning
**Date:** 2026-09-25
**Finding:** `word_count_range(133, 152)` was induced as a **hard** invariant and
fires on every injected fault, including ones that change nothing about meaning.
It is a coincidental rule that survived the decoy prune.

The reason is the stub: A and A_prime share an identical behaviour table, so
A_prime reproduces A's word counts exactly and a range fitted tight to A is
never contradicted. In a real system A_prime would vary, the range would widen
or be demoted to the band, and the rule would not reach `hard`.
**Consequence:** the decoy pruning mechanism — the answer to Daikon
over-generation and one of the two mechanisms the project claims as novel — is
**not being exercised by the current stub**, and every "0 knocked down by the
decoy arm" reading so far is an artifact of that, not evidence the pruning is
unnecessary.
**Action:** the stub needs a mode of within-system variation that A_prime
expresses differently from A — length jitter at minimum. Until then, no claim
about rule pruning may rest on stub evidence.
**Evidence:** every titration row shows the same `word_count_range` violation.
**Reopen if:** fixed, with a dated append.

## ENG-005 — CORRECTION (dated append, 2026-09-25)
ENG-005 called `word_count_range` a coincidental rule that survived the decoy
prune and "fires on every injected fault, including ones that change nothing
about meaning", implying a false-positive generator. **That was wrong, and the
diagnostic that should have preceded the claim shows the opposite.**

Measured, 40 inputs, k=8, 320 samples per arm:

| | range | support A | support A' | support on unchanged B | violations on unchanged B |
|---|---|---|---|---|---|
| no jitter | 133-152 | 1.0000 | 1.0000 | 1.0000 | **none** |
| jitter 0.4 | 133-160 | 1.0000 | 1.0000 | 1.0000 | **none** |

It fires **zero times on an unchanged candidate**. Under injected verbosity it
fires at 66.3% without jitter and 17.5% with. So it is a legitimate detector for
the one fault class the semantic channels miss entirely — not noise.

**Jitter does work**, just not the way the entry predicted. It widens the
induced range, which costs sensitivity (66% to 17.5%) and buys honesty: the
tight range was overfitted to one sample of A, and the wider one is what the
system's real variability supports. The trade is the right way round.

**What stands from ENG-005:** the decoy pruning mechanism is still not exercised
by the realistic stub — but for a better reason than stated. There is no
coincidental rule here *to* prune. Every induced rule genuinely holds on both
arms. The mechanism is unit-tested and demonstrably works
(`test_decoy_arm_knocks_down_a_coincidental_rule`); it simply has nothing to do
in this scenario.

**Hypothesis worth testing later:** Daikon's over-generation problem may be
milder at this sample size than its reputation suggests. With 320 baseline
samples a tight-fitted rule is mostly not coincidental, because 320 draws
already explore the range. If that holds, the middle band matters more than the
decoy prune, and the contribution should be described accordingly.
**Lesson recorded against process, not the finding:** ENG-005 asserted a
false-positive claim without running the one-line check that would have refuted
it. The check took thirty seconds.
