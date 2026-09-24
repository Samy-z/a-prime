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

**FROZEN 2026-09-24** — `docs/knowledge/fault-taxonomy.md`. 14 classes:
F1-F9 incident-evidenced (grade A/B operator sources), F10-F14
mechanism-evidenced (documented mechanism, no post-mortem with a blast radius).
Blast radius is an independent axis B0-B3, crossed with class, not a per-class
attribute (BCH-001).

Nothing may be tuned against it. Amendments are dated appends to the log at the
foot of that file, never in-place edits.

Dropped at freeze: decoding-parameter change, for having zero documented
instances (BCH-002). Also deliberately excluded and recorded there: retrieval
ACL drift, destructive agent action, and three practitioner-folklore classes
with no grade A/B source.

## Red-team set

> GAP — a fault set authored with no visibility into detector internals, held
> out completely. The owner of this task must not be the engine seat.

## Seed record

> GAP. The taxonomy is shared by all seats; the *seeds* — which inputs receive
> which fault at which severity in a given run — stay with `bench` and are not
> visible to the seat tuning the detector. That is the separation, not the
> class list.
