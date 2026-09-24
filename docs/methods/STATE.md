# methods — STATE

What is live or frozen right now. Updated in the same commit as the change.

## Frozen

- **Fault taxonomy and severity ladders — frozen 2026-09-24**, in
  `docs/knowledge/fault-taxonomy.md`. Nothing may be tuned against them.
  Amendments are dated appends to the log at the foot of that file; two have
  landed already (F8 split, exclusions ratified).

## Live

- Probe suite (`src/aprime/probes`, `scripts/run_probes.py`). Current reference
  run: `20260924T031004Z`, config `592763f4f2a8c4d7` (six logical channels over
  two NLI checkpoints, plus directional entailment). Embedding findings from the
  earlier run `20260924T022150Z`, config `eb95f0b802c4660a`. Findings in
  `docs/knowledge/probes.md`, rulings in MTH-011 through MTH-017.

## Pinned instruments

Resolved at load time and recorded from the reference run, not copied from a
model card.

| Role | Hub id | Revision | Pinned on |
|---|---|---|---|
| Embedding (small) | `sentence-transformers/all-MiniLM-L6-v2` | `1110a243fdf4706b3f48f1d95db1a4f5529b4d41` | 2026-09-24 |
| Embedding (base) | `BAAI/bge-base-en-v1.5` | `a5beb1e3e68b9ab74eb54cfd186867f64f240e1a` | 2026-09-24 |
| Embedding (base, prefixed) | `intfloat/e5-base-v2` | `f52bf8ec8c7124536f0efb74aca902b2995e5bcd` | 2026-09-24 |
| NLI (primary channel) | `MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli` | `6f5cf0a2b59cabb106aca4c287eed12e357e90eb` | 2026-09-24 |
| NLI (replication check) | `FacebookAI/roberta-large-mnli` | `2a8f12d27941090092df78e4ba6f0928eb5eac98` | 2026-09-24 |

Bumping any of these invalidates prior results. Record the bump as a dated
append in the LEDGER and re-run the probe suite; do not silently carry numbers
across a version change.

**Second NLI checkpoint done, and it only partly replicated (MTH-017).** The
direction of every finding held; none of the magnitudes did. Per category the
gap runs to 48 points (unit: 84% DeBERTa vs 36% RoBERTa). MTH-013 and MTH-016
are therefore properties of the DeBERTa checkpoint, not of NLI, and the pinned
checkpoint is a first-order design variable rather than an implementation
detail. Report it as prominently as any other choice.

## Sealed holdout

| Set | Sealed on | Opened on | Opened by |
|---|---|---|---|
| Real-regression holdout | not yet collected | — | — |
