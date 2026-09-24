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
3. `CLAUDE.md` lives at this repo root ONLY. Never create or edit one above
   the repo. Ancestors were checked clean on 2026-09-24.
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

> GAP — nothing is built yet. Populate when week 0 lands.

## Architecture map

> GAP — populate when the adapter boundary and pipeline exist.

Related repository: **palworld-rag** (https://github.com/Samy-z/palworld-rag)
— the instrumented reference system, consumed across the adapter boundary as an
external system. It is the development system and is therefore **excluded from
the headline transfer numbers**; it is reported separately. See HANDOFF §3.
