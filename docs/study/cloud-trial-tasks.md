# Work for a machine with no GPU

**Written 2026-10-04 for a Claude Code cloud session running on free trial
credit that expires 2026-11-05, 8:59 AM GMT+1.** After that date this file describes nothing
real and should be deleted.

**It goes stale fast.** It was already a day out of date the first time it was
read, because D19 had been decided in the meantime. Check `HANDOFF.md` for
anything dated after this file before trusting the task order below.

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

### Already decided, do not redo

**D19 is ratified** as of 2026-10-04. The paper is written for somebody who
ships LLM systems and might use the tool: software literacy assumed, everything
else defined including the statistics. See HANDOFF §16. An earlier version of
this file listed choosing that reader as task one.

**D24 is ratified.** The README becomes a front door pointing at the paper, but
**not until the paper exists**, and the honest-limits headlines stay in the
README regardless. See HANDOFF §17 for what moves and what does not.

### 1. The blind-spot map — DONE 2026-10-04 (STD-009)

Highest value on this list. It is a declared figure for the paper, and **the
data is already in the repository**: four probe runs totalling 1.3 MB under
`results/probes_*.json`. Nothing to measure, only to analyse and draw.

It also turns the README's honest-limits section from prose into a figure, and
those limits are the most-cited part of the document so far.

**Do not run `scripts/run_probes.py`.** It downloads four models and needs real
compute, and it would regenerate data that is already committed. On a machine
with no GPU it will either fail or grind for hours producing what is already
sitting in `results/`. Read those files.

### 2. The provenance knowledge doc — DONE 2026-10-04

`src/aprime/provenance.py` exists and works. `docs/knowledge/provenance.md` does
not exist, and `docs/study/STATE.md` still lists run provenance as a GAP with
the note that no number enters the paper before it exists.

That is a same-commit-rule violation from earlier work: code landed without its
layer-2 doc. Cheap to fix, and it clears a stated blocker on the paper.

### 3. The detector's report format — DONE 2026-10-04 (HANDOFF §19)

Marked GAP in `docs/engine/STATE.md`. The detector currently prints whatever
`Report.text()` produces. It needs a format a reader can act on.

### 4. F2, prompt regression — DONE 2026-10-04 (BCH-016)

I previously recorded this as blocked on needing a system with an editable
prompt. That was wrong: `Cell.system_prompt()` exists, so the cells have one.
Buildable and unit-testable with no GPU, against the captured fixtures in
`tests/fixtures/ollama_chat.json`.

### 5. F11, retrieval degradation — DONE 2026-10-04 (BCH-017)

Returning the wrong rows rather than older ones. The current `_shift` in
`cells/tools.py` serves older content of the same shape, which is staleness and
already covered by F5. Degradation needs its own handler. Code plus tests, no
GPU.

### 6. ENG-003 — DONE 2026-10-04, except the live re-measurement (see the ENG-003 append)

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
