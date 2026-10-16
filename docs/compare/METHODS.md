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

Known design questions parked here until work starts: per-pair FDR does not
give a many-way ranking (multiple-comparison design needed before any
leaderboard view); perf measurement interacts with behaviour recording
(MTH-015), so tokens/sec fields live in comparator records, never in Trace.
