# Layer 2 — current-state knowledge

One document per subsystem, stating what IS true now. Read the relevant doc
before touching that subsystem. A change that alters what a doc says updates
the doc **in the same commit**.

These are not design documents and not history. Design rationale lives in
`HANDOFF.md`; settled findings live in the family ledgers.

## Docs to write

| Doc | Owner family | Status |
|---|---|---|
| `probes.md` — the instrument probe suite, what each channel can and cannot resolve, minimum detectable effect per channel | methods | GAP — week 0 |
| `fault-taxonomy.md` — the frozen fault catalogue and severity ladder, with its amendment log | bench | GAP — week 0, freeze before any tuning |
| `recorder.md` — trace capture format, the three-arm protocol, dedup | engine | GAP — week 1 |
| `adapters.md` — the system-under-test interface and how each system is wired | engine | GAP — week 1 |
| `decoy-fdr.md` — the calibration procedure and how flags are produced | engine | GAP — week 1 |
| `conformance.md` — rule induction from baseline output distribution, A-prime pruning, the three-tier band | engine | GAP — week 2 |
| `mode-clustering.md` — semantic equivalence classes, dispersion test, NLI channel | engine | GAP — week 2 |
| `cells.md` — the domain x format factorial, knowledge packs, base-rate control | bench | GAP — week 3 |
| `provenance.md` — run ids, config hashes, how a number in the paper is traced | study | GAP — week 1, needed before the first real run |
