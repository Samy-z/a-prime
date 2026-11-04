# compare — ledger

Append-only settled findings: stable id (CMP-###), date, evidence,
reopen-if. Grep before investigating. No entries yet.

## CMP-001 — The pairwise stage sized and scoped, owner-ratified (2026-11-04)

The assistante campaign's comparing half, frozen before any pair is
recorded. **Pair selection rule:** the two fastest French-capable candidates
of the pace pass. **Sizing:** n = 40 language tasks (the T3/T4 fixtures,
grown this day from 14 to 40: 24 inbound messages, 16 outbound briefs),
k = 20 samples per arm, q = 0.10, matching the study configuration whose
calibration passed its pre-registered test (STD-013). The 14-task set was
caught against the 1/q floor before running: at q = 0.10 the detector can
never report fewer than ten findings, and ten of fourteen was too tight to
be useful. Growing n was chosen over loosening q, which would have weakened
the guarantee that makes the comparison worth trusting. **Design:** Design R
as frozen in MTH-027, four-arm pair (M1, M1', M2, M2'), all arms interleaved
per (input, sample index), each model's own second run as its null.
**Evidence:** `compare/fixtures_ventes.py` at this commit (deterministic;
the byte-identity test covers the grown set); the owner's ratification
message, 2026-11-04.
**Reopen if:** the pace pass leaves fewer than two French-capable candidates
standing, or Design R's first live pair contradicts its validation.

## CMP-002 — Pace pass complete; the pair is llama3.2:3b + phi4-mini (2026-11-04)

Measurement plan item 1 ran to completion on the dev machine, CPU only
(`num_gpu: 0`), all 40 language tasks per candidate, resumable file
`compare/results/pace-2026-11.json` (committed; runtime state is data).

| candidate | size | median wall | median tok/s | outputs |
|---|---|---|---|---|
| llama3.2:3b | 2.0 GB | **2.8 s/task** | 26.2 | 40/40 real text |
| phi4-mini:latest | 2.5 GB | **3.0 s/task** | 21.8 | 40/40 real text |
| ministral-3:3b | 3.0 GB | 4.7 s/task | 19.3 | 40/40 real text |
| qwen3.5:4b | 3.3 GB | 33.7 s/task | 12.5 | **0/40 — all empty** |
| smollm3 | — | — | — | no tag under tried names |
| lfm2.5 | — | — | — | no tag under tried names |

Absolute seconds are dev-machine numbers; the office CPU will be slower.
Ratios carry the decision, per the campaign doc.

**qwen3.5:4b is excluded as measured, and the finding is sharper than
"slow":** every one of its 40 tasks consumed the full 400-token budget and
returned an EMPTY visible response — the thinking-mode default swallowed
the whole budget before any answer. Two consequences. (1) No re-measure
with thinking disabled can rescue it here: its decode rate, 12.5 tok/s, is
last of the four measured regardless of where the tokens go, so it cannot
reach the top two. (2) Any integration that calls `/api/generate` with
default settings on this model gets empty strings — ChatADV's provisional
default was moved off it the same day for exactly this reason.

**French gate** (the rule in CMP-001 says fastest FRENCH-CAPABLE, and the
pace file stores lengths, not text): `compare/spotcheck_french.py` captured
three tasks per candidate (en→fr, de→fr, a French outbound brief) into
`compare/results/french-spotcheck-2026-11.json`, read by the recording
session. Both pass: French replies, business register, intelligible.
Neither is clean — llama3.2 calqued German word order ("est incomplète
arrivée") and rendered "next Friday" as "la prochaine semaine", a
date-fidelity slip on a payment promise; phi4-mini made agreement errors
("arrivée incomplet") and one redundancy ("vous rappeler le rappel").
One sample each, an anecdote, not a ranking: ranking the two is the
pairwise stage's job, now unblocked with this pair.

**License note for the deliverable:** llama3.2 ships under the Llama 3.2
Community License — internal commercial use is fine at this scale, but a
shipped app must carry "Built with Llama". phi4-mini is MIT. If the
pairwise stage ends near a tie, license simplicity is a legitimate
tiebreaker in phi4-mini's favour.

**Instrument corrections, recorded:** the first pass looked up a pulled
bare tag under its bare name, so phi4-mini's size was stored as 0.00 GB;
the field was corrected post-run from `/api/tags` (2.49 GB) and
`resolve()` now matches the `:latest` spelling. A stale "14 tasks" print
became the live count. Neither touches any measured timing.

**Reopen if:** the pairwise stage finds either model unusable at French in
quantity (the gate read three outputs, the pairwise records 1,600 per
model), or the missing tags (smollm3, lfm2.5) are located AND both
nominated models fail.
