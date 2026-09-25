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
