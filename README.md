# a-prime

Detect when an LLM system's behaviour changes — without knowing what its outputs
mean, and with a false-alarm rate you can actually state.

The name is the method. Before comparing baseline **A** to candidate **B**, run
A twice. The second baseline run, **A′**, is a comparison where *nothing
changed by construction*, so its scores are the null distribution — measured on
your corpus, your models, and the same afternoon. No distributional assumption,
no p-values, no hand-written assertions.

```
              ┌──► A   ─┐
  your inputs ─┼──► A′  ─┼──►  A vs B  = targets   ─┐
              └──► B   ─┘     A vs A′ = decoys    ─┴──► threshold at FDR q
```

> **Status: week 1 of 4.** The detector runs end to end against a synthetic
> system with known ground truth. It has never been pointed at a real one. Every
> number below is reproducible from this repo; none of it is a product claim.

## Measured end to end

300 inputs, 12 samples per arm, 30 genuinely changed, model-free path:

| | |
|---|---|
| realised false-discovery rate | **0.034** against a 0.10 budget |
| recall | **28 / 30 = 93%** |

That FDR figure is the point of the whole design, and it can only be checked
here — a real deployment never tells you which inputs genuinely changed, which
is exactly why the synthetic system exists rather than being a shortcut.

```bash
python scripts/demo_detect.py
```

## What each channel can and cannot see

Most of the value in this repo is the negative results. Measured on 896 probe
pairs across 4 subject domains and 4 output shapes, at a 5% false-alarm budget:

| channel | catches | blind to |
|---|---|---|
| NLI contradiction | 7 of 8 fact changes, 84–100% | omission, entirely |
| NLI directional, **upper tail** | dropped conditions, 98.4% | everything else |
| NLI directional, **lower tail** | added content, 100% | everything else |
| structural conformance | broken schemas, wrong scripts, mid-sentence stops, refusals | anything semantic |
| embedding displacement | **worse than chance, ungated** | see below |

**Embedding displacement is anti-correlated with meaning change.** Across three
model families, pooled separability was 0.391 / 0.440 / 0.532 — at or below a
coin flip. Rewording moves the vector about **twenty times further** than
changing a number, a date, or a negation. It recovers only when the candidate's
surface style is stable, so it ships behind a gate that measures that
precondition and refuses the channel when it fails. A channel below chance is
worse than an absent one, because it will be trusted.

## Ideas worth stealing

**The decoy arm does two jobs.** Beyond calibrating the false-alarm rate, it
prunes induced rules. Structural invariants are inferred from what the system
actually produces — the Daikon idea, never ported to LLM outputs — and Daikon's
famous problem is emitting far more candidates than a human can triage. A rule
that holds on A and breaks on an independent re-run of A was never structural.
Rules that survive both arms are enforced; rules that hold *often* are surfaced
as questions; the rest are dropped.

**One statistic, two tails, two faults.** Entailment asymmetry is positive when
information was removed and negative when it was added. The sign names the
fault. Taking the absolute value — which was the first implementation — conflates
them and discards the only piece of information that tells you which happened.

**Control and power are measured separately.** Conflating them is how a detector
ends up with its budget quietly widened to hit a recall target. Here the FDR
test asserts only calibration; power has its own test and its own published
envelope, including the regions where there isn't any.

## What's honest about the limits

- k=10 samples per arm has **8% power** against a moderate change. k=20 reaches
  73%. The operating point is 60 model calls per input, not 30.
- A ~0.3 mode-share shift is undetectable at every k tested.
- NLI results are **checkpoint-dependent**: a second model reproduced the
  direction of every finding and none of the magnitudes, with per-category gaps
  up to 48 points.
- Deduplication is exact and normalised only; semantic near-duplicates are not
  handled.
- The embedding gate's threshold is a guess, and labelled as one.

## Layout

```
src/aprime/     adapter, recorder, dedup, normalise, clustering, stats,
                fdr, conformance, gating, provenance, detect
docs/knowledge/ what is true now, one doc per subsystem
docs/*/LEDGER.md settled findings with evidence and a reopen-if clause
HANDOFF.md      why the design is what it is
```

Start with [`docs/knowledge/probes.md`](docs/knowledge/probes.md) for the
blind-spot map and [`docs/knowledge/detector.md`](docs/knowledge/detector.md)
for how the pieces compose.

## Prior art, honestly

This is not an empty field. [Clausius](https://github.com/beatakouchnir/clausius)
does label-free regression detection with a measured null and gets there first
on the slogan; it reads logprobs, so it is local-only and cannot touch a hosted
API. UK AISI's [Inspect](https://inspect.aisi.org.uk/) has the statistical core —
repeated decodes, clustered and paired standard errors — as a harness you
configure per eval. [Giskard](https://github.com/Giskard-AI/giskard) ships
metamorphic invariance tests. Arize Phoenix orders embedding clusters by drift.

What appears to be unoccupied: inducing structural rules from a baseline's own
output distribution, and the A′ decoy arm as a black-box calibration primitive.

```bash
python -m pytest tests/ -q     # 103 tests, no models required
```
