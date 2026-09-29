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

### The request corpus is phrased per mode

`build_inputs(pack, ..., mode=...)` wording follows the mode. Only `agent`
differs from the plain corpus: a question is what an extraction or
summarisation consumer actually sends, but a decision line answers a decision
request and nothing else. Demanding APPROVE / DECLINE / ESCALATE in reply to
"what is the status of AC-4000?" is an incoherent instruction, and the model
correctly ignored it (BCH-015).

The two corpora line up record for record — same ids, same tool shape, same
position — so nothing about the comparison moves except the framing. Passing
`mode` also stamps it into the input id, because the recorder groups by input id
and two different request texts under one id would pair unlike requests across
arms.

### Exhausting the step budget

Exhausting `max_steps` withdraws the tools and demands one final answer, then
returns that with `exhausted_steps` set. Returning nothing, which is what it did
before, cost a quarter of every corpus on the first live run: the model hunted
for a figure it could not reach, ran out of steps and the cell yielded `""`
(BCH-014). A deployment answers with what it has. `empty_output` is still set if
the forced answer is blank too, so the study can exclude these rather than
silently score blanks.

### Leaked reasoning blocks

`granite4.2:8b` sometimes writes its working into `content` and closes it with
`</think>`, with no opening tag, even though `think` is off. Everything up to
that tag is deliberation, not output; the cell strips it and sets `think_leak`.
Left in, the detector would be scoring the model thinking aloud as though it
were the answer.

## Agent mode is distinct but not compliant

Measured live, `granite4.2:8b`, 12 invocations per mode (BCH-015):

| | extraction | summary | agent |
|---|---|---|---|
| obeys its own format rule | 12/12 | 12/12 | **4/12** |
| parses as JSON | 12/12 | 0/12 | 0/12 |
| contains a decision token | 0/12 | 0/12 | **10/12** |
| median words | 31.5 | 51.5 | 32.5 |
| spread, words | 13-52 | 30-104 | **11-396** |

Read the third row before the first. The grid needs the three formats to be
three different shapes, because the detector fits a threshold per shape, and
that is a different question from whether each obeys its own instruction. The
decision token separates agent from summary completely. **The third arm is
real.**

What agent mode does wrong is put the decision last. It reasons in a paragraph
and appends the verdict; the rule asks for the verdict first. Three rounds of
fixes moved compliance 1 to 3 to 4 out of 12, the last round buying one input
for roughly 40% more GPU time, at which point further fixing becomes tuning the
bench until the number looks right.

The spread is the real problem, and it is not the one the compliance count
points at. Agent outputs vary by a factor of 36 where summary varies by 3. A
shape-stratified threshold has little to hold on to there.

**Agent mode costs 3.5x what summary costs** — 202 seconds against 57 for the
same 12 invocations, 51 tool calls against 19. At full corpus size that is the
dominant term in the GPU budget, and it is not yet costed.

## A recurring defect worth naming

Three times now a hand-written test double has diverged from the real API:

1. the fake transport invented a `sha256:` digest prefix a live server does not use
2. a check conflated an errored response with an empty one
3. the fake assistant message omitted `"role"`, which a real response includes
4. no fake ever emitted a `</think>` tag, so the leak went unseen until a live run
5. every scripted turn terminated, so nothing exercised a real exhaustion

Each was caught only by running against reality. The third also revealed a real
robustness gap — the cell now sets `role: "assistant"` explicitly rather than
appending the model's message verbatim.

**The process fix is to build fakes from captured real responses** rather than
from memory of the API. Not yet done; it needs one live capture per shape stored
as a fixture.

## Not yet done

- No cell has been recorded through the detector end to end.
- `build_inputs` covers the eight shapes plus one mixed template. No multi-turn
  inputs, so chained tool use is only exercised when a model chooses to chain.
- Only one model has ever driven a cell. Everything measured here, and the
  reasoning leak in particular, may be specific to `granite4.2:8b`.
- The stale view shifts a principal's prior records but not their figures,
  because the packs hold no history of the figures to shift. A knowledge-base
  staleness fault therefore has a narrower surface than it should.
