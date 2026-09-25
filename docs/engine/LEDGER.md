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
