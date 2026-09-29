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
| the paper | GAP — not drafted. A different audience; needs its own contract row. |
| dataset cards | GAP — belongs with `palworld-rag` when that is published. |

## Explicitly not owned

The family ledgers and `HANDOFF.md`. Their reader is a maintainer with full
context, so terseness and grep-ability beat accessibility there. Style follows
audience, not author.

## Known gaps

- The jargon list in the checker is hand-maintained, so a new project term is
  invisible to it until someone adds it.
- Nothing checks whether a worked example still matches actual program output. A
  README example that has drifted from reality is worse than none.
