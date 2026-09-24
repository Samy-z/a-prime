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

---

## §5 — Channel ordering inverted by the week-0 probe suite (2026-09-24)

The design entered week 0 assuming embedding displacement would be the primary
triage signal, with an NLI channel added to cover its expected weakness on
negation and numbers. The probe suite reversed that, and the reversal is large
enough to be worth recording as a decision rather than a tuning note.

Embedding displacement is not weak on the dangerous categories. It is
**anti-correlated** with meaning change: across three model families the pooled
separability AUC was 0.391, 0.440 and 0.532, and rewording moved the vector
roughly twenty times further than changing a number, a date or a negation.
A channel below chance is worse than an absent one, because it will be trusted.

It is not, however, useless. Against a minimal-surface-change baseline the same
channels recover to AUC 0.540 / 0.614 / 0.818. The failure is conditional on
surface instability, which is measurable, so the channel survives behind a gate
rather than being cut. MTH-011, MTH-012.

NLI contradiction carried seven of eight breaking categories at 84-100% under a
5% false-alarm budget, stable across output length and across four subject
domains. It becomes the primary channel. MTH-013.

The eighth category is the one that matters most for the project's shape.
Omission — a dropped material condition — is invisible to contradiction by
definition rather than by model weakness, since a text with a condition removed
is entailed by the original. Neither semantic channel covers it. Induced
structural conformance must carry that class alone, which means the one
mechanism the landscape survey found unoccupied (STD-003) is also the one the
blind-spot map says is load-bearing. MTH-014.

Two consequences beyond the channel ordering. Thresholds must be stratified by
output shape — the measured spread was a factor of eighty. And cost rises: a
bidirectional cross-encoder is far more expensive per comparison than a
bi-encoder, which strengthens rather than weakens the later case for distilling
the NLI-based mode clustering once it is the demonstrated bottleneck (see §4).

---

## §6 — Owner-scoped memory deliberately not persisted (2026-09-24)

A user-level `CLAUDE.md` holding owner working-style preferences was proposed
and rejected by the owner. Reasoning: preferences shift with topic, effort and
mood, and pre-instantiating them means methodology gets reapplied without being
thought about. The owner prefers to restate method per project.

Isolation rule 3 therefore stands as written — no `CLAUDE.md` above the repo,
for any purpose. Owner-scoped memory fragments across per-repo session keys by
design, and that is the accepted cost.

Narrow exception worth preserving: machine and environment facts are not
working-style preferences and do not shift. The TLS truststore requirement
(`src/aprime/net.py`) cost minutes rather than an hour precisely because it was
already known. Facts of that kind remain worth recording outside the repo;
preferences do not.

---

## §7 — Amendment to §6: a machine-facts file above the repo (2026-09-24)

§6 recorded that no `CLAUDE.md` may exist above the repo, for any purpose. The
owner has since granted a narrow exception, on the distinction §6 itself raised:
machine and environment facts are not working-style preferences and do not shift
with topic, effort or mood.

`~/.claude/CLAUDE.md` now exists, inherited by every project on this machine. It
is restricted by its own stated contract to facts about the computer — TLS
interception requiring the OS certificate store, system-level
`core.autocrlf=true`, display size, Python location, GUI launch behaviour. It
explicitly forbids project facts and working-style preferences, and states the
test for inclusion: would this be true regardless of who is working, on what, in
what mood.

Every entry in it carries a verification date and the command that produced it.
Four of the five were verified on the day of writing rather than carried from
memory; the fifth (GUI launch redirection) is marked as unverified and must be
re-confirmed before being relied on.

The rejection in §6 stands for preferences. Isolation rule 3 in `CLAUDE.md` is
amended to match.
