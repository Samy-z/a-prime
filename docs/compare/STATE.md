# compare — current state

Seat ratified 2026-10-16 (HANDOFF §24 and its amendment). First campaign
live: the assistante-ventes comparison (`docs/compare/campaign-assistante.md`).

| Piece | State |
|---|---|
| Input generation from a usage description | live: 40 deterministic language tasks from the campaign's usage description (`compare/fixtures_ventes.py`, CMP-001) |
| Output store | live: `compare/results/pairwise-ventes.jsonl`, four-arm tuple-atomic resumable store, 800/800 tuples recorded 2026-11-06 (CMP-003/004) |
| Multi-system scheduling | first form: lead rotation over the four-arm roster inside one Ollama, plus the unattended night chain `scripts/night-pairwise.cmd` (collision-guarded). Many-system scheduling not started. |
| Inference-performance measurement | pace instrument live (`compare/pace_ventes.py`, CMP-002); perf fields live in comparator records, never in Trace (MTH-015) |
| Comparison reporting / UI | first form: five-pairing report (`compare/results/pairwise-ventes.report.json` and its readable twin `compare/results/pairwise-ventes.report.txt`) plus the blind judging queue and its scorer (`compare/emit_judging_queue.py`). No UI. |

Campaign state: **measurement plan complete.** The human pass landed
2026-11-10 (CMP-005): of 18 blind cases, phi4-mini 8, llama3.2 6, egal 3,
aucun 1 — near-even, translations 3-1 phi, drafting dead even. The one
open move is the owner's: point ChatADV's default at llama (steadier
against itself, CMP-004) or phi (slight judge edge and MIT licence,
CMP-002/005). Pending engine work unchanged: the §4 pairing-aware
quantities ride the MTH-027 freeze.

Boundary: `tests/test_compare_boundary.py` whitelist carries six public
names (net, detect, recorder, clustering, probes.channels, provenance),
each with its reason in the test file.

Model pool for cross-system work: D10's ratified four (granite4.2:8b,
ministral-3:8b, qwen3.5:9b, ministral-3:3b as the capability axis), weights
on disk; a 2026-Q4 agentic-branded refresh candidate is under research
(HANDOFF §24 amendment). The cross-system null proposal
(`docs/methods/cross-system-null-proposal.md`) still awaits owner
ratification; the pairwise stage ran under the ratified MTH-027 freeze.
