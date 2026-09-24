# Adapters — current state

The system-under-test boundary. `src/aprime/adapter.py`, `src/aprime/stub.py`.

## The interface

    Invocation(input_id, text, session_id?, principal?)  ->  Response(output, Trace)

That is everything a-prime is allowed to know about a system it measures. No
logprobs, no internals, no access to the system's knowledge or its corpus.

**The restriction is the product claim, not an inconvenience.** A detector built
against information it will not have for a stranger's system is not the detector
being tested. This is also why the Palworld reference system is consumed across
this boundary from its own repository rather than vendored in.

### Resist widening it

Every proposed field is a dependency on something another system may not expose.
When the pressure comes, record it in `docs/engine/LEDGER.md` rather than acting
on it, so the accumulated pressure is visible instead of each concession looking
individually reasonable in isolation.

`Trace` carries only what an outside caller can see: latency, tools called,
steps, finish reason, model id, error. If a field can only be filled by
instrumenting the system's internals it does not belong here — it belongs in the
harness's fault-activation record, which is a separate artifact and is **not**
visible to the detector.

### Why identity is in the interface

`session_id` and `principal` are present from the first commit because of fault
classes F8a and F8b. A sticky fault concentrates a request-level problem onto a
subset of users — the Anthropic routing error ran at 0.8-16% of requests but
touched ~30% of users — and an identity-aware system produces per-user
clustering with no fault present at all. A detector that cannot see which
requests belong together cannot separate those two, and MTH-009's
cluster-splitting never gets validated against the case it exists for.

Both are optional. Plenty of systems are genuinely identity-blind.

## Arms

One instance is one arm. Baseline and candidate are two objects, not one object
with a flag, so nothing in the detector can condition on which arm it is looking
at — not even accidentally.

Arms are `A`, `A_prime`, `B`. All three are mandatory at record time.

## The stub

`stub.py` is a synthetic system whose true behaviour is known exactly. It is not
an LLM imitation; it exists so the detector's output can be checked against
ground truth rather than against a plausible story.

Each input maps to candidate outputs with a probability vector — deliberately
multimodal, since MTH-005 showed a centroid-and-spread summary is blind to
mode-share shifts. Mode shares vary across inputs so the corpus contains both
near-deterministic and well-spread cases.

A and A_prime share one behaviour table by value. B carries a perturbed table on
a known subset, and that subset is the ground truth nothing downstream can see.

Perturbations: `mode_share` (move mass between existing modes), `add_mode`
(introduce an output the baseline never produced), `collapse` (concentrate on
the modal answer — a reliability change with zero centroid displacement).

`sticky_principals` implements F8a: B behaves like the baseline for everyone it
does not touch, so the request-level and user-level rates come apart.
