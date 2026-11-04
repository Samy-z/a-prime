# compare — current state

Seat ratified 2026-10-16 (HANDOFF §24 and its amendment). Nothing is built.

| Piece | State |
|---|---|
| Input generation from a usage description | first real campaign opened 2026-11-04: `docs/compare/campaign-assistante.md`, fixtures in `compare/fixtures_ventes.py` |
| Output store | not started |
| Multi-system scheduling | not started |
| Inference-performance measurement | not started (methodology before code: serving load changes outputs, MTH-015) |
| Comparison reporting / UI | not started |

Model pool for cross-system work: D10's ratified four (granite4.2:8b,
ministral-3:8b, qwen3.5:9b, ministral-3:3b as the capability axis), weights
on disk; a 2026-Q4 agentic-branded refresh candidate is under research
(HANDOFF §24 amendment).

The boundary test promised by METHODS guardrail 1 exists:
`tests/test_compare_boundary.py`, whitelist empty. The assistante campaign's
pairwise stage waits on the cross-system null ratification; pace and
footprint measurement does not.
