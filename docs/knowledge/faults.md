# Fault injection — current state

`src/aprime/faults.py`. Breaks a working system in known ways so the detector
can be scored against ground truth.

Every injection corresponds to a class in the frozen taxonomy. Nothing is
invented, because the taxonomy's entire validity argument is that it is drawn
from documented reality — and an invented fault would quietly undo that.

## Per-input activation is the ground truth, never the cell label

A fault labelled at the cell level is **wrong for every input it never
touched**. Truncation cannot truncate four words. A schema break only bites
JSON. A refusal only bites where the system would otherwise have answered.
Labelling all of a cell's inputs positive is label noise by construction, and
it is the kind that inflates every downstream number in the direction that looks
like success.

`ActivationLog` records, per input and per sample, whether the fault actually
fired. **That is what the detector is graded against.** There is a test
asserting a fault which found nothing to bite records no activation, and an
end-to-end test asserting the detector is scored against activation rather than
against the cell.

## Blast radius is an axis (BCH-001)

| Regime | Who is affected | Injection |
|---|---|---|
| `B0` | everyone | shared artifact — one prompt, one model version |
| `B1` | one platform surface | wrap one deployment, leave the other alone |
| `B2` | uniform random share of requests | hash on input id |
| `B3` | sticky share of **principals** | hash on principal, so the user-level rate exceeds the request-level rate |

B3 raises an error when an invocation has no principal, rather than falling back
silently. Without a principal the request-level and user-level rates cannot come
apart, which is the only reason B3 exists.

## Available injections

| Name | Class | Bites | Signature |
|---|---|---|---|
| `omission` | F5/F3 | outputs with ≥2 sentences | trailing content dropped |
| `output_truncation` | F12 | outputs ≥8 words | mid-sentence stop, `finish_reason: length` |
| `script_corruption` | F7 | any non-empty | wrong-script characters mid-output |
| `unicode_escape` | F7 | any non-empty | raw `\uXXXX` instead of glyphs |
| `refusal` | F13 | any non-empty | answer replaced entirely |
| `schema_break` | F3 | JSON objects only | key dropped, or unparseable above severity 0.75 |
| `verbosity` | F9 | any non-empty | stance added, no fact changed |

## The injector wraps, it does not reconfigure

`FaultInjector` wraps a system and alters what comes back. The wrapped system is
untouched, so the same baseline object can serve the A and A_prime arms while
only B is wrapped. Reconfiguring the system instead would mean the fault lived
in the system's own state, and the decoy arm would inherit it.

## Three mechanisms: rewriting an output, degrading what is known, editing the instructions

`faults.py` rewrites an output after the fact. `cells/retrieval_faults.py`
changes what the system retrieves and lets the model write a different answer
itself. `cells/prompt_faults.py` edits the system prompt the cell sends, and
likewise lets the model write. All three are needed and they are not
interchangeable.

| | `FaultInjector` | `RetrievalFault` | `PromptFault` |
|---|---|---|---|
| changes | the output text | what the tools return | the instruction lines |
| works on | any system under test | cells only | cells only |
| fingerprints | ours, in wording we chose | the model's own | the model's own |
| classes | F4, F7, F10, F12, F14 | F3, F5, F11 | F2 |

The distinction matters for validity. An output we rewrote carries our
vocabulary and sentence shape, so a channel could in principle learn to spot
*us* rather than the fault. An output the model wrote from degraded inputs
carries only its own, which is what a real regression looks like.

**All three record activation through the same `ActivationLog`**, per
`(input_id, sample_idx)`, persist it through the same `load_from` and
`persist_to`, and share `_in_blast` rather than reimplementing it. Two notions
of activation, or two implementations of blast radius, would diverge and make
per-class and per-regime results incomparable across mechanisms. A first
version of the retrieval wrapper logged per input only, which silently
collapses the request-level and per-principal rates into one number, and
telling those apart is the only reason regimes B2 and B3 exist.

### Prompt regression: the ladder is frozen and small, and activation is exposure

F2's severity ladder in the taxonomy is anchored on measured production diffs:
rung 1 is one line added or removed, rung 2 is two added and three removed,
rung 3 (nine added, twenty-three removed) is a post-incident cleanup kept as
the ceiling. `PROMPT_EDITS` holds six edits, each shaped after a documented
incident and declaring its lines added and removed; a parametrised test
measures the real diff on every format with and without identity and refuses
an edit that outgrows its rung. `FaultSpec.severity` is the rung over three.

| edit | rung | lines | shaped after |
|---|---|---|---|
| `injected_instruction` | 1 | +1 | Grok 2025-05-14: an unreviewed, irrelevant instruction |
| `format_rule_dropped` | 1 | −1 | the most common production diff size |
| `format_rule_swapped` | 1 | +1 −1 | Grok 2025-07-08: old text served by the wrong code path |
| `identity_dropped` | 1 | −1 | a deletion with purchase only where a requester was named |
| `resurrected_instructions` | 2 | +2 | Grok 2025-07-08: deprecated instructions reactivated |
| `rewrite` | 3 | +9 −2 | `grok-prompts` e517db8, the remediation; the ceiling |

A cell's prompt is two or three lines, so "line" means one of those, the same
unit the production diffs count. `Cell.prompt_lines()` builds the prompt as
lines and the joined text is byte-identical to before, asserted by a test.

The taxonomy says F2 activation is partial even under B0: an instruction fires
only where it has purchase. Purchase, whether the instruction changed what the
model wrote, is what the detector is being asked to find and cannot be ground
truth without a second clean invocation per input at double the recording
cost. So activation is **in blast, and the prompt actually changed for this
invocation, and the model answered, and the edit's purchase predicate where it
has one**. Only `identity_dropped` has one. For the rest activation is
exposure, which errs towards understating the detector and is recorded as such
(BCH-016).

### Not every fault can be graded from inside the candidate arm

`stale_view` can: the tool is called, so the clean and faulty answers can be
compared on the spot.

`tool_withdrawn` cannot. A withdrawn tool is absent from the advertised schemas,
so the model never asks for it and there is no call to compare. What changed is
what the system *would* have done, which is visible only from the baseline arm.
So it requires the baseline's tool usage, collected by wrapping the clean arm in
`UsageRecorder`, and **refuses to construct without it**. Logging activation as
false everywhere would report a fault that fired on nothing, and a run in that
state looks successful while measuring nothing.

`UsageRecorder` exists because `ToolSet.calls` is a flat log with no input id on
each entry, so usage cannot be attributed after the fact. Pooling shapes across
the corpus would mark every input as affected and inflate the apparent activation
rate to 1.0.

### Degraded retrieval returns the wrong rows, and that is a different fault from stale

`degraded_retrieval` (F11) makes a `noise` fraction of what a read returns
belong to another record: a different entity under a lookup, somebody else's
events in a search, another principal's figures under an evaluation, another
topic's policy. The rows are well-formed and carry the right keys, so the
structural checks do not catch them for free. `stale_view` (F5) serves older
rows of the right record. A stale index is behind; a degraded one is confused;
the two disagree with each other and with the clean read on the same call, and
a test asserts it.

Severity is `noise`, on the published ladder `F11_LADDER = (0.10, 0.20, 0.30)`
from the controlled study the taxonomy cites. **At 0.10 that study measured no
downstream change at all**, so a miss at that rung is not a detector failure and
is not scored as one (BCH-004). Here the floor shows up as true negatives: at
10% noise most reads come back unchanged, and activation records them as
unaffected.

Degradation is seeded on the call (seed, shape, canonical arguments), so a
replay of the same call on an identically built toolset returns the same wrong
rows. That is what lets the clean-versus-faulty comparison that decides
activation see exactly what the cell saw. `compute` and `act` do not read, so
listing them as degraded changes nothing and fires on nothing.

### A stale knowledge base is stale for every read

Staling one tool shape and calling it a stale knowledge base overstates how
localised the fault is, and it depresses activation sharply: one shape fired on
2 of 12 inputs where the four readable shapes fired on 15 of 30 (BCH-014,
ENG-007). The broad version is both the more realistic reading of F5 and the only
one with enough activation to be gradable.

### Check activation before spending the GPU, not after

`check_activation_is_usable` warns when a fault fired on fewer inputs than the
estimator can report at all. The FDR estimate cannot go below `1/q`, so a fault
firing on fewer than that many inputs cannot be detected however good the
detector is, and an empty report carries no information (MTH-024). Two
end-to-end runs were spent learning this at roughly 25 minutes each.

## Severity floors come from published evidence (BCH-004)

Retrieval corruption at 10% produced identical metrics to 0% on n=500. If the
harness injects that and the detector misses it, **that is not a detector
failure** and must not be scored as one. Real production prompt edits are one to
three lines; a harness that rewrites whole prompts injects something that does
not occur in the wild.

## Seat separation, and what git proves

Building both the detector and the harness in one session is a contamination
risk: the seat that tunes the detector must not know where the faults are seeded
(HANDOFF §2). The auditable guarantee here is **commit order**. Every detector
threshold — the clustering threshold (MTH-020), the channel inventory
(MTH-013/016/022), the FDR machinery (MTH-018) — was fitted and committed
*before* this module existed, against the probe suite and the stub, neither of
which contains an injected fault. The git history is the evidence, and it is
checkable rather than promised.

## Known limits

- **F5 is implemented for cells** as `stale_view`, and F3 as `tool_withdrawn`.
  Neither works on a system we did not build, because both need the tool layer.
- F11 is built for cells and has never been run against a live model. Its
  rows are drawn from the same pack, so a wrong row is always a plausible
  record of the same domain; a retriever that returns rows from another
  domain entirely is not modelled.
- F2 is built for cells and has never been run against a live model. Its
  activation is exposure for five of six edits; whether a given instruction
  had purchase on a given input is measured by the detector, not known by the
  harness, so recall on F2 is a lower bound.
- `tool_withdrawn` has never been run against a live model, only unit-tested.
  Its activation depends on baseline tool usage, and how often an 8B model
  reaches for a specific shape is not yet measured per input.
- `B1` is modelled by which arm you wrap rather than by a platform attribute,
  which is honest but means the harness cannot express a fault that hits two
  platforms at different rates.
