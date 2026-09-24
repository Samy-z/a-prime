# bench — STATE

## Systems under test

| System | Role | Domain | Format | In transfer matrix? |
|---|---|---|---|---|
| palworld-rag | Development / instrumented reference | games | RAG QA | **No** — dev system, reported separately |
| (9 cells) | Domain x format factorial | GAP | GAP | Yes |

Target factorial: 3 formats (structured extraction, free-text summary,
multi-step agent) crossed with 3 domains (banking, logistics, hospitality).
Fallback is 3x2 or 2x3 with widened intervals — build it to degrade gracefully.

## Fault taxonomy

> GAP — week 0. Freezes before any tuning. Built from published post-mortems,
> not invented. Lands in `docs/knowledge/fault-taxonomy.md`.

## Red-team set

> GAP — a fault set authored with no visibility into detector internals, held
> out completely. The owner of this task must not be the engine seat.
