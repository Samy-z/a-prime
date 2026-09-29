# Domain cells — current state

`src/aprime/cells/`. Nine systems under test: 3 domains x 3 output formats.
Maintainer doc, not linked from the README (D20).

## Structure

| File | Holds |
|---|---|
| `packs.py` | knowledge packs — data only, generated deterministically from a seed |
| `tools.py` | the eight tool shapes, instantiated per domain, plus fault hooks |
| `cell.py` | `Cell` (a `SystemUnderTest`) and `build_inputs` |

## Packs are data, not behaviour

Tool results are therefore **ground truth**: nothing about a tool's answer
depends on a model, so an injected retrieval fault has a knowable correct answer
and a knowable observed answer. That is what per-input activation needs.

Structure is identical across the three domains — same record shapes, same
policy shapes, same history shapes, differing only in vocabulary. Asserted by
`test_every_domain_builds_and_has_the_same_structure`. Without that, a
detector difference between banking and logistics could be a pack difference
wearing a domain label.

Referential integrity is enforced: every entity points at a real principal, so
`build_inputs` can only produce answerable requests. A corpus of requests about
records that do not exist would measure error handling instead of detection.

## Eight tools, one topology

Shapes: `lookup`, `search`, `policy`, `compute`, `evaluate`, `history`,
`verify`, `act`. Names differ per domain (`get_account` / `get_shipment` /
`get_booking`); parameter and return structure do not.

Measured before committing (BCH-013): all three 8B models selected correctly
16/16 among these eight, and the schemas cost 461-751 prompt tokens, not the
1200-2000 assumed. Eight tools cost nothing in reliability and settle the D11
sizing question.

**Tolerant argument matching.** `_arg()` accepts `account_id`, `accountid`, `id`.
Being strict would measure the model's naming habits rather than the detector.

**Tools never raise.** A malformed call returns `{"error": ...}` plus, where
useful, the available options — a real tool answers rather than crashing the
agent, and models do get argument names wrong.

### Fault hooks

- `disabled={shape}` withdraws a tool. Fault class **F3**, an upstream tool
  renamed or removed while the agent still expects it.
- `stale={shape}` answers from a shifted view: same length, same keys, older
  content. Fault classes **F5** and **F11**. Deliberately structure-preserving,
  because staleness that broke the JSON would be caught for free by structural
  conformance, which is not what these faults look like in the wild.

Both were listed as "not implemented" in BCH-011 for want of a system that
retrieves. They are now implementable in all nine cells.

## Cells

All three formats call tools and differ in required output:

| mode | output | shape inferred as |
|---|---|---|
| `extraction` | one JSON object, four named keys | `json` |
| `summary` | 3-5 sentences of prose | `prose` or `short` |
| `agent` | one decision line, APPROVE / DECLINE / ESCALATE | `short` |

An earlier sketch gave tools only to `agent`, which would have confined F5 and
F11 to three of nine cells. Real extraction and summarisation agents retrieve
before they write.

`identity_aware=True` puts the requester in the system prompt. This is the
**control** for F8b: an identity-aware system produces per-user clustering with
no fault present, which is what distinguishes a sticky routing fault from
ordinary personalisation (BCH-006). Two cells carry it, per D2.

Exhausting `max_steps` returns a real Response with `exhausted_steps` and
`empty_output` set, rather than raising. A deployment returns *something* to its
user, so the recorder should see what that something was.

## A recurring defect worth naming

Three times now a hand-written test double has diverged from the real API:

1. the fake transport invented a `sha256:` digest prefix a live server does not use
2. a check conflated an errored response with an empty one
3. the fake assistant message omitted `"role"`, which a real response includes

Each was caught only by running against reality. The third also revealed a real
robustness gap — the cell now sets `role: "assistant"` explicitly rather than
appending the model's message verbatim.

**The process fix is to build fakes from captured real responses** rather than
from memory of the API. Not yet done; it needs one live capture per shape stored
as a fixture.

## Not yet done

- **Never run against a live model.** Every test uses a scripted chat function.
- No cell has been recorded through the detector end to end.
- Per-cell peak token demand unmeasured, which D11 puts before fixing the
  context cap. The 461-751 schema floor is known; the conversation above it is not.
- `build_inputs` covers the eight shapes plus one mixed template. No multi-turn
  inputs, so chained tool use is only exercised when a model chooses to chain.
