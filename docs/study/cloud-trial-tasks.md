# Work for a machine with no GPU

**Rewritten 2026-10-16 for the Claude Code cloud session (trial credit expires
2026-11-05, 8:59 AM GMT+1).** The 2026-10-04 list is done, items 1 to 6; it
lives in git history. This is the second hand-off. **Check `HANDOFF.md` for
anything dated after this file before trusting it**: the first version was a
day out of date the first time it was read.

If you are reading this on a machine that has a GPU and a running Ollama, you
are not the audience. Go to `CLAUDE.md` and the per-family `STATE.md` files.

## What changed since the first hand-off

- The k=6 matrix is complete: nine cells in `results/study/matrix.json`,
  analysed 2026-10-16 (HANDOFF §22, STD-010, STD-011). The agent row flags
  nothing in any of the three domains with 25 to 26 of 40 inputs touched.
- The k=20 summary row, the pre-registered D25 test (HANDOFF §21), is being
  recorded on the owner's GPU and is paused: banking-summary at 654 of 800
  triples, checkpoint `results/study/banking-summary.5aa2e096752e8c38.jsonl`.
  Do not wait for it. Write against the k=6 matrix and bracket what the k=20
  row will change, as section 8 already does for its gaps.
- Every result file carries its run id, configuration hash and commit; the
  matrix rows were analysed at `de23b8c` with a dirty tree holding results
  only. Quote those, not the chain log, which is gitignored.

## The constraint, unchanged

Recording needs the system under test, which is Ollama serving `granite4.2:8b`
on the owner's PC. **No new study data can be produced here.** The preflight
says so in about a second if you try. Everything below reads committed files.

What this machine can do: run the test suite in seconds, read every recording
under `results/`, run `scripts/diagnose_channels.py` (it needs the NLI judge,
which downloads from the Hub and runs on CPU in minutes, and no system under
test), and all documentation and analysis work.

## Tasks, in the order the owner agreed

### 1. Diagnose the agent row (STD-011's first reopen condition)

Run `scripts/diagnose_channels.py` over the three agent cells:
banking-agent `04b75acf8f69d4ec`, logistics-agent `4bc58937db555622`,
hospitality-agent `2cea59ca300a6358`. Read the script's own docstring for how
to classify what it prints: targets above the decoys is a power or sample-size
problem, targets among the decoys is blindness, decoys as wide as targets is
the system's own variation. Write the three `.diagnosis.json` files beside the
cells, as was done for the two extraction cells, and append to STD-011 with
the classification and the numbers. Two side questions belong in the same
append: why 944, 956 and 958 of 960 samples entered clustering in these cells
(`cost.samples_clustered`) when every other cell had 960; and whether the
distinctness figures in STD-011 (70 to 86 percent of samples unique after
normalisation) are the mechanism, or a coincidence of it.

### 2. Rewrite section 8 and Appendix F of `paper/draft.md` against the full matrix

Section 8 opens with "This section is partial by design" and a two-row table
with the agent row bracketed. Replace that framing: three rows recorded at six
samples; the agent row paragraph, new, written in the register of the
extraction paragraph and carrying task 1's diagnosis; the format effect as the
k=6 headline (five of six non-prose cells silent, one pair diagnosed as
resolution); "What is missing" updated so the k=20 rows read as recording
rather than missing; the provenance line updated to runs 20261015T205513Z and
20261015T205514Z and the commit; Appendix F to nine rows with the agent cells'
sessions (2, 2, 1), label completeness (40 of 40 in all three) and detection
times (67 s, 66 s, 80 s). Keep the D19 reader (HANDOFF §16) and the register of
section 1: a statistic is explained where it is used, nothing is compressed
into a name. Leave the abstract's [RESULT] blank; it fills with the k=20 row.
Bracket, do not guess, what k=20 will change. Then update the paper's closing
status footnote and the paper row of `docs/reader/STATE.md`.

### 3. Run `scripts/check_prose.py` on the rewritten section and act on it

It is advisory. The owner reads about two thirds of the paper on screen and
confirmed the register; a results section that drifts from it will be noticed.

### 4. Not yet

The README front door (D24) is gated on the paper existing: not now. The
leave-one-out numbers need the k=20 rows. Nothing that records.

## Hand-back

Commit and push on `main` unless the change is large enough to want a review,
in which case a branch named `cloud/2026-10-16-<task>` and say so in the
commit. The owner's local session pulls, runs `python -m pytest tests/ -q`
with the GPU machine's environment, and continues the k=20 recording. The
`.agents/` directory is gitignored and dies with the instance: if a dossier
there is worth keeping, say so in HANDOFF rather than assuming it travels
(`docs/knowledge/environment.md`).
