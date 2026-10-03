# Work for a machine with no GPU

**Written 2026-10-04 for a Claude Code cloud session running on free trial
credit that expires 2026-11-06.** After that date this file describes nothing
real and should be deleted.

If you are reading this on a machine that has a GPU and a running Ollama, you
are not the audience. Go to `CLAUDE.md` and the per-family `STATE.md` files.

## The constraint that produced this list

Recording needs the system under test, which is Ollama serving
`granite4.2:8b` on the owner's PC. A cloud environment has no GPU and the trial
credit is Claude usage, not compute. So **no new study data can be produced
here**, and anything that needs a recording is out of scope.

If you try anyway, the preflight stops you in about a second and says the server
is unreachable. That is working correctly, not a problem to solve.

What a fresh clone *can* do: run the 218 tests in five seconds, read every
recording already committed under `results/`, re-run
`scripts/diagnose_channels.py` against them, and all documentation and analysis
work.

## The list, in the order the owner agreed

### 1. D19, the paper's audience row

The reader seat's audience contract in `docs/reader/METHODS.md` has a row for
every outward-facing artifact except the paper, which is marked GAP. Decide who
reads it, what they may be assumed to know, and what must be defined. The owner
wants to do this one, so draft two or three options rather than picking.

It blocks the paper, which is why it is first.

### 2. The blind-spot map

Highest value on this list. It is a declared figure for the paper, and **the
data is already in the repository**: four probe runs totalling 1.3 MB under
`results/probes_*.json`. Nothing to measure, only to analyse and draw.

It also turns the README's honest-limits section from prose into a figure, and
those limits are the most-cited part of the document so far.

### 3. The provenance knowledge doc

`src/aprime/provenance.py` exists and works. `docs/knowledge/provenance.md` does
not exist, and `docs/study/STATE.md` still lists run provenance as a GAP with
the note that no number enters the paper before it exists.

That is a same-commit-rule violation from earlier work: code landed without its
layer-2 doc. Cheap to fix, and it clears a stated blocker on the paper.

### 4. The detector's report format

Marked GAP in `docs/engine/STATE.md`. The detector currently prints whatever
`Report.text()` produces. It needs a format a reader can act on.

### 5. F2, prompt regression

I previously recorded this as blocked on needing a system with an editable
prompt. That was wrong: `Cell.system_prompt()` exists, so the cells have one.
Buildable and unit-testable with no GPU, against the captured fixtures in
`tests/fixtures/ollama_chat.json`.

### 6. F11, retrieval degradation

Returning the wrong rows rather than older ones. The current `_shift` in
`cells/tools.py` serves older content of the same shape, which is staleness and
already covered by F5. Degradation needs its own handler. Code plus tests, no
GPU.

### 7. ENG-003

Clustering is recomputed three times per comparison. Logged as pressure rather
than fixed. The fix is code, and it can be verified against a recording already
on disk, so the cost claim can be re-measured here.

## Explicitly not here

- The nine-cell factorial, or any slice. Needs the GPU.
- Re-running the severity titration. The two files on disk are from the
  exact-match era and ENG-002 records that run as a saturated instrument rather
  than a result.
- Shape-stratified thresholds used for real. The code exists; every run so far
  pooled into one stratum because no output format had 30 inputs.
- The transfer matrix and the leave-one-out validation. Both sit downstream of
  the factorial.
- A hosted-model comparison. Deferred on cost, see HANDOFF §15 and its two
  amendments. Nothing to build until the owner gives a go.

## Before the trial ends

Anything written into `.agents/` is gitignored and will be lost when the
instance goes, except the two research documents that are committed as
exceptions. If you create a dossier there and it is worth keeping, say so
explicitly rather than assuming it travels. See `docs/knowledge/environment.md`.
