# compare — instruments and constitution

The seat's constitution is the four guardrails ratified 2026-10-16. They are
what makes living in the study's repository safe, and they are not
negotiable per commit:

1. **Public API only.** Comparator code imports `aprime`'s public surface,
   never its internals. Enforced by a boundary test that fails on deep
   imports; the test lands with the first comparator code.
2. **Own family.** `CMP-###` entries in this directory's LEDGER; study
   ledgers never carry comparator findings.
3. **No mixed commits.** A commit touches `compare` code or `src/aprime/`,
   never both. Greppable in history.
4. **Rails do not cross.** The study's pinned-instruments rail does not bind
   comparator code, and comparator conventions never harden into library
   constraints (the HANDOFF §10 lesson, both directions).

**Evidential boundary, owner-declared 2026-11-11 (HANDOFF §28).** The two
projects are fully distinct and stay that way: a-prime is the research on
the target-decoy FDR approach applied to LLM-emitting systems; ChatADV is a
proof-of-concept application for a real user that happens to be a good
near-real test bed for the tool. Campaign results — the assistante-ventes
pairwise run and its blind human pass included — are product evidence that
the comparator works, never study evidence: nothing from `compare/` enters
the paper, the README's research claims, or the backing of a study or
methods finding. The allowed direction is consumption: campaigns consume
frozen designs (Design R under MTH-027) and the public API, and a methods
entry may name a campaign as a consumer, which is a pointer, not evidence.
Verified at declaration time: a grep of `paper/` and `docs/reader/` for the
campaign's names, models and ids returns nothing.

Known design questions parked here until work starts: per-pair FDR does not
give a many-way ranking (multiple-comparison design needed before any
leaderboard view); perf measurement interacts with behaviour recording
(MTH-015), so tokens/sec fields live in comparator records, never in Trace.

Instruments: `compare/pace_ventes.py` runs measurement plan 1 of the
assistante campaign — per-candidate pace and footprint, CPU only
(`num_gpu: 0`), resumable, pull failures recorded as findings. Results in
`compare/results/`. It talks to Ollama directly; the detector is not
involved, and the boundary test holds the whole package to that.

`compare/pairwise_ventes.py` runs measurement plan 2: the Design R
four-arm recording (compare-side, tuple-atomic, resumable, digest-guarded,
collision-guarded against main-line recorders) and the five `detect()`
relabelings through the public API. `scripts/night-pairwise.cmd` chains
record then analyse unattended. Known data trap: the two pace constants in
its history were calibrated on translation tuples only; pace is per task
class (translation ~16 s/tuple, drafting ~46 s/tuple on the dev CPU,
CMP-004).

**Blind judging protocol** (measurement plan 3, instrument
`compare/emit_judging_queue.py`): the primary selection's inputs, in
seeded-shuffled order, two samples per side drawn one from each of the
model's two arms, side X/Y re-drawn per case; the queue shows task and
outputs only (no model names, channel scores or stability markers,
enforced by `tests/test_compare_judging.py`); the unblinding map stays
sealed in `judging-key-DO-NOT-OPEN.json` until every `verdict:` line is
filled (X / Y / egal / aucun), then `--score` unblinds and writes the
tally. The emitter refuses to overwrite filled verdicts without `--force`:
judging work is runtime state.
