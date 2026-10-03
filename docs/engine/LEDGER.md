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


## ENG-006 — First recorded pressure on the adapter boundary, not acted on
**Date:** 2026-09-30
**Finding:** MTH-023 requires the recorder to warn when both baseline arms are
configured with the same pinned seed, because that configuration silently
produces confident meaningless FDR numbers. Doing that properly would mean the
recorder can see a system's sampling configuration, and the adapter Protocol
deliberately carries no such thing: a detector that needs to inspect a
stranger's sampling options is not the detector being sold. The boundary's own
docstring says to record the pressure rather than concede to it.

**Not conceded.** `decoy_independence_warnings` duck-types for a `seed`
attribute on the system, on a transport the system holds, or in a `sampling`
dict, and stays silent when it finds none. Systems built in this repo are
checked; a stranger's system is not, and cannot be. The Protocol is unchanged.

**What this costs.** The guard is a courtesy, not a guarantee, and its silence
does not mean a run is sound. That is the honest position and it is why the
check warns rather than certifying. Anyone reading a clean run as verified has
misread it.

**The pressure is real and will recur.** Every downstream check that wants to
validate a run's configuration rather than its outputs will want this same
access. Three such requests should prompt a design conversation about a separate
optional capability interface, deliberately not part of `SystemUnderTest`, rather
than three more duck-typed probes.
**Evidence:** `src/aprime/recorder.py`, `decoy_independence_warnings`; MTH-023
and its correction; tests in `tests/test_resume.py`.
**Reopen if:** a second such check is wanted. The count matters more than any
one instance.

## ENG-007 — The detector separates a real fault cleanly on three channels, and the discovery floor suppressed it
**Date:** 2026-09-30
**Finding:** First end-to-end run against a real system under test. Banking
summary cell, `granite4.2:8b`, 30 inputs, k=4, 360 samples, 25 minutes of
recording. Candidate arm reads from a stale knowledge base (F5/F11). Seeds unset
on every arm. Fault fired on **15 of 30** inputs by per-input activation.

The report said `0 of 30 inputs flagged`. That was wrong to read as a failure.

| channel | best achievable estimate | at that cut |
|---|---|---|
| mode_share | **0.111** | 9 targets above, **0 decoys** |
| novel_mode | **0.111** | 9 targets above, **0 decoys** |
| nli_contradiction | **0.125** | 8 targets above, **0 decoys** |
| nli_directional | 0.500 | 2 targets above, 0 decoys |
| dispersion | 0.867 | 15 targets above, 12 decoys |

**Three channels achieved perfect separation.** Zero decoys above the cut, on
three statistics that are not variants of each other: cluster mix, unseen
clusters, and entailment contradiction. Each reported nothing because
`(1 + 0) / 9 = 0.111` exceeds q=0.10 by 0.011. **Ten targets would have cleared
it; nine did not.** This is MTH-024's floor doing exactly what it is defined to
do, on a detection that was otherwise clean.

Separation as raw text, no models, confirms it independently: on inputs where the
fault fired, A against B similarity was 0.593 while A against A-prime was 0.776;
on inputs where it did not, 0.846 against 0.815. The signal is real, it is in the
right direction, and it exceeds the system's own run-to-run variation.

**Two channels are blind to this fault class, both understandably.** Dispersion
measures spread within one cloud, and a stale value shifts a cloud without
widening it, so its mean target-minus-decoy difference was -0.006. The
directional channel is built for content removed or added, and substituting one
value for another is neither; it reached +0.083 against mode-share's +0.525.
Neither is a defect. Both are channels that should report nothing here, and the
decoy arm made them report nothing rather than noise, which is the property the
composition was designed for.

**Conformance reported independently of the floor.** 8 induced rules, all held
as hard, and two were violated on the candidate arm: a word-count range 2 times
in 120 and a line-count range once. The structural path is not gated by the
discovery floor, so it is the only part of the detector that can report a small
number of changes at all. That is worth knowing and was not designed for.

**k=4 is what cost the other six.** Mode-share over four samples can only take
the values 0, 0.25, 0.5, 0.75 and 1.0. The decoys reached 0.75, so 1.0 is the
only cut with zero decoys, and only 9 of the 15 fired inputs landed exactly
there. With finer clouds the separation would not have to be all-or-nothing.
**Evidence:** `results/cell_detection_20260929T231931Z.json` and its `.jsonl`
recording, `scripts/diagnose_channels.py`.
**Reopen if:** anything about the clustering predicate changes, since mode_share
and novel_mode both read the partition it produces and both of their numbers
here are statements about it.

## ENG-008 — A dead system under test produced a checkpoint that called itself complete
**Date:** 2026-09-30
**Finding:** The Ollama server stopped listening **90 seconds into a 50 minute
run**. The recorder then wrote 698 connection failures as complete triples over
the following 24 minutes, printed steady progress the whole time, and left a
checkpoint that `recording_progress` reported as **240/240 triples, 100%**.

| | as recorded | actually |
|---|---|---|
| samples | 720 | 22 usable |
| triples reported done | 240 | 8 |
| error rate | not reported | **96.9%** |

Nothing errored. Nothing warned. The detector then ran, dropped 38 of 40 inputs
for having an unusable arm, and reported `0 of 2 inputs flagged`, which is the
same sentence it prints for a clean run that found nothing.

**Three separate failures, in three places.**

*The recorder pressed on.* It treats a failed invocation as a recorded sample,
which is right for one transient failure and wrong for a run of them. It now
aborts after `abort_after_dead` consecutive triples in which every arm failed,
raising `RecordingFailed`. Wall clock is the cheapest thing lost in that state.

*The checkpoint counted errors as work.* `load_checkpoint` marked a triple
complete once all three arms were present, whether or not they held outputs. So
a resume would skip 232 dead triples permanently and the recording would never
be more than 3% real. A triple whose every arm errored is no longer counted as
finished, so a rerun collects it.

*Progress could not tell the two apart.* `recording_progress` returned a
fraction and nothing else, so 97% failed looked exactly like finished. It now
reports `errored_samples`, `dead_triples` and `error_rate`, and
`checkpoint_health` answers the question directly.

**A fourth bug surfaced while testing the fix, and it mattered more than it
looked.** The checkpoint is append-only, so a retried triple has both attempts
on disk. Counting errors across both meant a triple that had since been redone
successfully was still judged on the errors it used to have, and stayed dead
forever. That made the entire recovery path a no-op while appearing to work.
`load_checkpoint` now keeps the last write per `(triple, arm)`.

**Not caused by the concurrent run.** A second recording was started by mistake
at 02:02 while this one was going, which is its own error, but the server had
already been down since 01:53. Cause of the server's death unknown from here.

**What this says about the class of bug.** Every part of this behaved exactly as
written and the composition was still worthless, because no component's contract
said anything about the system under test being alive. The recorder's job is to
record what happens, so recording failures is correct; the checkpoint's job is to
remember what was done, and it did. The missing idea was that **a sample with no
output is not evidence**, and nothing owned it.
**Evidence:** `results/recordings/12dc8a339ed51f2b.jsonl` (kept as the artifact),
`checkpoint_health` on it, tests in `tests/test_resume.py`.
**Reopen if:** a system under test is added whose legitimate behaviour includes
erroring on most inputs, where the abort would fire on correct operation.

## ENG-009 — A preflight, and the conformance invariant it showed to be draw-dependent
**Date:** 2026-10-03
**Finding:** `record` now asks every arm one question before recording anything,
raising `PreflightFailed` when any cannot answer. Verified live against the
server that caused ENG-008, still down: **it fails in about a second**, quoting
the connection error per arm. `abort_after_dead` would have taken three triples;
the unguarded recorder took 24 minutes.

One rule for arm failure, matching `record`: any exception is a failure. A first
version re-raised `ValueError` so a misconfiguration would read differently from
an unreachable server, which disagreed with the recorder about what an arm
failure is and relied on sniffing exception types to guess intent. An empty
output is reported but is not a failure, because a cell exhausting its step
budget legitimately returns nothing.

**The preflight is an invocation, not an inspection**, and that has a
consequence worth stating: it perturbs a stateful system under test. Three extra
calls against a model cost three calls. Against the synthetic stub, which draws
from a jittered sequence, they shift every output after them.

**That is how a latent fragility surfaced.** With the sequence shifted,
`test_an_unchanged_candidate_violates_nothing` failed at jitter=0.5: the induced
`word_count_range(133, 159)` rule was violated by **2 of 200** candidate outputs,
a 1% false-alarm rate on a candidate where nothing changed. The test passes 5 of
5 on the unshifted draw and fails on the shifted one, so **its pass was
draw-dependent and nobody knew.**

This qualifies ENG-005 rather than overturning it. That entry established
`word_count_range` as a legitimate detector: zero firings on unchanged
candidates, 66% under injected verbosity. Both still hold for the draw it was
measured on. What is new is that at jitter=0.5 the rule is tight enough for an
ordinary draw to tip it, which the single-draw test could not reveal.

**Confidence: one derivation, one draw.** This is an observation from a single
shifted sample, not a measured false-alarm rate, and it should not be quoted as
one. The actionable part is that the test is a one-draw assertion of an
invariant, which makes it an unreliable guard either way: it will pass or fail on
anything that changes invocation counts anywhere upstream.
**Evidence:** `tests/test_conformance.py::test_an_unchanged_candidate_violates_nothing`
with and without `check_arms_first`; `preflight` in `src/aprime/recorder.py`.
**Reopen if:** anyone measures the induced word-count rule's false-alarm rate
across many draws at several jitter levels, which is what the test is currently
standing in for and should not be.
