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
