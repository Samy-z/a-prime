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

## Two mechanisms: rewriting an output, and degrading what is known

`faults.py` rewrites an output after the fact. `cells/retrieval_faults.py`
changes what the system retrieves and lets the model write a different answer
itself. Both are needed and they are not interchangeable.

| | `FaultInjector` | `RetrievalFault` |
|---|---|---|
| changes | the output text | what the tools return |
| works on | any system under test | cells only |
| fingerprints | ours, in wording we chose | the model's own |
| classes | F4, F7, F10, F12, F14 | F3, F5 |

The distinction matters for validity. An output we rewrote carries our
vocabulary and sentence shape, so a channel could in principle learn to spot
*us* rather than the fault. An output the model wrote from degraded inputs
carries only its own, which is what a real regression looks like.

**Both record activation through the same `ActivationLog`**, per
`(input_id, sample_idx)`, and both share `_in_blast` rather than reimplementing
it. Two notions of activation, or two implementations of blast radius, would
diverge and make per-class and per-regime results incomparable across the two
mechanisms. A first version of the retrieval wrapper logged per input only,
which silently collapses the request-level and per-principal rates into one
number, and telling those apart is the only reason regimes B2 and B3 exist.

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
- F11, retrieval degradation returning the wrong rows rather than old ones, is
  still not implemented. `_shift` serves older content of the same shape, which
  is staleness; returning unrelated rows is a different fault and needs its own
  handler.
- No prompt-regression injection (F2): it needs a system with a prompt to edit.
- `tool_withdrawn` has never been run against a live model, only unit-tested.
  Its activation depends on baseline tool usage, and how often an 8B model
  reaches for a specific shape is not yet measured per input.
- `B1` is modelled by which arm you wrap rather than by a platform attribute,
  which is honest but means the harness cannot express a fault that hits two
  platforms at different rates.
