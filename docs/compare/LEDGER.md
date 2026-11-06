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

## CMP-003 — Reference declared, runner built; nothing recorded yet (2026-11-04)

**A = llama3.2:3b, declared here, before any tuple is recorded**, as
Design R requires ("A is the reference of each pair, declared before
recording"): it is the pace leader and ChatADV's provisional default, so
the campaign's question reads naturally as "does the challenger behave
differently from what the app would ship today?". B = phi4-mini.

`compare/pairwise_ventes.py` (committed with this entry) records and
scores the pair at CMP-001's sizing (n=40, k=20, q=0.10, ~2.7 h CPU for
800 four-arm tuples):

- **Recording is compare-side.** The engine's recorder speaks exactly
  three arms by design; the roster generalisation is engine work under
  MTH-027. The loop honours Design R's layout directly: all four arms of
  one (input, sample index) called back to back, atomic on disk, lead
  rotation over the roster, grouped by input (ENG-001), both models
  resident, CPU only (`num_gpu: 0`), the deployment's own options
  (temperature 0.2, 400-token budget, no seed — MTH-023's mirror rule,
  regime recorded in the meta file). Guards: digest equality across
  resumes (a weight change mid-store aborts, the drift lesson), a stop
  flag, three-strike abort on consecutive tuple failures, and a refusal
  to share Ollama with a main-line recording (MTH-015: one server would
  serialise both runs and pollute both timings).
- **Scoring reuses the frozen pipeline through the public API** — five
  `detect()` passes over arm relabelings (the drift control's pattern):
  the primary selection (targets s(A,B), decoys s(A,A'), r=1,
  select/select_stratified byte-unchanged), the reverse orientation, and
  the three replicate target sets s(A,B'), s(A',B), s(A',B'). Only the
  primary selects; everything else is reported.
- **Two Design R reported quantities are named pending, not computed**:
  the reverse selection against s(B,B') and the cross-pooled (1+d/2)/t
  estimate need the pairing-aware `detect` and the r>1 estimator
  (proposal §4), which are engine work riding the MTH-027 freeze.
  Hand-rolling selector logic in a consumer seat is exactly what the
  rails forbid; the store keeps every array they will need.
- **Boundary:** `ALLOWED_IMPORTS` grew by six names (net, detect,
  recorder, clustering, probes.channels, provenance), each with its
  reason in the test file. Rotation, tuple-atomic resume and the pairing
  shapes are pinned by `tests/test_compare_pairwise.py`.

**Evidence:** the runner and tests at this commit; plan dry-run
2026-11-04 printing 0/800 tuples, ~2.7 h.
**Reopen if:** the engine ships the §4 generalisations (then the pending
quantities get computed from this store and appended here), or the first
live run contradicts the plan's cost by more than 2x.

**Reopened and closed on the cost clause, 2026-11-06 (see CMP-004):** the
live store cost ~6.3 h of CPU against the planned 2.7, a 2.3x miss. Cause
identified, not drift: both pace constants (12 then 19 s/tuple) were
calibrated on translation-class tuples, the only ones recorded when they
were set, and recording is input-major with the drafting class last. Live
medians per call: translation ~4 s, drafting ~11-12 s, so a drafting tuple
costs ~46 s. Within each class the pace was flat all night, so nothing
degraded. Consequence for validity: none (arms interleave within tuples,
1 s apart). Lesson for any future plan line: pace is per task class, never
one constant.

## CMP-004 — First live pairwise: 18 of 40 flagged; drafting carries the difference (2026-11-06)

The assistante campaign's measurement plan item 2 ran to completion
overnight: the store resumed at 29/800 and finished at **800/800 four-arm
tuples, 3,200 samples, zero errors, zero empty outputs**, digests held
across the resume, interleaving gap 1 s. Scored the same morning on the
GPU. Run id **20261106T075759Z**, config 52b45df073b51223; store, meta,
both report files and the night log's tail are the evidence, committed
with this entry (runtime state is data, BCH-018).

**Primary selection (A = llama3.2:3b per CMP-003, B = phi4-mini): 18 of
40 inputs flagged at q = 0.10.** Channels, each against its own decoys:
mode_share 15 (est. FDR 0.07), novel_mode 16 (0.06), nli_directional 11
(0.09); dispersion floor-limited (6 above every decoy, under the 1/q
floor of 10, MTH-024); nli_contradiction reported no separation in all
five pairings, which per ENG-007 is "silent", never "no contradictions".

**The composition is the finding:** 4 of 24 translation inputs flagged
(17%) against 14 of 16 drafting briefs (88%). Where the source text pins
the content, the two models are near-interchangeable; where text is
generated freely, they certifiably diverge on almost everything.

**Replicate stability (Design R's three extra target sets):** counts
18 / 18 / 19 / 16 across the four same-orientation pairings; 13 inputs
flagged in all four, 5 more in three of four (all five inside the primary
selection), 2 at two of four (outside it), none at one. The edge wobbles
by about the ~2 false alarms a q = 0.10 list of 18 expects; the core does
not move.

**Reverse orientation (A = phi4-mini, its own second run as the null):
10 of 40, every one inside the primary 18,** all via nli_directional with
exactly mirrored signs. The mode channels die under phi's null: best cut
10 targets over 1 decoy, estimate 0.20 against q = 0.10. Reading:
**phi4-mini is noisier against itself than llama3.2 is**; llama's tighter
self-null is what makes the mode-level differences selectable. For a
desktop assistant, run-to-run steadiness is itself deployable behaviour,
so this reads in the reference's favour, but the quality call stays with
the human pass.

**Direction of the difference:** on most flagged inputs the directional
channel says phi's outputs carry content llama's do not entail (phi "says
more"); out-01 is the lone input where it runs the other way. Conformance
agrees at the margins: phi broke llama's word-count envelope on 17/800
outputs (2%) and llama phi's on 11/800 (1%); phi sometimes runs past 22
lines and leaves "[Nom...]"-style template placeholders (example stored in
the report). Median lengths per output class are within 15% of each other,
so this is tail behaviour, not a length regime change.

**BCH-009 note in all five reports** (recording crosses midnight UTC, a
chat template may interpolate the date): absorbed by design here. Tuples
are atomic with arms ~1 s apart, recording is input-major, so at most one
input straddles the flip and its arms straddle it together.

**The judging queue (measurement plan item 3) is emitted:**
`compare/emit_judging_queue.py` wrote `compare/results/judging-queue.md`,
18 cases in seeded-shuffled order, two samples per side (one from each of
the model's two arms, seed 20261106), side X/Y re-drawn per case, the
unblinding map sealed in `judging-key-DO-NOT-OPEN.json`, scoring via
`--score` into `judging-verdict.json`. Blindness is tested
(`tests/test_compare_judging.py`): the queue carries no model names, no
channel scores, no stability markers. Structural caveat, recorded: this
entry itself describes aggregate tendencies, so an owner-judge is not
fully blind to style; the per-case side shuffle still holds, and the real
user is a fully blind judge if tone needs one.

**Reopen if:** the human pass judges most flagged cases `egal` (then the
selection measured decoy resolution, not behaviour difference, and the
pair needs a calibration look before any verdict), or the §4
generalisations ship and the two pending Design R quantities get computed
from this store.
