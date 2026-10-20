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

## Queued question — the cross-system null (opened 2026-10-16, gates paper two)

**Proposal drafted 2026-10-20 and revised twice the same day, awaiting
owner ratification:** `docs/methods/cross-system-null-proposal.md`. Its
first recommendation (a pooled within-system null with the ratio-adjusted
estimate `(1 + d/r)/t`, "adding resolution at the margin") was refuted by
an adversarial pass and withdrawn: the committed instrument
`scripts/simulate_null_designs.py` shows pooling reports no more often
than the single decoy in every row and never raises power. The second
revision, after a three-seat cross-model review, re-grounds validity on
pairwise exchangeability rather than equal marginals, which only Design R
inherits unchanged. The recommendation is Design R: every system
contributes two clouds (`A, A', B, B'` per pair; whether a roster may
hold more than one pair is put to the owner), selection against the
reference pair at `r = 1` exactly as today, with the candidate's
self-variance, the reverse selection, the reverse orientation, the pooled
estimate and the three replicate target sets reported beside it; the
orientation declared (the reference defines the strata and the
new-answers direction); the estimator `(1 + d/r)/t` over the `b - 1` star
pairs proposed for freezing for the titration's `b` dial, the cross-pooled
estimate reported under its own name outside `r`.
Validation is the stub sweep (MTH-018's protocol, the bounds
`tests/test_pipeline.py` asserts) for the selector; the null pair stays
as a hard stop and a sign statistic with a binomial band, since an
independent decoy arm flags nothing almost surely under any sound rule.
Seven ratification items in its §8. HANDOFF §26 and its two amendments.

A vs A-prime calibrates one system against its own variance. A vs B is two
systems with two self-variances, and no entry yet says whose null certifies
the comparison. Candidate design is four arms (A, A-prime, B, B-prime) with
the combination rule to be argued and frozen BEFORE any cross-model triple is
recorded; the recorder's triple-atomicity generalises with it. The stored-
baseline regime (version bump: baseline recorded weeks before the candidate,
interleaving impossible) is part of the same question, and the STD-008
negative control - score a system against itself across a time gap, expect
nothing - is its first instrument: period-one arms already exist in the k=6
and k=20 recordings; the period-two re-record runs under
`scripts/run_drift_control.py` and sits at 212 of 240 triples on main.

## Queued question — agent self-variance, titrated with clear numbers (owner-directed 2026-10-17)

**Protocol drafted 2026-10-20 and revised twice the same day, awaiting
owner ratification:** `docs/methods/agent-self-variance-titration-proposal.md`.
Point 1 (banking-agent at k=20) is owner-directed and records without
further ratification; every other point waits. Dials k, b (baseline runs;
`r = b - 1` star decoy pairs), temperature and the decision-versus-text
channel, each with an expectation that names its refuting observation; a
three-point committed grid on banking-agent (1, 2, 3) plus two points
gated on results and an optional re-anchor of k=6 in the current serving
regime; a cost table in three columns, 16.9 s (the 2026-09-29 pooled
smoke figure), 20.9 s (banking-agent's own smoke row, the planning figure
for this grid) and 65 s (the 6 October partial-CPU regime
`docs/knowledge/environment.md` documents, the risk column). Prerequisites
named per point: the generalised estimator, roster change and
roster-aware readers under a dated MTH-025 amendment before point 2; the
sampling parameters hashed without orphaning the committed checkpoints,
plus an eight-call temperature-0 repeat check, before any temperature
point; a hashed anchor label before the re-anchor; a digest guard and
server-version field in `run_study.py`. The reading rule registers a move
on the finer `1/t` of the two points or on crossing `q`. Five
ratification items in its §6.

The agent row's silence decomposed into high text-level self-variance plus
decisions the fault barely moved (STD-011 appends). The owner's direction:
investigate the limitation rather than wait for a reviewer to, and publish
it with numbers. Parameters to titrate, each a dial that might polish the
statistical issue: k (grid fineness and mass per mode); the number of
baseline arms m (A-prime, A-second, ... — the estimator currently assumes
one decoy per target, so m > 1 needs a generalised estimator, for example
(1 + d/m)/t, DESIGNED AND FROZEN before use, per the k=6 lesson; in the
proposals' terms, `b` baseline clouds with the first counted and
`r = b - 1` star pairs selecting, estimate `(1 + d/r)/t`, the null
proposal §0);
temperature and serving policy as the entropy dial; and the decision-token
versus rationale-text channel split the decision-level instrument opened.
First data point: the banking-agent k=20 cell (scheduled 2026-10-17 night).
