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
