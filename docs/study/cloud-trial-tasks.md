# Work for a machine with no GPU

**Rewritten 2026-10-19 for the Claude Code cloud session (trial credit expires
2026-11-05, 8:59 AM GMT+1 — about two weeks left).** This is the third
hand-off; the first two lists are done and live in git history. **Check
`HANDOFF.md` for anything dated after this file before trusting it.**

If you are reading this on a machine that has a GPU and a running Ollama, you
are not the audience. Go to `CLAUDE.md` and the per-family `STATE.md` files.

## What changed since the second hand-off

- The paper is complete against its evidence: section 8 and Appendix F carry
  the nine-cell k=6 matrix and the four k=20 cells against the D25
  prediction, the abstract's result is filled, the subtitle landed (RDR-010),
  and your three verification passes are in. One bracket remains: the agent
  format at k=20.
- Two GPU items run on the owner's machine on the next quiet night: the
  drift negative control (protocol MTH-026, expectations filed; its period-2
  recording sits at ~230 of 240 triples) and the banking-agent cell at k=20,
  the first data point of the agent self-variance investigation (methods
  STATE, owner-directed 2026-10-19). Their report files land on main when
  done. Do not wait on them for tasks 1-3 below.
- The network constraint stands: this instance cannot reach the model hosts,
  so nothing needing the NLI judge or the system under test runs here.

## Tasks, in the order the owner agreed

### 1. Draft the cross-system null design (a proposal, not a decision)

The methods STATE queues it: A-vs-B between two DIFFERENT systems has no
null yet. A-prime calibrates within-system variance only; a proper design
needs the candidate's own second run (B-prime) and a frozen combination
rule. Write `docs/methods/cross-system-null-proposal.md`, clearly headed as
a PROPOSAL awaiting owner ratification: the candidate designs (four arms
with pooled null, per-input max, two one-sided selections), what each does
to the (1+d)/t estimator, what the recorder's triple-atomicity needs to
generalise, and the stored-baseline regime (version bump: baseline weeks
old, interleaving impossible — MTH-026's drift control is its first
instrument). Argue from fdr.py, MTH-023/024/026 and the proteomics
literature on decoy-to-target ratios. Recommend one design and say why.

### 2. Draft the agent self-variance titration protocol

Methods STATE carries the owner's direction: investigate the agent
limitation with clear numbers before a reviewer does. Draft the protocol as
a dated proposal: the dials (k; number of baseline arms m, with the
estimator generalisation m>1 requires — this overlaps task 1, reference it;
temperature as the entropy dial; decision-token vs rationale-text channels),
a grid worth running, and a cost table from the measured 16.9 s per agent
invocation. The banking-agent k=20 cell (landing on main shortly) is the
first data point; design the rest of the grid around it.

### 3. Draft paper two's pre-registration skeleton

STD-012 names the second study's thesis: how much difference-information
between systems can be mined from outputs alone. Draft
`docs/study/preregistration-2-draft.md`, headed DRAFT — NOT REGISTERED:
the question stated falsifiably, the pool (D10's four models, confirmed
current by BCH-019), the protocol slots that wait on task 1's ratified
design, the sizing that MTH-024's rule dictates once k and q are chosen,
and empty prediction slots to be filled and dated BEFORE any recording.
This is the paper whose integrity story is "everything was registered
first"; the draft's job is to make that cheap to do.

### 4. When tonight's results land on main: fold them in

Pull first. The drift-control report (`results/drift/drift-control.*.json`)
carries three comparisons with expectations filed in MTH-026 — write its
paragraph into the paper where the stored-baseline/version-change
discussion lives, numbers from the file, bracket nothing. The banking-agent
k=20 report fills section 8's last bracket; if it is silent again, the
MTH-025 classification comes from the GPU machine's diagnosis, not from
here. Then the closing status footnote and the reader STATE row.

### 5. Not yet

The README front door (D24) stays gated until the owner says the paper
"exists" within the meaning of that decision — ask through the owner, not
here. LOSO needs the NLI judge: blocked on this instance. Nothing that
records.

## Hand-back

Commit and push on `main` unless the change is large enough to want review,
then a branch named `cloud/2026-10-19-<task>` and say so in the commit.
Anything in `.agents/` dies with the instance unless named a keeper in
HANDOFF. The owner's local session pulls, runs the suite, and drives the
GPU items.
