# Recorder — current state

Three-arm replay and input deduplication. `src/aprime/recorder.py`,
`src/aprime/dedup.py`.

## Collection protocol

`record(invocations, {A, A_prime, B}, k)` collects k samples per input per arm.
All three arms are required; the call raises without A_prime, because without a
decoy there is no calibrated false-alarm rate and every threshold is a guess
(MTH-007).

**Interleaved, never batched.** Temperature-0 decoding is not deterministic on
batched serving infrastructure — 1000 completions of one prompt gave 80 unique
outputs, and the divergence rate moves with server batch size (MTH-015). A decoy
arm collected in a burst before the candidate, or at a quiet hour, measures a
different noise floor than the candidate experiences and mis-calibrates
everything downstream.

**Arm order rotates by sample index**, so no arm permanently occupies the
cold-cache position. It costs nothing and removes a whole class of argument
about the result.

Every sample carries a monotonic `order`, and `Recording.interleaving_gap()`
reports the longest single-arm run — so interleaving is *checked* rather than
assumed. A batched collection shows a gap on the order of the corpus size; the
current implementation holds at 1.

Adapter exceptions are captured as samples with an `error` field rather than
aborting the run. A partial recording with visible failures is more useful than
no recording, and the clouds exclude errored samples.

## Pausing a long recording

Recording dominates the cost of a run by roughly two orders of magnitude: the
first end-to-end pass spent 589 seconds recording and 10 seconds detecting
(MTH-024). A full study is hours of wall clock, so a run has to survive being
stopped.

`record(..., should_stop=callable)` checks at every **triple boundary**, so a
stop never splits a triple and never costs more than one triple of work. When it
fires, `record` raises `RunPaused`.

**Raising rather than returning a partial recording is the whole design.** A
partial recording has short clouds for the inputs it reached and none for the
rest. Sent to the detector it produces thresholds fitted to fewer decoys and
mode shares over two samples instead of ten, and **nothing in the report says
so**. The numbers look entirely ordinary. Raising is the only place that failure
can be stopped, so it is stopped there.

`stop_requested(path)` makes the signal a file appearing on disk rather than a
process signal, because whoever wants the run stopped is usually not at the
terminal that started it: the run was left going overnight, and the person or
agent asking for it to stop is somewhere else.

`recording_progress(checkpoint, invocations, k)` reports how far along a run is
without touching a model, and counts separately any triples on disk that the
current plan no longer contains. Counting those as progress would report a run
as further along than it is.

### The checkpoint key has to be the configuration, not the run

`scripts/run_cell_detection.py` names its checkpoint after the **configuration
hash**. A checkpoint named after a run timestamp cannot be found by the next
run, which makes it a crash log rather than a checkpoint. Keying on the
configuration also means that changing the corpus, k, the fault or an instrument
changes the key, so a resume can never silently mix work recorded under two
different configurations.

### Anything derived alongside the recording has to be persisted too

A resumed session never re-invokes the triples it skips. Anything the harness
learns *while* invoking is therefore lost unless it is written down, and the loss
is silent. The per-input fault activation labels are the live case: they are
saved next to the checkpoint after every invocation, and the run reports how
many inputs carry no label so that an activation rate computed from a resumed
run is read as a lower bound rather than a measurement.

## A sample with no output is not evidence

A server that stops listening does not stop the recorder. Failed invocations are
recorded as samples, which is right for one transient failure and was wrong for
the 698 consecutive ones a dead server produced over 24 minutes (ENG-008).

Three guards now, because it failed in three places:

- **`record(..., abort_after_dead=3)`** raises `RecordingFailed` after that many
  consecutive triples in which every arm failed. One failed triple is noise; a
  run of them means nothing is answering.
- **`load_checkpoint` does not count an all-error triple as finished**, so a
  rerun collects it. It previously did, which meant a resume would skip the dead
  triples permanently and the recording could never exceed 3% real.
- **`recording_progress` reports `error_rate` and `dead_triples`**, and
  `checkpoint_health` answers directly. A fraction alone cannot tell a finished
  run from a failed one, which is how a 97%-failed recording was reported as
  100% complete.

A triple where only *some* arms failed is kept. It still carries real outputs,
and at k>1 the input survives on its other samples, so retrying it risks looping
on an arm that always fails.

**The checkpoint is append-only, so the last write per `(triple, arm)` wins.** A
retried triple has both attempts on disk. Judging it on the errors it used to
have leaves it dead forever, which silently makes the recovery path a no-op.

## The decoy arm has to be able to vary

`decoy_independence_warnings(arms)` warns when A and A-prime are configured with
the same pinned seed. A-prime is the second baseline run and it **is** the null
distribution that target-decoy FDR calibrates against. Under a pinned seed,
eight repeats of one identical request produced **2 distinct outputs**, against
**8** with the seed unset (MTH-023). A null supported on two points calibrates a
tail quantile no better than one supported on a single point, and the failure is
entirely silent: all three arms record cleanly and the FDR column fills with
confident numbers.

The rule is **mirror the deployment**, not force a difference. A deployment that
genuinely pins its seed genuinely has near-zero self-variance, and for that one
an exact diff answers the question better than this tool does.

Two deliberate limits:

- **It warns, it does not refuse.** The check cannot see every system's
  configuration, so refusing on it would block runs it is not able to judge.
- **It is duck-typed and often silent.** The adapter Protocol carries no sampling
  configuration and must not start to, so this looks for a `seed` on the system,
  on a transport the system holds, or in a `sampling` dict, and says nothing when
  it finds none. **Silence is not approval.** See ENG-006 for why the boundary
  was left alone.

## Deduplication

Near-duplicate inputs corrupt two things: they inflate the apparent number of
independent observations, so the FDR estimate runs over a corpus with fewer
effective units than it believes, and they create dense embedding regions that a
hotspot search will report as a finding. Production corpora are full of them.

Dedup runs before any counting, testing or clustering. No exceptions.

`normalise()` is deliberately conservative — casefold, strip accents, collapse
whitespace, trim edge punctuation. Anything more aggressive starts merging inputs
a system could legitimately answer differently, which hides behaviour rather than
removing noise.

The representative keeps its own id and the group records everything it stands
for, so a report can say "this finding covers 47 requests".

**Known gap, and it must be stated wherever a derived number is reported:**
exact and normalised matching only. Semantic near-duplicates — the same question
in different words — need an embedding pass and are not handled. Residual
duplication is not zero.
