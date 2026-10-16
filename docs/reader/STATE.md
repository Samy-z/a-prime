# reader — STATE

## Live

- `docs/reader/METHODS.md` — the audience contract and the style rules.
- `scripts/check_prose.py` — advisory report on em-dash density, sentence length
  distribution, bold density, internal identifiers, and terms used without an
  explanation nearby.

## Artifacts owned

| Artifact | Status |
|---|---|
| `README.md` | **reviewed and rewritten** 2026-09-29 (RDR-001) |
| `NOTICE`, licence statements | reviewed |
| the paper | **outlined** 2026-10-04, `docs/reader/paper-outline.md`; every section **drafted** in `paper/draft.md`; section 8 and Appendix F **rewritten 2026-10-16 against the complete nine-cell k=6 matrix in the two-question shape** (STD-012: the registered question answered at its width, the format-and-k finding labelled post hoc, the k=6 sizing slip disclosed in bold above the table), the silent cells classified under MTH-025 from the committed diagnosis files, the k=20 rows bracketed; the 2026-10-16 cold-read fix list taken; **pending after the estimator's tie fix (ENG-010, STD-011 third append): the §8 hospitality sentence "8 touched inputs above all but 2 decoys, an estimate of 0.375" and the "4 to 8" count, to be rewritten from the rerun diagnosis files (expected 3 touched and 2 untouched inputs at the top value against 1 decoy, 0.4), and the section 8 table once the k=6 reports are regenerated; the Appendix D demo block was refreshed the same day;** appendices A to F, about 17,800 words; the abstract's result stays blank until the k=20 summary row lands (D25). Owner read about two thirds on 2026-10-04 and confirmed the register; line edits pending (RDR-006 second confirmation). Reader ratified 2026-10-04 (D19): a practitioner who ships LLM systems, so the statistics get explained rather than assumed. The outline grades every claim measured / constructed / asserted and points it at its backing. |
| dataset cards | GAP — belongs with `palworld-rag` when that is published. |

## Explicitly not owned

The family ledgers and `HANDOFF.md`. Their reader is a maintainer with full
context, so terseness and grep-ability beat accessibility there. Style follows
audience, not author.

**Also not owned, by owner decision 2026-09-29:** the nine `docs/knowledge/`
files that the README does not link to — `adapters`, `recorder`, `decoy-fdr`,
`conformance`, `gating`, `mode-clustering`, `faults`, `systems`,
`fault-taxonomy`. Nobody arrives at them without project context, so rewriting
them would cost nine files of effort for a reader who does not exist. They stay
maintainer documents.

This is a decision that expires if the README starts linking one of them. Under
RDR-003 a linked document inherits the linking artifact's audience, so adding a
link is also a commitment to rewrite.

## Known gaps

- The jargon list in the checker is hand-maintained, so a new project term is
  invisible to it until someone adds it.
- Nothing checks whether a worked example still matches actual program output. A
  README example that has drifted from reality is worse than none.
