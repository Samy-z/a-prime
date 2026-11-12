# Campaign: the assistante-ventes comparison (opened 2026-11-04)

The comparator's first real campaign. One user, a sales assistant at an
aircraft-parts company; one question, the comparator's own: **which is the
cheapest local model that does her tasks well on a GPU-less office PC?**
Every constraint is real: company policy forbids external AI services, the
machine is a plain desktop, and the budget for complexity is zero because
the user is not a developer.

## The usage description (the input-generation seed)

Reference hardware, owner-fixed 2026-11-04: **8 GB RAM, a roughly
five-year-old desktop CPU, Windows 11, no usable GPU.** Candidate pool
bounded to **1-4B parameter models** at 4-bit quantisation, served by Ollama
in CPU mode.

Languages: **French is the working language.** English coverage preferred,
not mandatory. Other client languages (German, Spanish, Italian, ...) occur
at random by client origin. Owner's design rule, quoted for the record:
"singular and functional is better than polyvalent but disfunctional" — if
one small model cannot translate reliably, the app gains a dedicated
translation tool instead of a bigger model.

Task families, from her actual week:

| id | family | what happens | LLM's share |
|---|---|---|---|
| T1 | lookup | find an order / its status / its total in the order sheet | none — deterministic parsing; the LLM only phrases the answer |
| T2 | contract fill | carry order fields into a contract template | none — templating; the LLM checks nothing is missing |
| T3 | translate inbound | client message (en/de/es/it) -> French, theme intact | all of it |
| T4 | draft outbound | payment reminders; replies on late payment, incomplete shipment, discount asks (French, optionally client's language) | all of it |

T1 and T2 are deliberately tool-work: the study's own finding is that
low-entropy structured output is both the easiest to automate and the
easiest to certify, and the owner's deterministic-tools design principle
applies in full. The candidates compete on T3 and T4.

## Fixtures

`compare/fixtures_ventes.py`, deterministic, entirely synthetic (invented
parts, companies, prices — the real files never leave her machine and never
reach this repository). Orders carry the owner-specified standard columns:
order_id, product_id, qty, unit price, tax rate, total, status, dates,
client_id; plus products.csv and clients.csv; eight inbound messages across
the three real themes in four languages; six outbound briefs.

## Candidate pool, 1-4B, to verify before any run

| candidate | size | why it is here | verify before admitting |
|---|---|---|---|
| qwen3.5:4b | 4B | the consensus CPU-class pick of 2026 guides | French quality (untested in sources); license at the card |
| llama3.2:3b | 3B | official French among its eight languages | Llama license terms for her company's internal use; "Built with Llama" clause |
| ministral-3:3b | 3B | already benchmarked on the dev machine; Mistral's French pedigree | license tier for commercial internal use |
| smollm3:3b | 3B | six languages, cited support-ticket deployments | French quality; license |
| phi-4-mini | 3.8B | strong small generalist | French quality; MIT expected, verify |
| lfm2.5:2.6b | 2.6B | agent-branded edge model | known malformed-tool-output reports; license revenue cap irrelevant here, verify anyway |

Admission bars mirror BCH-019's: credible org, verifiable license for
commercial internal use, runs under Ollama CPU-only within 8 GB total
system RAM, and no documented breakage on the serving stack.

## Measurement plan

1. **Pace and footprint per candidate** — DONE 2026-11-04 (CMP-002).
   CPU-only on the dev machine (`num_gpu: 0` so the 4060 flatters nobody),
   40 tasks per candidate, results in `compare/results/pace-2026-11.json`.
   Outcome: llama3.2:3b (2.8 s/task) and phi4-mini (3.0 s/task) nominated;
   ministral-3:3b third; qwen3.5:4b excluded (thinking default returned
   empty text on 40/40 tasks AND last decode rate); smollm3 and lfm2.5
   unavailable under tried tags. French gate passed by both nominees via
   `compare/spotcheck_french.py`. A five-year-old office CPU will be
   slower; measured ratios, not absolute times, carry the decision.
2. **Pairwise difference triage with a-prime.** — DONE 2026-11-06
   (CMP-004, run 20261106T075759Z). 800/800 four-arm tuples, zero errors;
   primary selection 18 of 40 inputs at q=0.10 (4/24 translation, 14/16
   drafting); core of 13 stable across all four same-orientation
   replicates; reverse orientation confirms 10 of the 18 and reads
   phi4-mini as the noisier model against itself. Design R per MTH-027,
   sizing per CMP-001, deployment-mirroring record (CPU only, both models
   resident). No study rail crossed; none of these numbers enter the
   paper.
3. **Human judgment protocol** — IN PROGRESS 2026-11-06: flagged inputs
   go to the owner (and the real user where French tone matters) blind to
   which model produced which output. The queue is emitted
   (`compare/results/judging-queue.md`, 18 cases, sides shuffled per case,
   key sealed); verdicts X / Y / egal / aucun per case, then
   `compare/emit_judging_queue.py --score` unblinds the tally
   (protocol: compare METHODS).

## Deliverable

A CMP ledger entry naming the winning candidate with its numbers, and the
app (its own repository; consumes the conclusion, not the machinery)
pointed at that model.

**Delivered 2026-11-12 (CMP-006): phi4-mini**, ratified by the owner on
CMP-005's blind tally (8 to 6 of 18, translations 3 to 1) with the MIT
licence as the pre-filed near-tie tiebreaker; ChatADV points at it since
its commit 388d8de and serves the campaign's measured regime. The
campaign is closed; item 3's standing offer (a second, fully blind pass
by the real user) remains open under CMP-005's reopen clause.
