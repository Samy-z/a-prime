# methods — STATE

What is live or frozen right now. Updated in the same commit as the change.

## Frozen

> Nothing yet. The fault taxonomy and severity ladder freeze in week 0 and are
> recorded in `docs/knowledge/fault-taxonomy.md` with an append-only amendment
> log. Nothing may be tuned against them before the freeze is committed.

## Live

- Probe suite (`src/aprime/probes`, `scripts/run_probes.py`). Current reference
  run: `20260924T022150Z`, config `eb95f0b802c4660a`. Findings in
  `docs/knowledge/probes.md`, rulings in MTH-011 through MTH-014.

## Pinned instruments

Resolved at load time and recorded from the reference run, not copied from a
model card.

| Role | Hub id | Revision | Pinned on |
|---|---|---|---|
| Embedding (small) | `sentence-transformers/all-MiniLM-L6-v2` | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | 2026-09-24 |
| Embedding (base) | `BAAI/bge-base-en-v1.5` | `a5beb1e3e68b9ab74eb54cfd186867f64f240e1a` | 2026-09-24 |
| Embedding (base, prefixed) | `intfloat/e5-base-v2` | `f52bf8ec8c7124536f0efb74aca902b2995e5bcd` | 2026-09-24 |
| NLI (primary channel) | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | `6f5cf0a2b59cabb106aca4c287eed12e357e90eb` | 2026-09-24 |

Bumping any of these invalidates prior results. Record the bump as a dated
append in the LEDGER and re-run the probe suite; do not silently carry numbers
across a version change.

**Second NLI checkpoint outstanding.** MTH-013 rests on one model, unlike
MTH-011 which replicates across three embedding families. Until a second
checkpoint is probed, the NLI result is a property of this checkpoint and not
of NLI.

## Sealed holdout

| Set | Sealed on | Opened on | Opened by |
|---|---|---|---|
| Real-regression holdout | not yet collected | — | — |
