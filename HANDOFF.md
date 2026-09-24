# HANDOFF

Append-only decision journal. Numbered sections, newest at the bottom. This is
not a lookup surface — enter it through pointers from layer 2, or by grep.

---

## §1 — Memory system instantiated (2026-09-24)

Four-layer memory bootstrapped per the owner's specification: `CLAUDE.md` at
repo root (layer 1), `docs/knowledge/` (layer 2), this file (layer 3),
`.agents/` gitignored (layer 4), and per-family ledgers under `docs/<family>/`.

**Ancestor check performed and clean.** No `CLAUDE.md` exists in any directory
above this repo, nor at user level. Scanned: the parent projects folder,
Desktop, the user home, and their `.claude/` subdirectories.

**One pre-existing leak recorded, outside this repo.** The owner's auto-memory
under the key for the parent projects folder holds 24 entries, of which 16
carry a different private project's name. Roughly ten of those are hard project
facts — live state, dated commitments, tuning parameters, repo-specific file
conventions — and the rest are portable working-style feedback that merely
references that project. All 16 are visible to any session opened at that
parent folder, including sessions for this one; they were loaded into the
session that wrote this entry. Remediation belongs to that other project and is
not actioned here. This repo's discipline prevents a-prime from adding to the
pile.

---

## §2 — Family structure (2026-09-24)

Four seats: `methods`, `engine`, `bench`, `study`. The owner's initial sketch
(SDE / UX-UI / DSE / statistician / applied AI scientist) was set aside because
this project ships a study and a library, not an application — the UI surface
is a report, and the data-engineering work is inseparable from the bench.

**Why `engine` and `bench` are separate seats.** The statistical review
identified development-against-the-answers as a live threat: a detector tuned
by someone who knows where the faults are seeded will learn the seeds.
Splitting the seats makes the blindness structural rather than a matter of
discipline. It also sets up the red-team requirement — a fault set authored by
a seat with no visibility into detector internals.

`methods` additionally owns prior-art monitoring. The novelty claim depends on
a landscape that is moving (STD-006), so it is a standing duty, not a one-off.

---

## §3 — Scope boundary with palworld-rag (2026-09-24)

The reference system lives in its own repository and is consumed across the
adapter boundary as an external system. Reasons, in order of weight:

1. It is the only system whose correct answers we know, because we author the
   knowledge base — the one place detector flags can be checked against actual
   correctness rather than mere change.
2. RAG faults (knowledge-base corruption, stale index, retrieval degradation)
   need a system we own to instrument per-input fault activation cleanly.
3. Game patches supply real, dated, non-synthetic content drift with known
   deltas — better evidence than injected corruption for at least one fault
   class.
4. It contains both low-entropy factual lookups and high-entropy interpretive
   answers, giving a within-system entropy contrast with everything else held
   constant.

**Consequence, which must appear in the paper:** it is the development system.
It cannot honestly appear in the leave-one-system-out generalisation numbers
and is reported separately as the instrumented reference.

---

## §4 — Fine-tuning deferred out of this project (2026-09-24)

A fine-tuned component was considered and cut. The detector is black-box: from
its perspective a fine-tuned system under test is indistinguishable from a
prompted one, so "demonstrates the tool works on fine-tuned systems" is a claim
with no content behind it. The one real candidate — distilling the semantic
mode clustering once it is provably the cost bottleneck — cannot be justified
before that bottleneck exists, which is week 3 at the earliest.

Recorded so it is not relitigated: fine-tuning returns as a separate project
with a scope where it is the point, not a prop.
