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

Campaign state: **closed 2026-11-12 (CMP-006).** The owner ratified
phi4-mini as ChatADV's default; the app serves the campaign's measured
regime (temperature 0.2, 400-token budget, CPU only) at ChatADV commit
388d8de. llama3.2:3b stays one ASSISTANTE_MODELE away. Open follow-up,
not blocking: the engine's roster and r>1 work shipped 2026-11-11
(ENG-011), so the two CMP-003 pending quantities are now computable from
the stored arrays; CMP-003's reopen clause is live until they are
appended.

Boundary: `tests/test_compare_boundary.py` whitelist carries six public
names (net, detect, recorder, clustering, probes.channels, provenance),
each with its reason in the test file.

Model pool for cross-system work: D10's ratified four (granite4.2:8b,
ministral-3:8b, qwen3.5:9b, ministral-3:3b as the capability axis), weights
on disk; a 2026-Q4 agentic-branded refresh candidate is under research
(HANDOFF §24 amendment). The cross-system null proposal
(`docs/methods/cross-system-null-proposal.md`) was ratified 2026-11-04
with the other two proposals (MTH-027, HANDOFF §27); the pairwise stage
ran under that freeze.
