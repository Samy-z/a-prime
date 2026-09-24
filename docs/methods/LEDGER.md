# methods — LEDGER

Append-only settled findings. Prefix `MTH-###`. Never edit an entry in place;
correct it with a dated append below it. Negative results are recorded as
carefully as positive ones. **Grep this file before starting any statistical
investigation.**

Entry format: id, date, finding, consequence, evidence, reopen-if.

---

## MTH-001 — Three-way triage (benign / regression / improvement) is unidentifiable
**Date:** 2026-09-24
**Finding:** Direction cannot be recovered from the detector's primary features.
Every distributional statistic in the design is symmetric in A and B, so (A,B)
and (B,A) produce identical features. A classifier trained on directionally
labelled fault injection will learn asymmetric proxies instead — B is shorter,
noisier, refuses more — and those proxies are wrong for the dangerous failure
mode: confident, fluent and wrong.
**Consequence:** Ship change / no-change with FDR guarantees, plus a separately
validated and explicitly labelled heuristic risk score. Direction comes from a
human or a calibrated judge, never from the statistic.
**Evidence:** Statistical methodology review, 2026-09-24.
**Reopen if:** an asymmetric primary feature with demonstrated validity is found
— meaning-sensitive, not a length or entropy proxy.

## MTH-002 — Normalised displacement ratio has no null distribution
**Date:** 2026-09-24
**Finding:** Between-cloud distance over pooled within-cloud spread does not go
to zero under the no-change null; it converges to a constant depending on k and
dimensionality, with its own variance. It cannot produce a p-value.
**Consequence:** Replaced by energy distance on centred, L2-normalised
embeddings, plus a mode-share test, plus a separate dispersion test, all
calibrated against the A-prime decoy arm.
**Evidence:** Statistical methodology review, 2026-09-24.
**Reopen if:** never — a property of the statistic, not of our data.

## MTH-003 — Zero observed spread does not mean deterministic at small k
**Date:** 2026-09-24
**Finding:** The planned "floor is zero, fall back to exact match" branch is
invalid. A system emitting P with probability 0.9 shows five identical samples
about 59% of the time. By the rule of three, k identical samples bound the
minority rate only at roughly 3/k. The fallback converts ordinary sampling
noise into confident false positives.
**Consequence:** No per-input observed zero drives a decision. Use a
Beta-Binomial posterior on the disagreement rate with a stratum prior, and let
the decoy arm handle the degenerate case natively.
**Evidence:** Statistical methodology review, 2026-09-24. Arithmetic checked
independently.
**Reopen if:** k rises high enough that the bound is tight for the regime in
question — state the k and the bound when reopening.

## MTH-004 — Stratification must not use spread estimated from the same samples
**Date:** 2026-09-24
**Finding:** Binning inputs by observed variance and then estimating variance
within the bin is circular and produces regression-to-the-mean bias. Low bins
systematically under-estimate true spread, which is precisely where false
positives are generated.
**Consequence:** Stratify only on covariates independent of the outcome: input
length, input-embedding cluster, task type, or entropy from a separate draw.
**Evidence:** Statistical methodology review, 2026-09-24.
**Reopen if:** never.

## MTH-005 — Mean-and-spread summaries are blind to the changes that matter
**Date:** 2026-09-24
**Finding:** For a baseline emitting P 70% / Q 30% moving to B emitting Q 100%,
centroid displacement is about 0.3 of the P-Q gap against a within-cloud spread
of about 0.46 — a ratio near 0.65, unflagged, despite total mode collapse. The
mirror case scores identically, and a deterministic-to-stochastic change has
zero centroid displacement.
**Consequence:** Represent each output cloud as a distribution over semantic
modes, not a point with a radius. Test mode-share change and dispersion change
separately.
**Evidence:** Statistical methodology review, 2026-09-24.
**Reopen if:** never.

## MTH-006 — Minimum viable k is 10 per arm for per-input claims
**Date:** 2026-09-24
**Finding:** Fisher exact at 5-vs-5 has a minimum two-sided p of 2/C(10,5),
about 0.008 — only a complete flip is detectable, and nothing survives
multiplicity across thousands of inputs. At 10-vs-10 a complete flip reaches
p about 1e-5. k=20 gives roughly 0.73 power for a 70-to-30 mode-share shift at
alpha 0.05.
**Consequence:** k=10 per arm minimum, three arms, 30 calls per input. k=5 is
for corpus-level screening and ranking only, never per-input flags.
**Evidence:** Statistical methodology review, 2026-09-24. Combinatorics checked
independently.
**Reopen if:** cost forces a reduction — the claim must then downgrade from
per-input flags to corpus-level screening, explicitly.

## MTH-007 — Target-decoy FDR preferred over Benjamini-Hochberg here
**Date:** 2026-09-24
**Finding:** BH controls FDR under positive dependence, plausible but unproven
across inputs sharing one model, and production corpora contain near-duplicates
that make the dependence lumpy. The Benjamini-Yekutieli correction factor is
about 9.8 at m=10,000 and impractical. Sampling the baseline twice gives decoys
that share the dependence structure exactly:
FDR-hat(t) = (decoys above t + 1) / (targets above t).
**Consequence:** The A-prime arm is mandatory on every run, interleaved in time
with B. It doubles as a provider-drift alarm — a large A-vs-A-prime signal means
the baseline endpoint changed underneath us.
**Evidence:** Statistical methodology review, 2026-09-24. BY factor checked
independently (harmonic sum at m=10,000 is about 9.79).
**Reopen if:** a cheaper calibration with demonstrated validity under the same
dependence structure appears.

## MTH-008 — Generality claims are bounded by system count, not input count
**Date:** 2026-09-24
**Finding:** Inputs within one system are near-replicates; the unit for any
cross-domain claim is the system. With all systems succeeding, the two-sided
95% Clopper-Pearson lower bound on the per-system success rate is 0.54 at n=6
and 0.66 at n=9. "Worked on every system we tried" is consistent with failing
on a third of systems.
**Consequence:** The headline claim is stated with this interval. Adding systems
is the only lever that moves it, and returns are shallow — n=10 gives 0.69.
**Evidence:** Statistical methodology review, 2026-09-24. Bounds checked
independently.
**Reopen if:** never — arithmetic.

## MTH-009 — Validation must cluster-split by system; random splits are invalid
**Date:** 2026-09-24
**Finding:** A classifier will learn system identity — output style, embedding
region, floor level — as a fault signature. Random splits inflate every number.
**Consequence:** Required holdouts: leave-one-system-out; leave-one-fault-type-
out; never split a cell across train and test, including across severities; all
hyperparameter and threshold selection nested inside the LOSO folds. Report
random / LOSO / LOFO / LOSO-x-LOFO side by side so the gap is visible.
**Evidence:** Statistical methodology review, 2026-09-24.
**Reopen if:** never.

## MTH-010 — A 30-80 case real-regression holdout cannot support a fine claim
**Date:** 2026-09-24
**Finding:** Wilson 95% intervals on a recall point estimate of 0.80 are
[0.63, 0.90] at n=30 and [0.70, 0.87] at n=80. That detects catastrophic
non-transfer and nothing finer. Worse, collectable regressions are the ones
someone noticed — the large obvious ones — so the cases we most want to catch
are absent by construction.
**Consequence:** The real-regression set is a sanity check, not a headline
number. Any figure from it is published with its interval.
**Evidence:** Statistical methodology review, 2026-09-24.
**Reopen if:** the set exceeds about 200 cases drawn from more than three
systems.
