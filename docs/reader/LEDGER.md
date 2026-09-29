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
