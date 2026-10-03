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

## §13 — Two ratifications and a rename (2026-09-30)

### MTH-023 ratified: the seed mirrors the deployment

The owner's first reading was that A against A-prime measures the system's
self-variance, and that if production instantiates an agent at the same weights
with the same seed then the arms should follow that standard. The first half is
exactly right and is the whole point of the decoy arm. The second half rested on
a premise about production that does not hold: deployments pin weights, and they
almost never pin the seed. Anthropic's Messages API exposes no seed at all,
OpenAI documents its `seed` as best effort and added `system_fingerprint`
precisely because the backend can move underneath a pinned one, and local servers
leave it unset by default. The standard is same weights, unpinned seed.

So the owner's own principle, follow the deployment, decided it. The rule
ratified is **mirror the seed policy of the deployment under audit and record
which regime a run was made in**, not the blunt "always differ" first proposed.
Where a deployment really does pin its seed, its self-variance really is near
zero, that is the correct thing to report, and target-decoy FDR is the wrong
instrument for it: an exact diff answers the question directly.

This puts a hole in the pinned-instruments rail, deliberately and on the record.
Pinning every parameter for reproducibility would destroy the one thing the
method needs free. Reproducibility now means the seeds are **known**, not that
they are **equal**. `docs/methods/METHODS.md` rail 4 and the CLAUDE.md summary
both say so.

The guard is `decoy_independence_warnings` in the recorder. It warns rather than
refusing, and it is duck-typed rather than reading the adapter Protocol, because
the Protocol carries no sampling configuration and widening it would make the
detector depend on something a stranger's system may not expose. That pressure is
recorded as ENG-006 instead of conceded.

**Unresolved, and the part worth worrying about.** Two measurements of the same
model on the same server disagreed about whether a pinned seed gives identical
output, and the difference tracked whether other requests ran in between. Which
cluster a pinned-seed run lands in appears to depend on server cache and batch
state, which is not a study variable and is not in provenance. The null width is
therefore unstable in a way nothing records.

### The agent arm ratified: keep the heterogeneity, report the degradation

The agent format's outputs run 11 to 396 words where summary runs 30 to 104, and
a threshold fitted per output shape has little to hold on to across that spread.
This was put to the owner as a problem to engineer away. The owner rejected that
framing and was right to: real production agents do emit a one-line decision one
time and three paragraphs the next, so narrowing the bench until the detector
performs well is developing against the answers, and a tool validated only on
well-behaved synthetic agents invites exactly the criticism that it does not
apply to production, which is the target.

Ratified: **the spread stays, and whether detection survives it becomes a
measured axis rather than a design constraint.** One carve-out, narrow and worth
holding: heterogeneity traceable to our own incoherent instructions is a bug and
gets fixed, while heterogeneity a competent operator would also have produced
stays. The test is whether a competent operator would have written that prompt.

The corollary is that the fix belongs on the detector side rather than the bench
side: stratify by **realised** output shape rather than by declared format. That
has to land before any fault labels are consulted, or it becomes the same
developing-against-the-answers failure by a different route.

### A cell's `mode` is now its `output_format`

`mode` named two unrelated things: a cell's output format, and a semantic mode
that `clustering.py` finds in an output cloud. The owner hit the collision and
could not tell which was meant, which is evidence rather than bad luck. `MODES`
is now `FORMATS` and `Cell.mode` is `Cell.output_format`, confined to the cells
package, its tests, its scripts and its docs. Nothing in the detector changed,
because "semantic mode" is the older and better-established use of the word.

Results recorded before today carry `mode` where the new ones carry `format`;
`check_shape_distinctness.py` reads either.

## §14 — Long runs are pausable, because quality is not being traded for speed (2026-09-30)

The first end-to-end detector run put a number on something that had been a
guess: recording took 589 seconds and the entire detector stage took 10. The
detector is not the expensive part and never was. Sizing the study properly, per
MTH-024, means 30 or more inputs per output shape, which is roughly 75 minutes of
GPU per cell and a full day per system across nine cells.

Asked to choose between fewer inputs and more time, the owner chose time: the run
should be pausable and resumable, started when the machine is otherwise idle and
stopped on request. That is the right call. The alternative was cutting the
corpus, and MTH-024 makes that unusually expensive because the discovery floor is
a hard 1/q rather than a gradual loss of power.

Three things had to be true for this to work, and only the first already was.

**Stopping must not cost the work.** The recorder was already checkpointed and
triple-atomic, so a kill only ever lost the triple in flight. `should_stop` now
adds a clean stop at a triple boundary, signalled by a file appearing on disk
rather than a process signal, because whoever wants the run stopped is usually
not at the terminal that started it.

**A paused run must not be analysable.** `record` raises `RunPaused` instead of
returning what it has. A partial recording has short clouds for the inputs it
reached and none for the rest, and the detector consumes it perfectly happily:
thresholds fitted to fewer decoys, mode shares over two samples instead of ten,
and nothing in the report to say so. There is no way to notice it downstream, so
it is refused upstream.

**The checkpoint key must be the configuration, not the run.** The first version
named the checkpoint after the run timestamp, which no rerun can find. That is a
crash log wearing a checkpoint's name. Keying on the configuration hash also
means a resume cannot silently mix work from two different configurations,
because changing the corpus, k, the fault or an instrument changes the key.

**One consequence that was nearly missed.** A resumed session never re-invokes
the triples it skips, so anything the harness learns while invoking is lost
unless it is written down. The per-input fault activation labels are exactly
that, and they are ground truth. They are now persisted after every invocation,
and the run says how many inputs carry no label so an activation rate from a
resumed run reads as a lower bound rather than a measurement. This generalises:
**any instrumentation that observes the act of recording, rather than the
recording itself, has to be persisted alongside the checkpoint.**

### The README now states the discovery floor

MTH-024 is a product limitation before it is a study parameter, so it went into
the README's honest limits in the reader register: the tool cannot report fewer
than ten changed inputs at its default setting, an empty report means "fewer than
ten changed" rather than "nothing changed", and anyone who needs to catch one
specific broken input should compare that input directly instead. Ratified by the
owner before writing.

## §15 — A hosted model is a probe, not a study arm (2026-10-03)

Two decisions, D22 and D23.

### D23: GPU work stays on the owner's PC

Decided. The alternative was a rented box, now that the runners read
`APRIME_OLLAMA_HOST` and the system under test can live anywhere. Not taken,
because renting costs money and the point of the current cloud trial is that it
is free. Recording therefore stays pinned to one machine, and that machine has
to be awake and have Ollama running.

### D22: a hosted model joins as a costed probe, with a $10/month ceiling

The owner wants to compare a hosted model against the local pool and will spend
at most $10 a month. The question was whether that fits.

**Token volume, from the measured smoke run** at n=40, k=6, three arms. Traffic
is about 95% input, because every invocation sends a system prompt plus eight
tool schemas and gets back forty words.

| | tokens | at ~$0.25/M in | at ~$1/M in |
|---|---|---|---|
| one cell | 2.2M to 6.5M | $1.22 | $4.89 |
| one domain, three formats | 12.2M | $3.66 | $14.66 |
| nine cells | 36.6M | $11.00 | $43.98 |

So the budget buys one domain on a cheap model, or two cells on a dearer one.
The full factorial does not fit at either price. The agent format is three times
the cost of summary, the same ratio as on local GPU, so dropping it halves the
bill. Roughly half of each prompt is the identical system message and tool
schemas, which providers usually discount when cached, and the recorder already
groups by input to make that caching work. The size of that discount is not
measured.

**The reason it cannot be a study arm.** A hosted model cannot be pinned. The
provider can change the weights mid-run, with no version string and no notice.
That breaks the pinned-instruments rail, and it means a hosted baseline cannot
be re-run later and compared, which is what the transfer matrix needs.

**So it is scoped as a probe.** One cell, one fault, the same configuration as
the run that worked, for one to five dollars. The question it answers: does the
detector behave the same way on a hosted model as on a local one? Matching
channel separation is an external-validity result worth having in the paper.
Different separation is a more interesting finding at the same price.

**One property makes it better than it looks.** Most hosted APIs expose no seed.
MTH-023 says the arms must mirror the deployment's seed policy, and the
unpinned case is the one we argued is ordinary but have only tested locally. The
hosted probe exercises it at no extra cost.

**What this probe must record**, since reproducibility is not available: the
date, the exact model string, any version or fingerprint field the API returns,
and the fact that none of it is a pin. A number from this probe is a
measurement of one week in one provider's deployment, and the paper has to say
so.

## §15 — AMENDMENT (dated append, 2026-10-04)

**D22 is reversed: no hosted model, not even as a probe.** The reasoning I gave
for the original scoping was also wrong, which matters more than the decision.

### Why it is a no

Both of the owner's reasons are about scope, not method.

**Price.** Ten dollars a month buys one domain on a cheap model and nothing
close to the factorial.

**What affording it would cost.** The agent format is three times the price of
summary, so fitting the budget means dropping it. Agents are the most common
shape of production LLM system, and this project chose eight tools over two
precisely so the study would not be about toy systems (BCH-013). Buying a
hosted comparison by deleting the agent format trades away the thing the study
is for. Consistency and scope outrank a side observation.

### Where my argument was wrong

I said a hosted model cannot be a study arm because it cannot be pinned, and
that this breaks the pinned-instruments rail. The owner pushed back: models
changing under you is the problem this project exists to detect, and the README
says so.

They are right, and the rail's own words say so. It reads "Embedding and NLI
model versions locked." **It protects the instruments, not the systems under
test.** The NLI model and the embedder do the measuring, so if they change, old
numbers stop being comparable. A system under test that changes is not a rail
violation. It is the subject matter.

### The real objection, which is much narrower

Not reproducibility across months. **Stability inside one run.** A and A-prime
have to be the same system, because their spread is the null. If the provider
swaps weights between the A call and the A-prime call for one input, that
triple's null contains a real change, and the decoy arm stops being a null for
it.

How bad: small and bounded. The recorder is triple-atomic and grouped by input
(ENG-001), so the three arms for one sample are consecutive calls seconds
apart. A deployment landing inside that window is unlikely, and across a
six-hour run it would touch a handful of triples out of hundreds.

What genuinely remains is a reproducibility caveat for the paper. A reader
cannot re-run a hosted arm and get our numbers. That is a limitation to state,
not a reason to refuse.

**The method was never the problem.** Had the budget allowed it without cutting
the agent format, a hosted arm would have been sound with a stated caveat. The
decision stands on the owner's reasons, not mine.

## §15 — SECOND AMENDMENT (dated append, 2026-10-04)

**D22 is deferred, not refused.** This decision has now been recorded three ways
in two days: a costed probe, then a refusal, now a deferral. The churn is worth
noting, because two of the three records were driven by my reasoning rather than
the owner's, and only this one reflects what they actually want.

**The stable version.** The owner is sceptical about spending anything while the
project has no reportable result and no paper. They put a figure on it: **$50
for a one-time run across all nine cells is acceptable if it adds meaningful
nuance.** That matches the measured arithmetic, which put nine cells between $11
and $44 depending on the price tier, so the budget is realistic rather than
hopeful. The decision comes back when there are results to judge it against,
which is the right order: you cannot tell whether a comparison adds nuance
before you know what it would be nuancing.

Nothing to build now. When the go comes, the work is one provider adapter behind
the existing boundary, and the boundary already takes a host.

**What changed in the reasoning, for the record.** The first version of this
section said a hosted model could not be a study arm at all. That was wrong, and
the first amendment corrected it. The deferral rests only on money and timing.

## §16 — D19 ratified: the paper is written for a practitioner (2026-10-04)

**First time this decision has existed in the repository.** It was referred to as
D19 in conversation for five days without ever being written down, which RDR-007
records as its own failure. Keeping the number, because that is what it has been
called, and noting that nothing before today backed it.

### The decision

The paper's reader is **somebody who ships LLM systems and might use the tool.**
They may be assumed to have general software literacy and nothing else.
Everything else gets defined, the statistics included.

In practice: not "target-decoy FDR control at q=0.10", but what a false
discovery rate is, why running the baseline twice produces a null, and what it
means for one piece of text to entail another.

The rejected alternatives were a researcher in a neighbouring field, which was
the unexamined first guess, and a reviewer at a specific venue, which was the
tersest and narrowest.

### Why

**The practitioner is the reader most likely to get use out of this**, and the
honest-limits section is the part of the work with the clearest use. Writing for
somebody who already knows statistics loses exactly the reader who needs those
limits spelled out.

**"May assume statistics" was doing unexamined work.** This is the owner's
argument and it is the stronger one. Target-decoy FDR comes from proteomics. A
researcher in machine-learning testing may never have encountered it, so the
assumption was not buying brevity. It was deferring an explanation that still
had to happen, to a reader who would not notice it was missing until they tried
to use the method.

**Explaining complex context simply is underrated.** The owner's point, quoted
because the phrasing is the argument: there is a charm to it, and it is probably
the best vector for quick and consistent human comprehension. The README rewrite
is the evidence inside this project. It got shorter to read and longer on the
page, and the owner's reaction to it was the strongest positive signal any
artifact here has produced.

### The cost, accepted rather than ignored

A paper that explains its own statistics is longer, and length is a harder sell
at a venue that expects the conventional register. That was weighed.

### One consequence to settle later

The paper's contract is now close to the README's. Both are written for somebody
with software literacy and nothing assumed. That is duplication to manage, and
there are two ways out: the README stays a short front door and points at the
paper for anything real, or the two split by purpose, with the README answering
why you would use this and the paper answering what we measured. Not decided.
Worth deciding before the paper is drafted rather than after, or the two will
drift and both will be maintained badly.

## §17 — D24: the README becomes a front door (2026-10-04)

Follows D19. With the paper written for the same reader as the README, the two
would duplicate each other, and the owner chose: **the README is a front door
and points at the paper for anything substantial.**

### Sequencing, which matters here

This cannot be executed yet. A front door that points at a paper which does not
exist is worse than the current README. **The change happens when the paper is
drafted, not before**, and the README stays as it is until then.

### What moves and what stays, because "front door" is not self-explanatory

Moves to the paper: prior art, the findings in detail, the section on ideas that
might be reusable elsewhere, and anything that argues rather than orients.

Stays in the README: what problem this solves, the core idea in one paragraph,
how to run it, repository layout, licence.

### The constraint, and it is not negotiable

**The honest-limits section does not move wholesale.** It is the most-cited part
of this project so far and it is what makes a stranger trust the rest. Burying
it in a paper that fewer people will open would be a quiet downgrade of honesty
dressed up as deduplication.

The headline limits stay in the README: that the tool cannot report fewer than
ten changed inputs at the default setting, that twenty samples per system is the
real minimum, that the figures describe our instruments rather than the
technique, and that nothing has run against a production system. The paper
carries the full version with the numbers behind each one.

A front door that omits the lock is not a front door.
