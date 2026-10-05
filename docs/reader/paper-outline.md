# Paper outline — *Does label-free regression detection transfer across domains?*

Reader-seat planning document, written 2026-10-04. Its reader is the owner and
whoever drafts the paper, so identifiers are used freely here; **none of them
may appear in the paper as a load-bearing reference** (reader METHODS, rule 2).

## What this document is for

Every claim the paper will make is listed under its section with what backs
it: a ledger entry, a figure, a results file, or `GAP` with what fills it.
Three grades, carried into the draft as a discipline rather than as labels:

| grade | meaning | how the paper may state it |
|---|---|---|
| **measured** | a number from a run with a run id | as a result, with denominator and interval |
| **constructed** | built and tested, not measured on a real system | as a mechanism, never as a result (the STD-001 register) |
| **asserted** | from the literature or from reasoning | with its source, never as our finding |

Nothing in the draft may be stated above its grade. The banned phrasings in
`docs/study/METHODS.md` apply from the first sentence.

## The reader, and what that costs

D19 (HANDOFF §16): somebody who ships LLM systems and might use the tool.
Software literacy assumed; everything else defined, the statistics included.
D24 (HANDOFF §17): the README becomes a front door once this exists, and the
honest-limits headlines stay there regardless.

**Terms the paper must define on first use**, in the order the outline reaches
them: regression (a change in behaviour, not a drop in a score we cannot
compute), label-free, black-box, baseline and candidate, sample and cloud,
decoy, false discovery rate, the false-alarm budget `q`, mode, entailment,
contradiction, normalisation, stratum, induced rule, blast radius, fault
class, activation, severity, leave-one-system-out, run id and config hash.

A term defined in the README is still undefined in the paper (rule 1). Each
definition is one or two sentences in the place it is first needed, not a
glossary; the prose checker's jargon list should be extended with any new term
the draft introduces (reader STATE, known gaps).

## What moves from the README and what stays (D24)

| moves to the paper | stays in the README |
|---|---|
| prior art in full (§2) | the problem, in one screen |
| the findings in detail with their numbers (§4, §5, §8) | the core idea in one paragraph and the diagram |
| the two reusable ideas (§10) | the worked example, kept current with program output |
| anything that argues | how to run it; repository layout; licence |
| the full honest-limits section with the numbers behind each (§9) | **the honest-limits headlines**, never removed |

The README change happens when the draft exists, not before.

---

## §0 Abstract

Written last. Must contain, in this order: the question (STD-005), the method
in one sentence (run the baseline twice; the second run calibrates everything),
the headline transfer number with its interval (`GAP`: the factorial), the
largest honest limit (the tool cannot report fewer than 1/q changed inputs),
and one sentence on what the figures describe (one judging model, MTH-017).

## §1 The problem: you swapped the model, and nothing you have can tell you what broke

Claims, all **asserted** from the literature unless marked:

- Unit tests test the code, not the model's judgement. Teams have no labels
  for their own domain. The new model rewords everything, so differences are
  everywhere and the question is which ones matter. (README §1; the argument,
  not a finding.)
- Across 118 published incidents from the two largest providers, none
  describes a quality drop; regressions ran four days to ten months before
  anyone noticed; none in the written-up cases was caught by the operator's
  own tests. (`.agents/bench-taxonomy-research.md`, committed as the evidence
  under BCH-004; the counts must be re-derived from that document before the
  draft quotes them.)
- The incident record also sets the shape of real regressions: prompt edits
  are one to three lines (BCH-004); three unrelated serving-stack faults share
  one output signature (BCH-005); a sticky routing fault touched 30% of users
  at 0.8 to 16% of requests (BCH-006, BCH-001). This is where the paper earns
  the right to inject faults later.

Defines: regression, label-free, black-box.

## §2 What already exists, and where the gap is

All **asserted**, from the landscape survey, with the verification note
honoured: no hard novelty claim against a named tool reaches the draft until
that tool has been run, not read (study LEDGER, note after STD-007).

- The statistics of repeated sampling and paired error bars are canonical;
  Inspect ships them. Not a contribution (STD-001).
- Metamorphic testing is solved academically and shipped by Giskard. Cite,
  use, do not claim (STD-002).
- Embedding triage is half-occupied by Phoenix (STD-004).
- Clausius is the nearest competitor and got to the slogan first: label-free,
  measured null, five model families, seven domains. It reads logprobs, so it
  cannot be pointed at a hosted API, and its own documentation says its null
  must be re-measured per stack (STD-006). a-prime is black-box. Position
  against it explicitly; the space is not empty.
- Two things appear unoccupied: inducing structural rules from a baseline's
  own output, Daikon's idea never ported to LLM output (STD-003), and a
  repeated baseline run as a general calibration for a black-box comparison,
  target-decoy FDR having no prior LLM-evaluation use found (STD-001).
- Nobody has published whether such detection transfers across domains
  (STD-005). That is the question. The paper is a study with a tool attached,
  not the reverse.

## §3 The idea: run the baseline twice

The method section. Mostly **constructed**, with one **measured** validation.

- Three arms: baseline, baseline again, candidate. The second baseline run is
  a comparison where nothing changed by construction; its differences are the
  null (README §2; engine METHODS, "three arms always").
- Define false discovery rate: of everything flagged, the share expected to
  be wrong. Define the budget `q`. Explain target-decoy selection in plain
  words: lower the bar until the decoys that clear it, plus one, would exceed
  `q` of the targets that clear it. The `+1` is the conservative correction
  and it is not optional (MTH-024).
- Why not the textbook correction (Benjamini-Hochberg): its guarantee needs an
  assumption about dependence between inputs that production corpora, full of
  near-duplicates, do not honour; the decoys are subject to the same
  dependence, so they need no model of it (MTH-007). State without the
  acronyms.
- **The floor, stated here and again in §9:** with the `+1`, nothing can be
  reported until 1/q inputs clear the bar, ten at the default budget. An
  empty report means fewer than ten changed, not none (MTH-024). The
  arithmetic, not a tuning choice.
- Sizing: `n >= (1/q) / (a*s)`, with `s` set by how fine the statistic is,
  which is set by samples per arm (MTH-024 correction, ENG-007). Define `a`
  and `s` in words.
- Samples per arm: twenty, not ten. Ten detects 8% of a moderate shift, twenty
  73% (MTH-018). Sixty calls per input across three arms.
- The seed: the arms mirror the deployment's seed policy; a pinned seed on
  both baseline arms collapses the null onto two points and the tool should
  refuse (MTH-023 and correction; ENG-006 for why it only warns). Explain
  why "reproducible" does not mean "identical seeds".
- Per-shape thresholds: the 5% false-alarm cut varied by a factor of eighty
  across four output shapes, so one threshold is wrong for at least two of
  them (MTH-013). Define stratum. Note honestly that every run so far pooled
  into one stratum (engine STATE, "not built").
- **Measured:** on a synthetic system with known ground truth, asking for 10%
  false alarms gave 10.1% or less across nine cells (MTH-018), and 3.4% with
  28 of 30 changed inputs caught on the demo (`scripts/demo_detect.py`,
  `docs/knowledge/detector.md`). Say what "synthetic" means and why it is the
  only place this can be checked at all.
- No check votes; findings are per check, because weights would have to be
  fitted outside a fold (MTH-009; detect.py docstring). One paragraph.

Figure: the three-arm diagram from the README, redrawn. Table: the sizing
formula with the ENG-007 numbers as the worked case.

## §4 What each check sees, and what it misses

The blind-spot map section. **Measured** on the probe suite; the suite's own
construction gets a paragraph because a broken pair and a blind check print
the same number (`probes.md`, "why the pairs have their own tests").

- How the suite is built: 896 template-generated pairs, three relations
  (preserving, breaking, register), eight kinds of fact change, four shapes,
  four subject areas; why the asymmetry between preserving and breaking is
  deliberate (`probes.md`). Register as a third class and why (MTH-021).
- Define entailment and contradiction. The judging model reads two texts
  together; this is more expensive than embedding each alone (ENG-003 cost,
  `mode-clustering.md`).
- **Figure 1: the blind-spot map** (`docs/figures/blind_spot_map.svg`,
  STD-009 and amendment). Grid of three judging models on one raw pair set;
  the shipped configuration below it; the floors under the grid.
- Findings, each with its entry: embeddings perform below chance and the
  mechanism is twenty-to-one (MTH-011); recovers only when wording is stable,
  hence the gate (MTH-012; gate threshold unfitted, engine STATE); contradiction
  carries seven of eight (MTH-013); omission is invisible to contradiction and
  visible to the signed entailment read at the upper tail (MTH-014 corrected,
  MTH-016); the lower tail catches added content and both register directions,
  and the sign names the fault (MTH-022); normalisation buys detection and not
  fewer false alarms (MTH-019); reformatting is the shared false-alarm source
  (probes Finding 5).
- **The figures describe a model, not a method:** a second judging model
  reproduced every direction and no magnitude, with gaps to 48 points
  (MTH-017). This belongs in §4, §9 and the abstract.
- Numbers quoted in this section follow the map's rule; the reconciliation
  with earlier entries is Appendix A (MTH-017 reconciliation append).

## §5 Rules the baseline teaches about itself

The induced-conformance section. **Constructed**, with two **measured** notes.

- Daikon, named properly: a 2001 tool that watched programs run and guessed
  the rules their variables obeyed; its known weakness is over-generation
  (STD-003; README §"two ideas").
- The three-tier band: rules that hold on both baseline runs are enforced;
  rules that hold most of the time are shown to a person as a question; the
  rest discarded. The second baseline run is what prunes coincidence (engine
  METHODS, `conformance.md`).
- **Measured:** on the semantic titration, corrupted characters and raw
  escapes were caught by the structural rules at every severity and by no
  meaning check at any, because a meaning check correctly judges a corrupted
  output as meaning the same thing (ENG-004). Rules are the only cover for a
  whole fault class.
- Rules describe the system, not an input, so they are not subject to the
  1/q floor; on the first real run they were the only part of the report that
  could say anything (ENG-007).
- Honest notes: the decoy prune has not yet been exercised by a realistic
  system because the stub produced no coincidental rule to prune (ENG-005 and
  correction); a tight induced rule can be tipped by an ordinary draw
  (ENG-009, one draw, not a rate).

## §6 Systems under test, and the faults

The bench section. Mostly **constructed**, with the live-run measurements
marked.

- Nine cells: three domains by three output formats, eight tools each,
  identical topology, differing only in vocabulary, so a domain difference
  cannot be a pack difference (`cells.md`; BCH-013 for the tool-selection
  measurement, 16 of 16, and schema cost).
- The fault taxonomy, frozen before any tuning: fourteen classes, nine with
  incident evidence (BCH-003); blast radius as its own axis (BCH-001); two
  severity floors from published evidence, not ours (BCH-004); decoding
  parameters dropped for lack of any documented instance (BCH-002).
- Define activation: a fault labelled at the cell level is wrong for every
  input it never touched; ground truth is per input and per sample (BCH-011,
  `faults.md`).
- The three injection mechanisms and why two of them let the model write the
  faulty output itself (`faults.md`; BCH-016 for F2 and its exposure-based
  activation, ratified; BCH-017 for F11 and the 10% floor).
- Seat separation and what git proves: every detector threshold was committed
  before the harness existed (BCH-011; HANDOFF §2).
- **Measured, live:** the cells run against an 8B model; the first live run
  found four bench defects, three silent (BCH-014); the agent format is a
  distinct shape and 4 of 12 compliant, kept deliberately (BCH-015, HANDOFF
  §13); two models on disk silently inject fault classes the study measures,
  which is why every system under test gets an explicit system message and
  explicit sampling parameters (BCH-009).
- The model pool and why family diversity, not capability, chose it (BCH-007).

## §7 Study design

**Constructed**; nothing here has run. Written so a reader can judge the
design before the result exists.

- The question, as the largest defensible claim shape (study METHODS): under
  leave-one-system-out, across N systems spanning named task types and
  domains, the detector flagged changed inputs at budget `q` and detected
  injected faults down to severity `s` per class; performance on unseen
  systems expected within the stated interval.
- Define leave-one-system-out and why random splits are invalid: a classifier
  learns system identity as a fault signature (MTH-009). Report random-split
  numbers beside LOSO, never instead (study METHODS).
- Systems, not inputs, are the unit, and the interval is wide: a lower bound
  of 0.54 on the per-system success rate at six systems, 0.66 at nine, even
  with every system succeeding (MTH-008). Say this before any number.
- Base rates can manufacture a transfer result; they are controlled across
  cells by design (STD-007).
- Pre-registration, sealed holdout, no threshold outside a fold, pinned
  instruments, provenance (methods METHODS, the rails). The holdout of 30 to
  80 real regressions can detect catastrophic non-transfer and nothing finer
  (MTH-010); it is not collected yet (methods STATE).
- Provenance: every number traces to a run id and a config hash; what is
  hashed and what is only recorded, and why the host is not hashed
  (`provenance.md`).
- The development system is reported separately and never pooled (HANDOFF
  §3, study METHODS).
- Recording is the binding constraint: 589 s recording against 10 s detection
  on the first end-to-end run; runs are pausable (HANDOFF §14).

## §8 Results

**Drafted 2026-10-05 against two of three rows (STD-010); the agent row and
the extraction diagnosis are bracketed.** The LOSO/LOFO comparison and the
severity titration per fault type remain downstream of the full factorial. The section is written now as a table of what each
result will be backed by, so that the draft cannot quietly promote a
constructed mechanism to a measured result when the numbers arrive.

| result | status | backing when it exists |
|---|---|---|
| transfer matrix, 3 domains x 3 formats | **partial**: summary and extraction rows measured (STD-010); agent row recording | `results/study/matrix.json`, per-row provenance (75081ad) |
| random / LOSO / LOFO / LOSO x LOFO side by side | `GAP`; LOFO undefined with one fault class (STD-010) | same |
| severity titration per fault class, semantic path | partial: six faults on the stub (ENG-004) | the factorial, per class |
| FDR control on ground truth | **measured**: 0.101 or below against 0.10 (MTH-018) | `tests/test_pipeline.py` sweep |
| one real cell, end to end | **measured**: three checks separated the fault with zero decoys above the cut; nine inputs cleared against a floor of ten; nothing reported (ENG-007) | `results/cell_detection_20260929T231931Z.json` |
| exact-match titration | not a result: a saturated instrument (ENG-002) | cited only to say so |

ENG-007 is reported in full as the worked case of the floor: a clean
separation the estimator could not report, and what the report now says about
it (HANDOFF §19).

## §9 Honest limits

The section with the clearest use to the reader, so it is written for them
(D19). Headlines stay in the README; the paper carries each with its number.

1. **Cannot report fewer than 1/q changed inputs.** Ten at the default. An
   empty report is not "nothing changed" (MTH-024). The README headline.
2. **Twenty samples per arm is the real minimum.** 8% against 73% (MTH-018).
   README headline.
3. **The figures describe our instruments, not the technique.** One judging
   model; a second reproduced directions and no magnitudes, gaps to 48 points
   (MTH-017). README headline.
4. **Nothing has run against a production system.** Every figure is from a
   synthetic system or hand-built pairs, plus one real cell at ENG-007 that
   fell under the floor. README headline.
5. Small shifts are invisible and the floor is roughly known: a 0.3 shift in
   answer mix, undetected at every sample size tested; below about 0.5 the
   statistic has nothing to say (MTH-018). On the map.
6. A short hedge inside a long output is near-invisible to every meaning
   check (ENG-004, dilution). On the map.
7. Corrupted characters are invisible to every meaning check and visible only
   to the structural rules (ENG-004). On the map.
8. Duplicates are removed only on wording; semantic near-duplicates are a
   known gap and they make the guarantee slightly optimistic (README; engine
   STATE).
9. One threshold set by judgement: the embedding gate (engine STATE).
10. Direction cannot be recovered: the detector cannot say whether a change
    is a regression or an improvement, and the signed entailment check
    measures more-versus-less information, not better-versus-worse (MTH-001
    and correction).
11. Transfer across *judging models* degrades measurably and the study is not
    designed to answer it (MTH-017). Say so rather than let a reader assume.
12. The agent format's outputs vary 36-fold in length where summaries vary
    3-fold; a per-shape threshold has little to hold on to (BCH-015).
13. F2 activation is exposure for five edits of six, so recall on prompt
    regressions is a lower bound (BCH-016). F11's wrong rows always come from
    the same domain (BCH-017).
14. The rules' decoy prune has not been exercised on a realistic system
    (ENG-005); a tight rule can be tipped by a draw (ENG-009).
15. The pooled stratum: every run so far had fewer than thirty inputs per
    output shape, so the per-shape machinery is tested and never stressed
    (engine STATE, MTH-024).
16. Everything is English and template-generated (`probes.md` limits).

## §10 Two ideas that may be useful elsewhere

Moves here from the README under D24. Both **constructed**, stated as
mechanisms.

- The second baseline run does a second job: it filters induced rules. A
  rule that holds on one run of a system and breaks on another run of the
  same system was never a rule (§5; engine METHODS).
- One number, read at both ends, names two faults: the signed entailment
  asymmetry, positive for content removed, negative for content added; the
  first implementation took the absolute value and threw away the only part
  that identified the fault (MTH-022; HANDOFF §5).
- A third candidate, if the draft has room: the floor is a feature. A tool
  that cannot report one finding is a tool that cannot be made to find
  something by lowering its bar (MTH-024; detector.md on the `inf` threshold).

## §11 Extensions, one honest sentence each

In the STD-001 register: constructed or derived, not measured.

- The same statistic pointed at time detects provider drift; the negative
  control is about an hour of GPU and is not yet run (STD-008 and append).
- A hosted model as a system under test is one adapter behind the existing
  boundary, deferred on cost (HANDOFF §15 and amendments).
- Distilling the judging model: the cost line is now honest about the
  predicate's share (ENG-003 fixed) and is the evidence for or against it
  (HANDOFF §4).

## §12 Reproducibility

- The pinned instrument table with revisions and dates (methods STATE).
- Commands (CLAUDE.md), the dependency manifest and its torch note
  (`requirements.txt`), what travels with the repository and what does not
  (`environment.md`).
- Data and licence: code Apache 2.0, documentation and results CC BY 4.0
  (README, NOTICE).
- Every figure names its run ids; derived artifacts name their sources
  (`provenance.md`).

## Appendices

- **A. Reconciliation of published numbers with the map's rule** (MTH-017
  reconciliation append): every moved cell as counts of 64, with the reason.
- **B. The fault taxonomy** as frozen, with the amendment log
  (`fault-taxonomy.md`).
- **C. How the probe pairs are built and verified**, including the four
  construction bugs the pair tests found (`probes.md`).
- **D. A report, annotated**: the ENG-007 run through the current report
  format, each line explained (`detector.md`, "Reading the report").
- **E. What the knowledge index and STATE checks guard** (RDR-008): one
  paragraph, because a reader deciding whether to trust the repository's
  self-description should know it is tested.

---

## Figures and tables, with status

| | status |
|---|---|
| Fig 1, blind-spot map | **done**, `docs/figures/blind_spot_map.svg` |
| Fig 2, three-arm diagram | README ASCII; redraw for print |
| Fig 3, transfer matrix | `GAP`, factorial |
| Fig 4, random / LOSO / LOFO side by side | `GAP`, factorial |
| Fig 5, severity titration curves per fault class | partial (ENG-004 on the stub) |
| Table 1, sizing worked example | from ENG-007 and MTH-024 |
| Table 2, pinned instruments | methods STATE |
| Table 3, fault classes and injection mechanisms | `faults.md`, BCH-003 |
| Table 4, results backing | §8 above |

## What the outline cannot settle

- Whether the headline is the transfer result or STD-003, which depends on
  what the factorial shows (study STATE, contribution ordering).
- Length. A paper that defines its statistics is longer; the cost was
  accepted at D19. The draft should be written in full and cut from the
  appendices first.
- Whether the incident counts in §1 survive re-derivation from the committed
  research document. They were written for the README from that document
  and have not been re-counted since.
