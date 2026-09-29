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

---

## §8 — Overnight block, 2026-09-25 (week 1 completed, week 2 substantially built)

Worked unattended on the owner's instruction to push as far as possible. Six
decisions were taken without consultation; each is recorded with its reasoning
so any of them can be reversed cheaply.

**Register became a third probe class (MTH-021).** Owner decision, but the
consequence was not anticipated: the false alarms the design had attributed to
`verbosity` were never false alarms. The channel was correctly detecting a
change we had mislabelled as a non-change. Relabelling recovered a signal rather
than merely tidying the labels, and it fixed the clustering fit as a side effect
— the argmax moved from 0.05 to 0.65, converging on the threshold MTH-020 had
chosen by argument alone.

**Replay is grouped by input (ENG-001).** Mine, and the largest single
scheduling decision available: roughly twenty days of prefill on the measured
hardware. It does not weaken MTH-015, because that guarantee is about the
triple and grouping puts the three arms closer together, not further apart. What
it costs is that an input's noise floor now spans a short window while the run
spans a long one, so every sample carries a wall-clock timestamp and the span is
reported rather than assumed away.

**A machine-facts file above the repo (§7 amendment).** Already recorded.

**The fault harness grades on activation, never the cell label (BCH-011).** A
fault labelled at the cell level is wrong for every input it never touched, and
that is label noise in the direction that looks like success.

**Seat separation was preserved by commit order, not by process.** Building the
detector and the harness in one session is a contamination risk. The guarantee
is that every detector threshold was fitted and committed before the harness
existed, against the probe suite and the stub, neither of which contains an
injected fault. That is checkable in the git history rather than promised — and
it is a weaker guarantee than two people would give. Say so in the paper.

**The first titration was a saturated instrument, not a result (ENG-002).** 100%
recall in all 24 cells including the lowest severity. Under exact-match
clustering any text change produces a novel mode, so the ladder measured whether
the string changed rather than how much. Reported as a defect in the
measurement, because the alternative — reporting 100% detection — would have
been true and completely misleading.

**What is still not built:** the Palworld adapter and the domain-cell factorial,
both blocked on the owner ratifying the model pool; prompt-regression and
retrieval fault injection, which need a system with a prompt and a retriever;
and the fix for ENG-003, where clustering is recomputed three times per
comparison.

---

## §9 — Decisions ratified 2026-09-29

**Model pool (D10).** Granite 4.2 8B, Ministral 3 8B, Qwen3.5 9B, plus a 3B as a
deliberate weak system. Four labs, two architectures, all Apache-2.0. Hermes
dropped at 14B despite being the owner's own suggestion. Recorded in
`docs/bench/STATE.md`.

**Context cap (D11) — framing corrected by the owner.** I had presented the cap
as a throughput dial to be lowered. It is a constraint that must fit the systems,
and the cells decide it. The multi-step agent cell is the binding case: tool
definitions alone run 1-2k tokens and multi-turn accumulates. Sequence is now:
build the cells, measure each one's peak token demand, then fix the cap to the
smallest value that fits with headroom. Picking the budget before knowing the
demand is how the agent cell spills to CPU in week 3.

**Serving stack (D12) — recommendation reversed on reflection.** I initially
recommended migrating off Ollama. The honest position is narrower: pin Ollama's
version, disable auto-update, extract and pin its per-model templates explicitly,
and record all of it in provenance. That addresses the actual incident — the
client updating itself mid-survey, which is F4 provider drift injected by our own
tooling — at a fraction of the cost.

Migration is conditional on needing GBNF constrained decoding for the extraction
cells. The drawback of migrating was understated at first: hand-rolling chat
templates does not remove template risk, it *transfers* it from an invisible
vendor default to a visible config of ours. Visible and pinnable is better for a
study; it is not automatically safer, and F14 is precisely "somebody got the
template wrong".

**Budget (D13) — my error, corrected.** See the BCH-010 append. The 1M and 324k
figures were different calculations, not a rescoping.

**Licence (D14).** Apache-2.0 for code, CC BY 4.0 for documentation and
findings. Apache rather than MIT for the patent grant; permissive rather than
copyleft because copyleft would deter exactly the adoption that makes the tool
worth publishing. The docs are split out because the measured findings are the
contribution and CC BY asks for attribution when they are quoted.

**Fault grid (D16).** Start at the six incident-evidenced classes our injections
implement, x 3 severities, x 1 blast regime (B0) = 18 comparisons per cell.
Additional regimes only for the sticky-routing cells, where B3 is the point
rather than a variation. This number is the compute bill, so it is chosen rather
than discovered.


---

## §10 — Study constraints are configuration, not code (2026-09-29)

**D18, and the owner's reasoning is the more useful half.**

For the study, `think=False` uniformly across the pool. The purpose is confound
control: the study asks whether detection transfers across domains, and if half
the pool reasons before answering then measured overlaps and differences could
come from thinking performance rather than from anything the detector does.
Holding it off makes the pool differ by architecture and training rather than by
which knobs happen to work — and two of the four models reject `think=True` with
HTTP 400 anyway (BCH-012), so uniformity is also the only setting that runs.

For the **tool**, thinking stays available. The owner's framing: the tool exists
to assess light changes to a system whose LLM is swapped "like a pen's head",
and to surface which metrics are actually useful for benchmarking one model
against another. A user comparing a thinking model to a non-thinking one is
doing exactly that — it is a real switch somebody makes, not an edge case.

**The general rule, which is why this got a section rather than a ledger line:**
a constraint the study imposes to control a variable must not harden into a
limitation of the library. Audited on the day: every study-relevant value is a
parameter with a default rather than a constant — `q`, `threshold`,
`gate_threshold`, `hard_min`, `band_lo`, `min_stratum`, `think`, `keep_alive`.
Nothing currently violates the rule. It is written down so that the next
simplification does not.

**A framing consequence worth carrying to the README.** "Regression detection"
undersells it and is also more crowded. The narrower and truer description is
*what changed when I swapped the model?* — same system, same prompts, same
tools, one component replaced. That is the question the decoy arm exists to make
answerable, and it is the question a user actually arrives with.

**Noted, not scheduled:** if the intended use is comparing model against model,
then thinking is not merely a config flag but something a report could
*attribute* a difference to. That is a channel-level feature, out of scope now,
and worth revisiting once the cells exist.

---

## §11 — A `reader` seat, because style follows audience (2026-09-29)

Owner review of the README: too cryptic, referencing concepts a first-time reader
cannot relate to, with compressed prose and recognisable machine-writing habits.
Correct on all three counts. Measured, the old README had **11 terms it never
defined**, 15 em dashes per 1000 words, and bold on every other clause.

The owner offered two ways to fix it structurally: a new reviewer or style seat,
or a writing style defined per existing family. Neither quite fits, and the
reason is worth recording.

**Style is not the variable. Audience is.** The family ledgers *should* be dense
and identifier-heavy, because their reader is a maintainer with full context who
wants the finding rather than an on-ramp. Defining a style per family would also
misfire, since one family writes both a ledger and the paper — two different
readers, two different contracts.

So: a new seat, scoped by **perspective rather than task**. Not a style
corrector, which would smooth prose without fixing the real problem. The real
problem is writing for somebody who already knows, and that is invisible to the
author because every internal term feels obvious after a week of use. You cannot
audit your own blind spot. That is exactly the argument that separates `engine`
from `bench`, applied to documents.

The seat owns an audience contract, one row per artifact class, stating what each
may assume and what it must define. `README.md` may assume general software
literacy and must define everything else. `docs/*/LEDGER.md` may assume
everything and must define nothing.

**Made checkable rather than aspirational.** `scripts/check_prose.py` reports em
dash density, sentence length distribution, bold density, internal identifiers,
and terms used without a nearby explanation. Advisory, not a gate. This project
measures things instead of asserting they improved, and prose is not an exception.

**The checker itself was wrong twice, which is the useful part.** Its first
version accepted any of `is`, `:` or `(` within 240 characters as evidence a term
had been explained, so it reported zero undefined terms in a README that had
eleven. After the fix, an escaping layer turned `\b` in one regex into a literal
backspace character, silently disabling a pattern. Both were found by running it
against a document already known to be bad, then checking it said so. A tool that
returns zero is only informative once you have watched it return non-zero on
something you know is broken.

Recorded as RDR-001 and RDR-002.

## §12 — The first live run scored the bench, not the detector (2026-09-29)

Running all nine cells against a real model for the first time produced four
failures. Every one of them was in the bench, and three of the four would have
contaminated the study silently rather than loudly.

**Agent mode scored 0 of 4 on output shape in two domains, while answering
every input.** The format rule demands a line beginning APPROVE, DECLINE or
ESCALATE. The corpus asked "what is the current status of account AC-4000?".
There is no decision in that question, so the model answered the question. A
model doing the sensible thing with an incoherent instruction was being recorded
as a compliance failure.

The tempting fix was to relax the format rule, and it was the wrong one. Three
output shapes exist so the detector's per-shape thresholds have three genuinely
different shapes to be fitted against; a decision line is the most distinctive
of the three, and softening it collapses `agent` into `summary` and costs the
study an axis. The corpus was rephrased instead — same records, same tool shape,
same position in the list, and decision framing only for the mode whose
consumer sends decisions.

**A quarter of every corpus came back empty.** The `compute` template asks for a
ratio from a principal's figures, and no tool exposed those figures: entities
were keyed by entity id, and the principal-keyed read returned only prior
records. The model called four different tools hunting for an income number,
exhausted the step budget, and the cell returned `""`. Two separate defects sat
behind one symptom: an unreachable tool path, and a step budget whose exhaustion
threw the input away. Both are fixed: the principal-keyed read now
carries the figures, and exhaustion now withdraws the tools and demands one
final answer, still flagged.

**The model emitted its own deliberation into the output** with a closing
`</think>` whose opener never arrived, despite `think` being off. Unstripped,
the detector would have been scoring the model thinking aloud as output.
The volume of that thinking is exactly the kind of thing that changes when a
model is swapped, so it would have read as a loud and entirely spurious signal.

**One quarter of outputs were truncated mid-sentence** at `num_predict=320`.
Cut-off text is a confound in the same way: the detector would read a length
difference that came from the cap rather than from the system. Raised to 512,
and `finish_reason` records the cases where it still bites.

### Why this is worth a section

Nothing here was found by 159 passing unit tests. Every failure was a place
where a hand-written test double had been more cooperative than reality, the
fifth and sixth entries in a list that already had three. The scripted chat
function always terminated, so exhaustion was never really exercised; no fake
ever emitted a `</think>` tag; no fake ever declined to find what it was
looking for.

**The separation of the `bench` and `engine` seats did its job here.** All four
defects are ones that would have flattered the detector if they had been
discovered after tuning against them rather than before. They were found by
running the systems under test on their own, with no detector attached and
nothing yet to protect.

The standing process fix is now overdue rather than merely open: build test
doubles from captured real responses rather than from memory of the API.
