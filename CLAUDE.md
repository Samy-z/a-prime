# a-prime

Domain-agnostic regression detection for LLM-emitting systems, and the study
that measures whether it transfers across domains.

Two deliverables, one repo:

- **The tool** — given a baseline system A and a candidate B, report which
  inputs changed behaviour, with a calibrated false-alarm rate, without
  knowing what the outputs mean.
- **The study** — does that detection survive being moved to a domain it was
  not built for? No published answer exists (`docs/study/LEDGER.md`, STD-005).

Working paper title: *Does label-free regression detection transfer across domains?*

The name is the method: before comparing A to B, run A twice. The second
baseline run (A-prime) is the decoy arm that calibrates everything else.

## The four-layer memory system

Project memory is PROJECT-SCOPED and lives inside this repository.

| Layer | Where | What |
|---|---|---|
| 1 | `CLAUDE.md` (this file) | Current-state invariants, commands, architecture on one screen, pointers to layer 2. Session bootstrap, not a journal. Under ~150 lines. |
| 2 | `docs/knowledge/<subsystem>.md` | What IS true now, one doc per subsystem. Read before touching that subsystem. Updated in the SAME COMMIT as the change. |
| 3 | `HANDOFF.md` | Append-only decision journal, numbered sections, the WHY. Entered via pointers or grep, never browsed. |
| 4 | `.agents/*.md` (ignored, two exceptions) | Per-agent working dossiers and claim boards. Scratch, so ignored. `bench-taxonomy-research.md` and `bench-model-survey.md` are committed: they are the evidence under BCH-004 and BCH-007. |
| Ledgers | `docs/<family>/LEDGER.md` | Append-only settled findings: stable id, date, evidence, reopen-if. Grep BEFORE investigating anything. |

Each family also keeps `STATE.md` (what is live or frozen now) and
`METHODS.md` (instruments, conventions, known data traps).

### Isolation rules (non-negotiable)

1. All project memory lives inside this repository.
2. Auto-memory (`~/.claude/projects/<key>/memory`) holds ONLY owner facts: who
   they are, how they work, feedback on working style. Never a project fact.
   If asked to remember one, write it to the right repo layer and say which.
3. This project's `CLAUDE.md` lives at this repo root ONLY. The one file above
   it, `~/.claude/CLAUDE.md`, is machine and environment facts by its own
   contract: never add a project fact there, never create a `CLAUDE.md`
   anywhere else. See HANDOFF §7.
4. Spawned agents receive memory through their briefs. Agents never write to
   auto-memory and never read another project's files.
5. Open every session with this repo root as the working directory. The
   auto-memory key follows the session's working directory, so opening this
   project from a parent folder pools its memory with sibling projects.

## Families (seats)

| Family | Prefix | Owns |
|---|---|---|
| `methods` | `MTH-###` | Statistical design and validity. Estimators, test statistics, FDR construction, power, validation protocol, pre-registration integrity, prior-art monitoring. |
| `engine` | `ENG-###` | The detector. Recorder, three-arm replay, adapters, induced conformance, semantic mode clustering, NLI channel, cost control. |
| `bench` | `BCH-###` | Systems under test and the fault harness. Domain cells, knowledge packs, fault injection, per-input activation instrumentation, dedup, base-rate control. |
| `study` | `STD-###` | Execution and analysis. Run provenance, LOSO/LOFO, the transfer matrix, the blind-spot map. |
| `reader` | `RDR-###` | Outward-facing artifacts: README, the paper, dataset cards. **Forbidden from assuming project context** — must be able to read an artifact cold, having opened no other file. Owns the audience contract in `docs/reader/METHODS.md`. |
| `compare` | `CMP-###` | The comparator: input generation from a usage description, multi-system scheduling, output store, inference performance, comparison reporting. Same repo behind four guardrails: public API only (boundary test), own ledgers, no commit touching both it and `src/aprime/`, rails do not cross. See `docs/compare/METHODS.md`. |

**`engine` and `bench` are deliberately separate seats.** The seat that tunes
the detector must not be the seat that seeds the faults. This is a validity
guard against developing against the answers, not bookkeeping. See HANDOFF §2.

**`reader` is separate for the same reason.** Writing for somebody who already
knows is invisible to the author, because every internal term feels obvious once
you have used it for a week. You cannot audit your own blind spot. Style follows
**audience**, not author: the ledgers stay dense and identifier-heavy on purpose,
because their reader has full context and wants the finding rather than an
on-ramp. See HANDOFF §11.

## Standing disciplines

- **Same-commit rule** — code and its layer-2 doc land together.
- **Grep-before-investigate** — ledgers first, then HANDOFF, then code. A fact
  already settled may still have an unexamined implication; look for both.
- **Ask for the instrument, not the summary** — a claim is verified by the
  command that produced it. This applies to our own null results: `0 flagged`
  and a blind channel look identical in a report (ENG-007).
- **Reports to the owner** — one self-contained page, numbers always with
  denominators, findings graded by how many independent derivations support
  them, and a step-back closing paragraph.
- **Close every reply with a standing position block** — where the project
  stands, then the decisions the owner must take or ratify. A decision never
  restated is a decision made by default.
- **Staging** — each seat stages its own files by explicit path. Read the diff
  before committing.
- **Documentation threshold** — HANDOFF gets substantial changes only.
- **No study-shaping parameter outside a dated entry.** k=6 entered the study
  undocumented and is the only rail leak on record (HANDOFF §21). Sizing
  choices are methods decisions.
- **A thesis migration is an amendment, never a drift.** Claim-surface
  changes get dated declarations naming what prompted them; STD-012 is the
  template.
- **Runtime state is data.** Anything that cannot be regenerated (label
  stores, partial checkpoints) is committed the moment it exists, not at the
  next milestone. Both label losses were this lesson (BCH-018).
- **Study constraints are configuration, never code.** The study controls
  variables the tool must still expose. `think=False` is uniform across the
  study pool so that measured differences cannot come from thinking
  performance — but thinking is a real thing a user might want to compare, so
  the library defaults it off and never forbids it. Any study-time control that
  hardens into a library constraint is a bug, not a simplification. See
  HANDOFF §10.

## Study integrity rails

Detail in `docs/methods/METHODS.md`. These are the ones that, if violated,
silently invalidate the result rather than failing loudly:

- **Pre-registration** — fault taxonomy and severity ladder frozen before any
  detector tuning. Amendments are dated appends, never in-place edits.
- **Sealed holdout** — the real-regression set is opened once, and the opening
  is recorded with its date.
- **No threshold chosen outside a fold** — every cutoff and hyperparameter
  selected inside nested leave-one-system-out.
- **Pinned instruments** — embedding and NLI model versions locked. Bumping one
  invalidates prior results rather than silently changing them. **The sampling
  seed is deliberately outside this rail**: pinning it collapses the decoy arm,
  which is the null. Arms mirror the deployment's seed policy and record it
  (MTH-023).
- **Dedup before counting** — near-duplicates corrupt both the FDR estimate and
  the clustering.
- **Provenance** — every number traces to a run id and a config hash.

## Commands

Environment is a repo-local venv. Prefix with `.venv/Scripts/python.exe` on
Windows.

    python -m pytest tests/ -q              # the whole suite in seconds, no models
    python scripts/run_probes.py --dry-run  # build probe pairs, no models
    python scripts/run_probes.py            # full blind-spot map (downloads 4 models)
    python scripts/run_probes.py --only deberta_mnli --normalise
    python scripts/fit_clustering.py        # refit the equivalence threshold
    python scripts/draw_blind_spot_map.py   # redraw the figure from stored probe runs, no models
    python scripts/run_cell_detection.py --status   # progress of a paused run
    python scripts/run_cell_detection.py --stop     # stop one at the next triple
    python scripts/run_study.py --status            # the nine-cell factorial
    python scripts/run_study.py --k 20 --only-format summary --go   # D25: a separate configuration
    python scripts/diagnose_channels.py     # why a channel reported nothing
    python scripts/agent_decision_variation.py results/study/<cell>.<hash>.jsonl  # agent cells, no model
    python scripts/capture_chat_fixtures.py # refresh the API test fixtures

`src/aprime/net.py` must be imported and `enable_os_truststore()` called before
anything opens HTTPS, or every model download fails behind this machine's TLS
interception. Entry points already do it.

## Architecture map

    adapter.py      the system-under-test boundary: input -> output + trace.
                    Nothing else. Resist widening it; log the pressure instead.
    stub.py         synthetic system with known ground truth, so FDR control can
                    be checked against something a real system never tells you.
    recorder.py     three-arm interleaved replay. Grouped by input (ENG-001),
                    triple-atomic, checkpointed and resumable.
    dedup.py        exact + normalised. Semantic near-dup is a known gap.
    normalize.py    strip presentation, never content. Runs before everything.
    clustering.py   semantic modes via bidirectional entailment, threshold 0.7.
    stats.py        mode-share distance, dispersion, novel-mode mass.
    fdr.py          target-decoy selection. The decoys are the null.
    conformance.py  induced structural rules, pruned by the decoy arm.
    provenance.py   run id, config hash, git state, pinned instrument revisions.
    probes/         the probe suite: what each channel can and cannot resolve.
    cells/          nine systems under test: 3 domains x 3 output formats, with
                    eight tools each. `retrieval_faults.py` degrades what they
                    know and `prompt_faults.py` edits what they are told,
                    rather than rewriting what they say.

Pipeline: record three arms -> dedup -> normalise -> cluster jointly -> score
(mode-share, dispersion, NLI contradiction, NLI directional both tails,
conformance) -> target-decoy select at q.

**Channel inventory lives in `docs/engine/METHODS.md`** and was measured, not
assumed — embedding displacement turned out anti-correlated with meaning change
and is now gated; NLI carries the load. Read that table before touching a
channel.

Related repository: **palworld-rag** (https://github.com/Samy-z/palworld-rag)
— the instrumented reference system, consumed across the adapter boundary as an
external system. It is the development system and is therefore **excluded from
the headline transfer numbers**; it is reported separately. See HANDOFF §3.

## Where things stand

**The k=6 matrix is complete: nine of nine cells recorded, analysed and
written to `results/study/matrix.json` on 2026-10-16** (the per-cell report
files carry analysis runs 20261017T012750Z/51Z at 1d50fee, the third pass
over the same recordings, every flag count unchanged since the night pass;
one fault class, the stale knowledge base F5; per-input activation as ground
truth; q = 0.10). Summary row: recall
0.88 / 0.79 / 0.86 for banking / logistics / hospitality. Extraction row:
0 / 0.48 / 0, the two zeros diagnosed as decoy resolution at six samples, not
blindness (STD-010, D25). **Agent row: nothing flagged in any domain, with
26 / 25 / 26 of 40 inputs touched and every channel silent** (STD-011). Its
diagnosis ran on the GPU machine (the cloud instance cannot reach the model
host, STD-011 first append, HANDOFF §23): **resolution-limited in all three
cells under the frozen criterion MTH-025** (best estimates 0.25 / 0.25 / 0.4
at the top value; 4 / 4 / 3 touched inputs there above 0 / 0 / 1 decoys), with
decoys as wide as the fired targets on most inputs, as the decision-level
reading expected (STD-011 second append; `scripts/agent_decision_variation.py`).
The hospitality figure was recorded as 0.375 with 8 above 2 until the
estimator's tie handling was fixed on 2026-10-16 (ENG-010, HANDOFF §25); the
five diagnosis files, the nine per-cell report files and
`results/study/matrix.json` were regenerated on the GPU machine the same day
and every flag count held (STD-011 fourth append, 48fa3ee); the paper's
section 8 and Appendix F cite the rerun. The paper is
the two-question paper (STD-012, HANDOFF §24): the registered transfer
question answered at its width, the format-and-k structure a declared
post-hoc finding with the k=20 row as its confirmatory arm. The
banking-summary realised FDR stays a bracket, [0.05, 0.21], at k=6 (STD-010
fourth append).

**The D25 test is closed (STD-013, 2026-10-17).** The k=20 summary row
passed its pre-registered test: pooled recall 51/56 = 0.91 inside
[0.72, 0.92], realised FDR 3/54 = 0.056 under budget, labels complete
(hashes 5aa2e096752e8c38, fbcbd6de938d8366, ba6eaed55818324c). The
banking-extraction k=20 re-record (1a37665b4308bcf4) caught 21/21 at FDR 0,
superseding the partial-label k=6 row. No full re-record. Paper §8 reports
both against the prediction and the abstract's result is filled
(2026-10-17); one bracket left, the agent format at k=20. **Data trap:**
`matrix.json` is a view of the last `run_study.py` run; cite the per-cell
`.report.json` files (STD-013, study METHODS). The 05:00 daily task runs only
the k=6 stage.

Not built: the severity titration rerun (needs k>=20 and a fault with a
severity knob, bench METHODS), LOSO, the embedding style-stability gate, the
Palworld adapter. F2 and F11 are built and unit-tested, never run live. The
paper is drafted in every section; section 8 and Appendix F describe the
nine-cell k=6 matrix in the two-question shape and the four k=20 cells
against the D25 prediction (2026-10-17), silent cells diagnosed; the abstract
carries its result; subtitle per RDR-010.
