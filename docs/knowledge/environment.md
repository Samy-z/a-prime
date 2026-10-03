# Environment — what travels with the repo and what does not

Current state doc. Read before moving this project to another machine, and
before moving it back.

The project is being worked on temporarily from a Claude Code cloud instance
(free credit until 2026-11-06) and will return to the owner's PC afterwards.
**Both directions matter, and they are not symmetric.**

## What the repository carries

Everything the study needs to be audited and continued, except the hardware:

| In git | Why it matters |
|---|---|
| `CLAUDE.md`, `HANDOFF.md`, `docs/**` | layers 1, 2, 3 and every ledger |
| `src/**`, `tests/**`, `scripts/**` | the tool, 218 tests, every runner |
| `results/**` including `results/recordings/*.jsonl` | run artifacts and their provenance, so a recording can be re-analysed anywhere |
| `tests/fixtures/ollama_chat.json` | captured real API envelopes, so the test doubles do not drift back to being written from memory |
| `requirements.txt` | the five direct dependencies, added 2026-10-03 because nothing could rebuild the venv before that |

So a fresh clone can run the tests, read every recording, re-run
`diagnose_channels.py`, and do all documentation and analysis work. That is most
of what a machine without a GPU can usefully do here.

## What the repository does not carry, and must not

### `.venv/` — rebuildable, correctly ignored

`pip install -r requirements.txt`. Note the torch comment in that file: the
pinned version deliberately omits the `+cu126` local version so the file works
on a machine without that CUDA.

### The Hugging Face model cache — about 2 GB, outside the repo

Five models: DeBERTa-v3-base-mnli-fever-anli and roberta-large-mnli for the NLI
channel, plus all-MiniLM-L6-v2, bge-base-en-v1.5 and e5-base-v2 for the
embedding probes. They download on first use into `~/.cache/huggingface/hub`.
Pinned by revision in provenance, so a re-download is the same weights.

### The system under test does not have to be on this machine

`host` has always been a parameter on both adapters; only the two main runners
assumed localhost, and since 2026-10-03 they read `APRIME_OLLAMA_HOST`:

    APRIME_OLLAMA_HOST=http://192.168.1.50:11434 python scripts/run_study.py --go

So the GPU work can be moved off this PC without moving the study: run Ollama on
another box and point the runners at it. **What cannot be moved is the
requirement for a GPU somewhere.** A Claude Code cloud environment is a
development sandbox with no GPU, and the credit attached to it is Claude usage
rather than compute, so moving a session to the cloud moves the agent and leaves
the system under test exactly where it was installed.

**The host is recorded in provenance and deliberately kept out of the config
hash.** What has to match for two runs to be comparable is the weights, which the
digest pins; where they were served from does not change an output, and a
hostname in the hash would make the same run on two boxes look like two
configurations. Verified: the same corpus resolves to the same hash against two
different hosts.

That puts real weight on the digest. It is the only thing establishing that
another box serves the same `granite4.2:8b`, and it comes from `/api/tags`:
`/api/show` has no digest field, and asking the wrong endpoint recorded the
model as "unresolved" into a config hash for several runs, which is a pin in
name only.

### Ollama and `granite4.2:8b` — the system under test

6.8 GB of weights and a server on `localhost:11434`. **This is the hard
boundary.** No cells can be recorded without it, so no new study data can be
produced anywhere that lacks it. Since 2026-10-03 the recorder says so in about
a second rather than filling a checkpoint with connection errors for 24 minutes
(ENG-008, ENG-009).

### `~/.claude/CLAUDE.md` — machine facts, and copying it would be a mistake

It documents TLS interception, `core.autocrlf=true` in the system gitconfig, a
1536x864 display and a Windows Python path. **Every one of those is a statement
about one computer.** On a Linux cloud box they are wrong or irrelevant, and an
agent reading them would reach for `truststore` against a problem it does not
have and assert a Python that does not exist. The file says this itself: it is
restricted to machine and environment facts, which are by definition not
portable. Leave it where it is, on both machines, each describing its own.

### `.agents/` — layer 4, gitignored, and the one real round-trip risk

92 KB across seven files, including a 59 KB fault-taxonomy research document and
a 28 KB model survey. `CLAUDE.md` says never committed, and for the worklogs
that is right: they are scratch.

**The two research documents are a different thing.** They are the evidence
behind BCH-004's severity floors and the model-pool choices, they took real work,
and they exist on exactly one disk with no backup. Anything a cloud session
writes into `.agents/` is invisible to git and therefore **silently lost when the
cloud instance goes away**. That is the single most likely way for work to
disappear in this migration, because nothing will warn about it.

Decision for the owner, not taken here: commit the two research documents and
keep the worklogs ignored, or keep the current rule and copy `.agents/` by hand
in both directions. The first is auditable and survives; the second preserves
the stated rule and depends on remembering.

### Auto-memory — empty, and keyed to a path

`~/.claude/projects/<key>/memory/` holds no files. The key follows the session's
working directory, so a cloud instance with a different path starts fresh
regardless. Nothing to migrate.

Worth knowing: **this repository is public.** Owner-scoped notes about working
style belong in auto-memory precisely because it is local, and moving them into
the repo to make them portable would publish them.

## Coming back

The return trip is the easy direction, provided one rule held while away:

**Anything that matters was committed and pushed.** Git is the only channel that
round-trips without a manual step, and everything a GPU-less machine can produce
here is git-tracked anyway: docs, ledgers, the paper, analysis of recordings
already on disk.

On return:

1. `git pull` on the PC.
2. Rebuild nothing: the venv, the model cache and Ollama are all still here.
3. `python -m pytest tests/ -q` to confirm the environment still matches the
   code, which is also the cheapest check that a dependency did not drift.
4. Copy back anything from `.agents/` by hand, if the current rule was kept.

The one thing a cloud instance cannot hand back is study data, because it cannot
produce any. Recording stays pinned to the machine with the GPU.
