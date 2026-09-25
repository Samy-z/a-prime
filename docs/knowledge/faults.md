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

- Retrieval and knowledge-base faults (F5, F11) are not implemented. They need a
  system that retrieves, which is the Palworld adapter's job.
- No prompt-regression injection (F2), for the same reason: it needs a system
  with a prompt to edit.
- `B1` is modelled by which arm you wrap rather than by a platform attribute,
  which is honest but means the harness cannot express a fault that hits two
  platforms at different rates.
