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
| 4 | `.agents/*.md` (gitignored) | Per-agent working dossiers, plus one claim-board per family. |
| Ledgers | `docs/<family>/LEDGER.md` | Append-only settled findings: stable id, date, evidence, reopen-if. Grep BEFORE investigating anything. |

Each family also keeps `STATE.md` (what is live or frozen now) and
`METHODS.md` (instruments, conventions, known data traps).

### Isolation rules (non-negotiable)

1. All project memory lives inside this repository.
2. Auto-memory (`~/.claude/projects/<key>/memory`) holds ONLY facts about the
   owner: who they are, how they work, feedback on working style. It never
   holds a project fact — no architecture, decision, finding, state, date,
   number or file path. If asked to remember a project fact, write it to the
   correct repo layer and say which one.
3. This project's `CLAUDE.md` lives at this repo root ONLY. One file exists
   above the repo — `~/.claude/CLAUDE.md`, inherited by every project — and it
   is restricted to **machine and environment facts** (TLS interception, git
   line-ending conversion, display size, Python location). It carries no
   project facts and no working-style preferences, by its own stated contract.
   Never add a project fact to it, and never create a `CLAUDE.md` at any other
   level. Ancestors were otherwise checked clean on 2026-09-24. See HANDOFF §7.
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
| `study` | `STD-###` | Execution and analysis. Run provenance, LOSO/LOFO, the transfer matrix, the blind-spot map, paper and README. |

**`engine` and `bench` are deliberately separate seats.** The seat that tunes
the detector must not be the seat that seeds the faults. This is a validity
guard against developing against the answers, not bookkeeping. See HANDOFF §2.

## Standing disciplines

- **Same-commit rule** — code and its layer-2 doc land together. A stale
  current-state doc is worse than none.
- **Grep-before-investigate** — ledgers first, then HANDOFF, then code.
- **Ask for the instrument, not the summary** — a claim is verified by the
  command, query or test that produced it, never by re-reading text.
- **Reports to the owner** — one self-contained page, full quality, numbers
  always with denominators, every finding graded by how many independent
  derivations support it, and a step-back closing paragraph.
- **Close every reply with a standing position block** — a short paragraph
  saying where the project stands, followed by a light list of decisions the
  owner needs to take or ratify. Carrying open decisions forward is the point:
  a decision that is never restated is a decision that gets made by default.
- **Staging** — each seat stages only its own files by explicit path. The Lead
  stages a shared file only after the author hands it off. Read the diff
  before committing.
- **Documentation threshold** — HANDOFF gets substantial changes only. Minor
  or cosmetic changes get no section and no mention in commit messages.

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
  invalidates prior results rather than silently changing them.
- **Dedup before counting** — near-duplicates corrupt both the FDR estimate and
  the clustering.
- **Provenance** — every number traces to a run id and a config hash.

## Commands

Environment is a repo-local venv. Prefix with `.venv/Scripts/python.exe` on
Windows.

    python -m pytest tests/ -q              # 77 tests, all fast, no models
    python scripts/run_probes.py --dry-run  # build probe pairs, no models
    python scripts/run_probes.py            # full blind-spot map (downloads 4 models)
    python scripts/run_probes.py --only deberta_mnli --normalise
    python scripts/fit_clustering.py        # refit the equivalence threshold

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

Week 0 and most of week 1 are done. Not built: the embedding style-stability
gate, shape-stratified thresholds, the Palworld adapter, the cell factorial and
fault-injection harness. Clustering and conformance exist but have **never run
inside the detector on real outputs** — only unit-tested against synthetic
corpora, so their cost figures are expectations rather than measurements.
