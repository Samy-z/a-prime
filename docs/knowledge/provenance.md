# Provenance — how a number traces back to the run that produced it

Current state of `src/aprime/provenance.py` and of the files the runners write.
Read before adding a runner, adding a parameter that changes a result, or
quoting a number anywhere outward-facing.

The rail (CLAUDE.md): every number in the paper traces to a run id and a config
hash. This doc says what those are, where they are written, and where the
tracing still breaks.

## Two kinds of fact, and the line between them

`capture()` snapshots two kinds of thing, and the distinction is the whole
design:

| Kind | Fields | Rule |
|---|---|---|
| **Hashed** | `instruments`, `params`, `corpus` | Anything that changes a result. Two runs with the same config hash should be comparable. If they are not, something that affects results is missing from the hash, and that is a bug to hunt. |
| **Recorded, not hashed** | `git_commit`, `git_branch`, `git_dirty`, `platform`, `python`, `packages`, `notes` | Explains a discrepancy after the fact without making every environment change look like a different configuration. |

The test for which side a new thing goes on: would two runs that differ only in
this produce different outputs? If yes, hash it. If no, record it. The model
host is the worked example: it is in `notes`, never in the hash, because the
same weights served from another box give the same outputs, and a hostname in
the hash would make one run on two machines look like two configurations
(`docs/knowledge/environment.md`).

The seed policy went the other way. MTH-023 established that A and A-prime
built under the same pinned seed collapse the null, so `seed_policy` is a
param and is hashed.

## The identifiers

- **`run_id`** is the UTC start time, `%Y%m%dT%H%M%SZ`. It identifies an
  execution, not a configuration; two runs of the same thing get two ids.
- **`config_hash`** is the first 16 hex characters of SHA-256 over the
  canonical JSON of `{instruments, params, corpus}`, keys sorted, no
  whitespace. A dict built in a different order hashes the same. Change any
  hashed value and the hash changes.
- **`corpus`** is `corpus_fingerprint(ids, texts)`: SHA-256 over the sorted
  input ids, each followed by its text when available, first 16 hex. Order-
  independent, so a reshuffled corpus is the same corpus; text-aware, so the
  same ids with different content are not.

Instruments are recorded as `hub_id@revision`. A bare name is not a pin,
because what sits behind a name on a hub can change; `capture()` warns when it
sees one without `@`. The runners write three:

    predicate     NLIEquivalence@0.7 on MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli
    nli_revision  6f5cf0a2b59cabb106aca4c287eed12e357e90eb
    system_model  granite4.2:8b@<first 16 of the Ollama digest>

The authoritative revision table is `docs/methods/STATE.md`, maintained by hand.
Nothing checks it against what the runs recorded; a mismatch would be found by
a person reading both.

## Where it is written, and the two layouts

| Runner | Result file | Layout |
|---|---|---|
| `run_cell_detection.py` | `results/cell_detection_<run_id>.json` | provenance fields flattened at the top level (`run_id`, `config_hash`, `git_commit`, `git_dirty`, `params`, `instruments`) |
| `run_study.py` | per-cell rows under `results/study/`, matrix in `results/study/matrix.json` | flattened via `row_provenance()`, plus the system digest, session count and an analysis timestamp; `check_row_provenance()` runs per row **before that cell's report file is written**, so a refusal (exit 4) leaves no untraceable file of any kind. Phase 2 is `analyse()`, driven model-free end to end by `tests/test_study_analysis.py` against a synthetic recording laid out as the recorder lays out a real one |
| `titration.py` | `results/titration_<run_id>_<config_hash>.json` | the whole `RunProvenance` under a `"provenance"` key |
| `demo_detect.py` | stdout only | prints run, config, git |
| `run_probes.py` | `results/probes_<run_id>_<config_hash>.json` | **does not use `capture()`**; see the gap below |

Two layouts exist because the runners were written a day apart and nobody
unified them. Anything that reads provenance generically has to handle both.
New runners use `row_provenance(prov, **extra)`, which returns the flattened
fields (`run_id`, `config_hash`, `git_commit`, `git_dirty`) ready to splat into
a row, and `check_row_provenance(rows)`, which names any row missing one of
`REQUIRED_ROW_PROVENANCE`. One helper so two runners cannot drift apart on what
they record, which is how the gap below appeared.

## The config hash is the resume key

Recordings live at `results/recordings/<config_hash>.jsonl`, with
`<config_hash>.activation.json` beside it and `<config_hash>.STOP` as the pause
flag. This is the mechanism that makes runs resumable (`recorder.md`), and it
has a consequence worth stating:

- Change a hashed value (k, q, n, fault, seed policy, the model digest, the
  predicate) and you get a **new recording**, started from nothing.
- Change a non-hashed value (host, git commit, Python version) and you
  **resume the same recording**. Deliberate: moving the model server to another
  machine mid-run continues the run.

So a hashed param added later silently orphans every checkpoint on disk, and a
param wrongly left out of the hash lets two different configurations append to
one file. Both are quiet. When adding a param, decide its side first.

## Dirty trees are recorded, not blocked

`git_dirty: true` means the recorded commit does not describe the code that
ran. `capture()` warns loudly and carries on; blocking would push people to
commit noise to satisfy a tool. The warning is suppressed for the study runner
(`warn_if_dirty=False`), which is the long unattended run where a warning at
the start helps nobody.

The record stays. `results/cell_detection_20260930T001738Z.json` is a dirty run
and says so; a reader of that file cannot reconstruct the exact code, only its
nearest commit.

## Traps already fallen into

**A hashed string is part of a filename, so tidying it is a migration.**
`make_job` in `run_study.py` records the judging model's revision as a bare
SHA under `instruments`, and `capture()` warns on every run that a bare value
is not a pin. The pin is correct; the warning is cosmetic. The one-line fix
that silences it, prefixing the model id, is not cosmetic: `instruments` feeds
the config hash, the config hash names every cell's checkpoint, and a renamed
checkpoint is an orphaned recording. Measured on otherwise identical inputs,
the bare form hashes to `9864af6f7989ee8a` and the prefixed form to
`9ed71b092eb45c10`. This session offered that fix while `banking-summary` was
46 percent recorded; the local session checked before taking it. Decision
2026-10-04: leave the warning until the factorial completes, then change the
format at a boundary where nothing is part-recorded, expecting to re-record
anything in flight. The general rule: **anything inside `instruments` or
`params` is load-bearing for the filename, not only for the record, and a
formatting change there is a schema migration wearing the clothes of a typo
fix.** The guard comment at the call site says the same.


**A pin in name only.** The same file records `system_digest: "unresolved"`.
Ollama's `/api/show` carries no digest; `/api/tags` does, and the runner asked
the wrong endpoint for several runs. Every one of those runs has a config hash
that pins the model by tag alone, which is exactly the silent instrument change
the rail exists to prevent. Fixed 2026-10-03; runs before that date carry the
weaker pin and should be read as such.

**The factorial's rows carried the config hash and nothing else, until
2026-10-04.** `run_study.py` called `capture()`, used the result to name its
checkpoints, then wrote a per-cell row with `config_hash` alone; the run id,
git commit and dirty flag were computed and dropped. Found while writing this
document, before the factorial had run, so no number was affected. Fixed the
same day (`75081ad`): rows go through `row_provenance()`, and the runner refuses
to write the matrix rather than warn when a row is untraceable, because an
untraceable number in a committed file looks usable. Five tests, one pinning
the broken shape.

**The probe runner sits outside `capture()`.** `run_probes.py` computes its own
hash over the pair texts and the model specs, and records the resolved model
revisions per channel, which is the right hash for that job. But it records no
git commit, no package versions and no dirty flag. The four probe files under
`results/` that feed `probes.md` and the blind-spot map are therefore traceable
to their pair set and their weights, and not to the code that scored them.
Nobody has needed that trace yet. The fix is to call `capture()` with the pair
hash as `corpus`, and it has not been done because it would change the config
hashes of files the ledgers cite by hash.

**Owner decision, 2026-10-04: fix it in the same commit as the next probe
re-run, not before.** The next re-run is already named (STD-009, reopen-if:
the normalised pair set scored with the second checkpoint and the embeddings).
That run is new regardless, so the one-time change in how probe hashes are
computed coincides with a run nobody would compare to an old one, and the
hash scheme stays consistent on each side of that boundary. Whoever makes
that run: call `capture()`, keep the pair hash as `corpus`, record the legacy
hash in `notes` for the four committed files' sake, and date the change here.

**`packages` records the torch version without its build.** The GPU machine
runs `2.14.0+cu126` and `importlib.metadata` reports it as such, but a CPU box
reports `2.14.0`, so the same pinned requirement looks like two versions. See
the note in `requirements.txt`.

## Derived artifacts carry their sources

A file computed from other result files names them. `results/blind_spot_map.json`
lists the run id, config hash and relabelling of each probe file it read, and
the figure prints them in its footer. The rule for any future derived artifact:
if it was not produced by a run, it must say which runs it was produced from,
or a number in it cannot be traced.

## Tracing a number, start to finish

1. The caption or table names a run id (and, for probes and titrations, a
   config hash). If it names neither, the number is not quotable yet.
2. Open the matching file under `results/`. For a derived artifact, follow its
   `sources` to the run files.
3. `git_commit` gives the code; `git_dirty` says whether to trust it exactly.
4. `instruments` gives the weights by revision; the digest gives the system
   under test. Before 2026-10-03, check whether the digest reads `unresolved`.
5. For the raw samples behind a detector result, the recording is
   `results/recordings/<config_hash>.jsonl`.

Where a step fails, the gap belongs in this document, not in the caption.
