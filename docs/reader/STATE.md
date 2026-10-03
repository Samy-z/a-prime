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
| the paper | GAP — not drafted. A provisional contract row exists (added 2026-09-29, never ratified); the reader has not been chosen. See RDR-007. |
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
