# reader — LEDGER

Append-only settled findings about outward-facing writing. Prefix `RDR-###`.
Never edit an entry in place; correct it with a dated append below.

Entry format: id, date, finding, consequence, evidence, reopen-if.

---

## RDR-001 — The README assumed knowledge no first-time reader has
**Date:** 2026-09-29
**Finding:** Owner review. The README referenced concepts a stranger cannot
relate to on first read, used compressed prose, and carried recognisable
machine-writing habits. Measured with `scripts/check_prose.py`:

| signal | before | after | target |
|---|---|---|---|
| em dashes per 1000 words | 15.0 | **0.0** | <= 3.3 |
| sentence fragments (under 8 words) | 15% | 12% | < 15% |
| bold spans per 1000 words | 26.0 | **9.6** | <= 12 |
| terms used with no explanation nearby | **11** | **0** | 0 |

The eleven undefined terms were: false discovery rate, natural language
inference, entailment, mode-share, decoy, probe pairs, separability, logprobs,
Daikon, dedup, metamorphic, anti-correlated. Each was obvious to the author and
opaque to everyone else, which is the failure the `reader` seat exists to catch.
**Consequence:** README rewritten to open with the problem rather than the
method, to define every term at first use, and to show a worked example before
any table. A new seat owns outward-facing artifacts and is forbidden from
assuming project context.
**What did NOT change, deliberately:** the ledgers. They stay dense and
identifier-heavy, because their reader is a maintainer with full context who
wants the finding, not an on-ramp. Style follows audience, not author.
**Evidence:** before and after both measurable via
`python scripts/check_prose.py <file>`; the old version is recoverable with
`git show <commit>:README.md`.
**Reopen if:** the paper is drafted, which is a different audience again and
needs its own row in the audience contract.

## RDR-002 — The prose checker passed a document with twenty undefined terms
**Date:** 2026-09-29
**Finding:** The first version of `defined_nearby()` accepted any of `is`, `:` or
`(` within 240 characters of a term as evidence it had been explained. Those
appear in almost any prose, so it reported **zero** undefined terms in a README
that manifestly had eleven.

A second defect followed the fix: an escaping layer collapsed `\b` in one regex
into a literal backspace character (0x08), which can never match, silently
disabling the "term, a gloss like this" pattern. Visible only in `cat -A`.
**Consequence:** the heuristic now requires a gloss **adjacent** to the term, in
one of four shapes, and was validated by confirming it flags 11 terms on the old
README and 0 on the new one. A checker that returns zero is only informative once
you have seen it return non-zero on something you know is bad.
**Evidence:** both versions in git history; the discriminating test is
`git show <commit>:README.md` piped through the current checker.
**Reopen if:** the term list grows enough that maintaining it by hand stops being
worthwhile, at which point extract it from the docs automatically.

## RDR-003 — Linking a document from the README changes its audience
**Date:** 2026-09-29
**Finding:** The audience contract classed `docs/knowledge/*.md` as documents for
someone who already has project context. But the README points newcomers at
`probes.md` and `detector.md` as suggested entry points, so in practice their
reader has read one page and nothing else. Measured before rewriting:

| | probes.md | detector.md |
|---|---|---|
| terms used with no explanation nearby | 6 | 6 |
| internal identifiers used as references | 7 | 4 |
| em dashes per 1000 words | 10.7 | 6.7 |
| bold spans per 1000 words | 17.6 | 20.0 |

**Consequence:** the contract now says a document linked from an outward-facing
artifact inherits that artifact's audience. Either rewrite it for that reader or
stop linking it. Both files were rewritten; all four signals now pass on both.
**Also added to the style rules:** bullet points must stand alone. Lists are read
first and often read alone, so a bullet that only makes sense after the paragraph
above it has failed at the job bullets are for. Owner observation.
**Evidence:** `scripts/check_prose.py` on both files, before and after.
**Reopen if:** a ledger is ever linked from the README, which would force a
choice between linking it and keeping it terse.

## RDR-004 — The prose checker gave a false pass three times before it worked
**Date:** 2026-09-29
**Finding:** Four separate defects, all of which made the checker report a clean
document when it was not:

1. The first gloss test accepted `is`, `:` or `(` anywhere within 240 characters,
   which matches almost any prose. It reported 0 undefined terms in a document
   with 11.
2. An escaping layer turned `\b` in one pattern into a literal backspace
   character, silently disabling a rule. Visible only under `cat -A`.
3. Emphasis markers were not stripped, so `**AUC**, area under the curve` read as
   a term followed by an asterisk rather than by a comma, and flagged as
   undefined.
4. Terms matched as substrings, so `NLI` matched inside `DeBERTa-v3-base-MNLI`
   and was reported undefined in a document that never used the acronym.

A fifth suspected defect was not real. Accepting an em dash as a gloss marker was
removed on the theory that it caused a false pass, and it plausibly could have,
but the false pass being investigated came from a wrong control: `git show
HEAD:README.md` was the already-rewritten file, so the old and new versions were
being compared against each other. The dash rule is still gone, on the narrower
grounds that dashes mark asides at least as often as definitions.
**Consequence:** the checker errs toward flagging by design. A false alarm costs
a reader thirty seconds; a false pass ships a cryptic document. Any change to the
gloss test is validated by confirming it still flags 11 terms on the pre-rewrite
README and 0 on the current one.
**Lesson recorded against process:** a tool that reports zero is uninformative
until you have watched it report non-zero on something you know is bad, and the
control has to be the document you think it is.
**Evidence:** pre-rewrite README recoverable via the parent of the commit whose
message begins "Rewrite the README".

## RDR-005 — The contract had no row for a report to the owner, so one was written in ledger voice
**Date:** 2026-10-03
**Finding:** The owner asked for a review to catch up after a long session. I
wrote 1,800 words containing **48 internal identifiers**, which made reading it
a lookup exercise. The owner's note: references force the reader "to go back and
forth to find the meaning".

**Rule 2 of the audience contract already forbade this**, in those words: an
identifier may appear as a parenthetical pointer after the idea is explained in
plain words, never as the explanation. So the rule was not missing and was not
wrong.

**What was missing was a row in the table.** The contract covered the README, the
paper, dataset cards, knowledge docs, ledgers and HANDOFF. It did not cover a
report written for the owner, which is a document type this project produces in
almost every session. With no row, the default was ledger register, and ledger
register is correct for ledgers and wrong for anything read start to finish.

The row now exists, with a test: a reader should get the whole picture without
opening a second file, and the extra words that costs are worth paying.

**A second piece of feedback, on sentence construction.** The owner also asked
for plainer grammar: "humans don't use perfect relative grammar like you do", and
it forces "mental gymnastics that isn't required". This is a sharper version of
the staccato-fragments item already in the style list, and it points the other
way. The problem is not short sentences but **long correct ones**: stacked
relative clauses, long subject phrases before the verb, and cleft openings. Each
is grammatically fine, which is why it survives self-review, and each makes the
reader hold several things in memory before the sentence resolves. Added to the
habits list with the three shapes named and a mechanical fix.

**Why this kept happening.** Both notes describe the same failure as RDR-001: a
document written by someone with full context, for someone without it. The seat
exists for that reason, and the seat was not consulted because a report did not
look like an artifact.
**Evidence:** the untracked `docs/study/REVIEW-2026-10-03.md`, 48 identifiers in
1,800 words by `scripts/check_prose.py`; owner notes 2026-10-03.
**Reopen if:** a new document type appears with no row in the table, which is the
condition that caused this.

## RDR-006 — Three attempts to measure register all gave a clean score on prose the owner found hard to read
**Date:** 2026-10-03
**Finding:** The owner said my writing is "trop soutenu", too elevated a
register. I tried three times to turn that into something the prose checker
could measure. All three failed, and the failures are more useful than a fourth
attempt would be.

**First guess: sentence construction.** Stacked relative clauses, long subject
phrases, cleft openings. The owner corrected this directly: "it's my bad, i
missframed what was wrong in your style". Not the problem.

**Second guess: elevated vocabulary.** A list of words with plain twins, written
from a style guide rather than from my own text: eschew, paucity, remit,
obviate. Run against the catch-up review, the very document under criticism, it
found **two hits in 1,841 words**. The words were not ones I use.

**Third guess: nominalisation and adverbs.** Verbs turned into abstract nouns,
plus -ly adverbs doing argumentative work. This one looked promising: the review
scored 29.3 abstract nouns per 1000 words against the README's 18.2. Then I
excluded the project's own technical terms, which is necessary because
"contradiction" and "entailment" are channel names rather than style choices.
The gap nearly closed: 16.3 against 13.8. And the README, which the owner
approved, scores **worse** on adverbs than the review: 11.0 against 7.6.

**All three were removed rather than kept.** RDR-004 already records that this
checker gave false passes three times before it worked. A measure that returns
"ok" on prose the reader struggled with is a fourth false pass, and false
reassurance is the specific failure this seat exists to prevent. The checker is
back to the four signals that were validated against real documents.

**What I believe is happening, unmeasured.** Reading my own samples, the
elevation is not in the words but in saying things as compressed figures instead
of saying them: "the engineering is well ahead of the evidence", "nothing owned
it", "this cuts against the pinned-instruments rail". Each asks the reader to
unpack a metaphor before reaching the point. Alongside that, essay connectives
that announce an argument rather than making one: "Worth noting", "Stepping
back", "The honest summary is".

**Confidence: low, and it is my own diagnosis of my own blind spot**, which is
precisely the thing this seat was created because nobody can do. It needs the
owner to point at specific phrases that felt wrong. Until then it is a
hypothesis, not a finding, and no checker should imply otherwise.
**Evidence:** three removed implementations; counts quoted above, reproducible
with `scripts/check_prose.py` against `README.md` and the untracked review.
**Reopen if:** the owner supplies examples. Then the list is built from their
judgement instead of my guesses, which is the step I skipped three times.

## RDR-006 — CONFIRMED (dated append, 2026-10-03)

The owner confirmed the low-confidence hypothesis in the entry above, and named
it as the one rule the README's standards were missing: **"I say things in
compressed figures instead of saying them."** Everything else in the existing
rules stays as it is, and the owner noted that the identifier problem was
already covered by rule 2, so no new rule was needed for it.

So the three failed measurement attempts were not wasted, but they were done in
the wrong order. The hypothesis that turned out to be right came from reading my
own samples, which cost nothing. The three attempts to mechanise it came first
and cost the most. **Read the examples, form the hypothesis, check it with the
reader, and only then consider whether it can be measured.** I did those four
steps backwards.

Now rule 7 in the audience contract, with a before-and-after table and a test:
if a phrase stands in for a claim, write the claim.

**Still not measurable, and now deliberately not measured.** "Is this phrase a
figure standing in for a claim" needs a reader. The checker keeps its four
validated signals and says nothing about this, which is the honest state rather
than a gap to be filled.

## RDR-007 — A decision I restated for five days was never written down
**Date:** 2026-10-04
**Finding:** The owner asked what "D19" actually decides. I could not answer
from the repository, because **it is not in the repository.** The only commit
containing the string is yesterday's, in a file I wrote myself. For five days it
appeared in every position block as an open decision, and it existed nowhere but
my own messages.

**What it referred to is also already half-done.** The audience contract has had
a row for the paper since 2026-09-29, added in commit `225832c` in the same
commit that created this seat. Meanwhile `STATE.md` still said the paper "needs
its own contract row". Two documents in the same family, contradicting each
other, for five days.

So the real state was: a provisional row written as a first guess, never
examined, with a stale gap note beside it and a decision id attached to neither.

**The process failure is specific and worth naming.** The standing disciplines
say to close every reply with a position block, because "a decision never
restated is a decision made by default". I restated this one constantly. That
turned out not to be the protection it looks like. **Restating a decision in
conversation is not recording it.** The conversation is ephemeral and the
position block was carrying a memory of a memory, which is why nobody could
check it and why it drifted out of sync with the file it was about.

The fix is one line of discipline: when a position block names an open decision,
that decision needs a home in the repository on the same day, even if the home
is one sentence saying it is open and why. An id with no file behind it is worse
than no id, because it looks like a reference.

**Corrected now.** The row is marked provisional and unratified, `STATE.md` no
longer claims the row is missing, and the actual choice is written out with its
options so the owner can decide against something concrete.
**Evidence:** `git log -S"D19" --all` returns one commit, dated 2026-10-03;
`git log -S"a researcher in a neighbouring field"` returns `225832c`, dated
2026-09-29.
**Reopen if:** another decision id appears in a position block without a file
behind it, which this entry exists to prevent.

## RDR-008 — A status row is a claim with no instrument behind it
**Date:** 2026-10-04
**Finding:** Three status rows in `docs/knowledge/README.md` were wrong at
once, in both directions. `provenance.md` was marked done on 2026-09-25 and did
not exist until 2026-10-04. `cells.md` was marked GAP and had existed since
2026-09-29. `environment.md` had existed since 2026-10-03 and had no row. Add
RDR-007, where `STATE.md` said the paper needed a contract row five days after
one was added, and that is four stale status claims in one week across two
index files.

**The pattern.** A row that says "done" is a sentence that looks like a fact.
Nothing checked it, so it stayed true-looking for nine days while being false,
and a session that trusted it would have skipped writing the doc. The same
failure as ENG-007's `0 flagged`: a healthy state and a broken one print the
same thing. The disciplines already say to ask for the instrument rather than
the summary; a status table is the summary.

**Consequence:** `tests/test_docs_index.py` now reads the index and fails when
a row marked done or frozen names a file that does not exist, when a row marked
GAP names one that does, or when a file under `docs/knowledge/` has no row. It
runs with the rest of the suite, so a stale row fails the same command that
every commit runs. It cannot tell whether a doc that exists is *current*; it
only closes the gap between "the file is there" and "the index says so".
**Evidence:** `git log --format=%ad --date=short -- docs/knowledge/cells.md | tail -1`
gives 2026-09-29; the index row read "GAP — week 3" until this commit.
**Reopen if:** a status claim lives somewhere the test does not read. The
family `STATE.md` files are the obvious next place and are not covered.

## RDR-008 — APPEND (2026-10-04): a fifth instance, and the limit of testing this

Two additions to the entry above, both from the local session.

**A fifth stale claim, and it was mine.** The provenance fix in `75081ad` added
`row_provenance` and `check_row_provenance` to `src/aprime/provenance.py` and
did not touch `docs/knowledge/provenance.md`, which went on describing the gap
as open. The same-commit rule is the first standing discipline in `CLAUDE.md`
and I broke it within hours of the cloud session fixing four instances of the
same family of failure. The cloud session caught it and corrected the doc.

**`tests/test_state_files.py` now covers the family STATE files, and it would
not have caught any of the four.** The STATE files are not the same shape as the
knowledge index: five status words across them, columns that differ per family,
and many rows naming a capability rather than a file. "Domain x format factorial
| GAP" has no path in it, so no script can judge it.

So that suite checks path references only. A row naming a file that is absent
fails; a row calling something a GAP while it sits on disk fails. Verified
failing in both directions on synthetic rows, because a check nobody has seen
fail is decoration.

Three of the four original failures were in the knowledge index, which
`test_docs_index.py` covers. The fourth was a prose contradiction in
`reader/STATE.md`, where the row said the paper needed a contract row while the
contract already had one. No path was wrong.

**The honest conclusion: the observed failure mode resists testing.** What went
wrong four times was a status sentence going stale, and a status sentence is
prose about intent. RDR-004 and RDR-006 already record what happens when a
check is built for something it cannot measure, so this is logged as a bounded
guard rather than a solution. The remaining candidate is a cross-file
consistency check inside the reader family, where `STATE.md` and `METHODS.md`
both enumerate artifacts and must agree on which have contract rows. That one
would have caught the fourth. It is narrow, it is real, and it is not built.
