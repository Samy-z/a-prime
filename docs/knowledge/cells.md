# Domain cells — current state

`src/aprime/cells/`. Nine systems under test: 3 domains x 3 output formats.
Maintainer doc, not linked from the README (D20).

## Structure

| File | Holds |
|---|---|
| `packs.py` | knowledge packs — data only, generated deterministically from a seed |
| `tools.py` | the eight tool shapes, instantiated per domain, plus fault hooks |
| `cell.py` | `Cell` (a `SystemUnderTest`) and `build_inputs` |

**A cell's three output formats are `extraction`, `summary` and `agent`, and
`agent` names what the cell must OUTPUT** -- a short decision line -- not a kind
of system being audited. All three call tools, so all three are agents in the
ordinary sense. This was called a cell's `mode` until 2026-09-30, which collided
with the semantic modes `clustering.py` finds in an output cloud. One word, two
unrelated meanings, in one codebase; it confused a reader who had every reason
to expect otherwise. The field is now `Cell.output_format` and the tuple is
`FORMATS`.

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

| output format | output | shape inferred as |
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

### The request corpus is phrased per output format

`build_inputs(pack, ..., output_format=...)` wording follows the format. Only `agent`
differs from the plain corpus: a question is what an extraction or
summarisation consumer actually sends, but a decision line answers a decision
request and nothing else. Demanding APPROVE / DECLINE / ESCALATE in reply to
"what is the status of AC-4000?" is an incoherent instruction, and the model
correctly ignored it (BCH-015).

The two corpora line up record for record — same ids, same tool shape, same
position — so nothing about the comparison moves except the framing. Passing
the format is also stamped into the input id, because the recorder groups by input id
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

## The agent format is distinct but not compliant

Measured live, `granite4.2:8b`, 12 invocations per format (BCH-015):

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

What the agent format does wrong is put the decision last. It reasons in a paragraph
and appends the verdict; the rule asks for the verdict first. Three rounds of
fixes moved compliance 1 to 3 to 4 out of 12, the last round buying one input
for roughly 40% more GPU time, at which point further fixing becomes tuning the
bench until the number looks right.

The spread is the real problem, and it is not the one the compliance count
points at. Agent outputs vary by a factor of 36 where summary varies by 3. A
shape-stratified threshold has little to hold on to there.

**The agent format costs 3.5x what summary costs** — 202 seconds against 57 for the
same 12 invocations, 51 tool calls against 19. At full corpus size that is the
dominant term in the GPU budget, and it is not yet costed.

## Test doubles are captured, not written

Eight times a hand-written test double diverged from the real API:

1. the fake transport invented a `sha256:` digest prefix a live server does not use
2. a check conflated an errored response with an empty one
3. the fake assistant message omitted `"role"`, which a real response includes
4. no fake ever emitted a `</think>` tag, so the leak went unseen until a live run
5. every scripted turn terminated, so nothing exercised a real exhaustion
6. every fake tool found what it was asked for, so no fake ever ran out of options
7. real `tool_calls` entries carry an `id`; no fake had one
8. real `function` objects carry an `index`; no fake had one

Every one cost a live run to find and none was caught by a test. A fake written
from memory encodes what we believe the API does. A fixture encodes what it
does, and the two only differ where it matters.

**So the doubles are now built from captured bodies.**
`scripts/capture_chat_fixtures.py` records real responses into
`tests/fixtures/ollama_chat.json`; the test helpers take the envelope from
there and substitute only the payload a test needs to choose. With the fixture
file absent the tests fail and say why, because a fallback to hand-written
doubles is precisely what hid the eight divergences above.

Items 7 and 8 were found by the capture itself, within a minute of it first
running, and 7 was a live bug rather than a test artifact: **without echoing
`tool_call_id`, a turn containing several tool calls has its results matched to
calls by position alone**, so any reordering attaches an answer to the wrong
question. The cell now echoes it.

## Not yet done

- No cell has been recorded through the detector end to end.
- `build_inputs` covers the eight shapes plus one mixed template. No multi-turn
  inputs, so chained tool use is only exercised when a model chooses to chain.
- Only one model has ever driven a cell. Everything measured here, and the
  reasoning leak in particular, may be specific to `granite4.2:8b`. The captured
  fixtures come from that model too, so they record one server's shapes.
- Runs recorded before 2026-09-30 carry `mode` where these now say `format`.
  `check_shape_distinctness.py` reads either.
- **Input ids changed shape on 2026-09-30.** Passing `output_format` stamps it
  into the id, so `banking-lookup-000` is now `banking-extraction-lookup-000`.
  Two consequences. Extraction and summary get identical request text under
  different ids, which is intended, because an input id identifies a request
  within one cell's corpus and cross-cell pooling by id was never meant to work.
  And a recorder checkpoint written before the change will not match ids written
  after it, so a resumed run would redo the work rather than corrupt it. No cell
  has been through the recorder yet, so nothing is affected today.
- The stale view shifts a principal's prior records but not their figures,
  because the packs hold no history of the figures to shift. A knowledge-base
  staleness fault therefore has a narrower surface than it should.
