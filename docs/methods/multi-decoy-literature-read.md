# EVIDENCE READ — decision 5 of the MTH-027 first append; a read, not a decision

Dated 2026-11-11. Commissioned by the owner's ratification of the audit
menu (methods LEDGER, MTH-027 first append). Question: what multi-decoy
target-decoy estimator provably controls FDR, and what does that imply for
the parked C' = (1+d)/(rt) and the titration's b > 1 dial (b baseline
clouds, r = b-1 star decoy pairs per target)? Sources were fetched and
read on 2026-11-11, not recalled.

## Sources, each with the one thing it proves or constructs

- **Emery, Hasam, Noble, Keich — "Multiple competition-based FDR control
  and its application to peptide detection"** (arXiv:1907.01458; RECOMB
  2020). The load-bearing construction. With d decoys per target (d1 =
  d+1 scores), each hypothesis is reduced BY WITHIN-HYPOTHESIS COMPETITION
  to a label and one score: rank the target among its own d1 scores;
  label it an original win if its rank is in the top i_c, a decoy win if
  in the bottom d1 - i_lambda, ignored otherwise; the carried score W_i
  is a (possibly randomized) representative of the top ranks. Estimate at
  a cut, sorted by W:
  `(1 + #decoy-wins) / max(#original-wins, 1) * c/(1-lambda)`,
  with c = i_c/d1, lambda = i_lambda/d1. **Theorem 1 (finite sample):**
  FDR <= alpha if the null-label conditional probabilities property holds
  (conditional on all W, true-null labels iid with P(win) = c,
  P(decoy win) = 1-lambda). **Theorem 2:** iid decoys per null target
  plus an equal-coverage mapping condition imply it; the proof reduces to
  Barber-Candes SSS+ / Lei-Fithian Adaptive SeqStep. Extends to a
  "conditional null exchangeability" setting (their supplement 6.9).
  Special cases: d=1, c=lambda=1/2 is classical TDC; the **max-method**
  (c = lambda = 1/d1: the target must be the maximum of all d1 scores to
  win) makes the factor c/(1-lambda) = **1/d — the only legitimate
  "division by the number of decoys" in this literature, and it divides
  the decoy-WIN count, never a pooled above-threshold count.** Their
  data-driven variants (FDS, LBM) have no finite-sample proof; ignore.
  Also proves the negative result we need: **pooling decoys across
  hypotheses breaks down** — pooled p-values are dependent (shared decoy
  batch) and non-uniform when scores are not calibrated across
  hypotheses, and BH/Storey over them can fail outright.

- **Gimenez, Zou — "Improving the stability of the knockoff procedure:
  multiple simultaneous knockoffs and entropy maximization"** (AISTATS
  2019, PMLR v89; arXiv:1810.11378). The knockoff-side mirror of the same
  idea. With kappa knockoffs per feature, jointly sampled: winner index
  (which of the kappa+1 copies scored highest) and gap statistic tau;
  estimate `(1/kappa + (1/kappa) * #{winner != original, tau >= t}) /
  max(#{winner = original, tau >= t}, 1)`. FDR control via reduction to
  SeqStep+, REQUIRING extended exchangeability of the joint draw —
  **running single knockoffs kappa times in parallel and aggregating by
  consensus breaks the symmetry and does not control FDR.** The payoff
  that motivated our C': the detection floor drops from ceil(1/q) to
  **ceil(1/(q*kappa))**.

- **Rajchert, Keich — "Controlling the FDR via competition: is the +1
  needed?"** (arXiv:2204.13248; Stat. Prob. Letters 2023,
  10.1016/j.spl.2023.109819). At the standard competition setting
  (c = 1/2) and alpha in {0.01, 0.05, 0.1, 0.2}, replacing the +1 by any
  t < 1 either changes no rejection or fails FDR control in some regime
  (building on He et al.'s negative results; simulated failures from
  n ~ 300). **No relief comes from shrinking the +1 itself; the floor
  must be bought with more competitors, not a smaller offset.**

- **Ren, Barber — "Derandomised knockoffs: leveraging e-values for false
  discovery rate control"** (JRSS-B 2024; arXiv:2205.15461). Knockoffs
  is in essence an e-BH procedure; aggregating e-values across multiple
  knockoff REALIZATIONS gives derandomized selection with FDR control
  "without any additional conditions", at comparable power and much lower
  selection variability. **The principled route for aggregating across
  repeated decoy draws is e-values, not vote-counting** — the valid
  version of what naive repetition attempts. (A 2025-range preprint line
  notes averaging across replicates leans conservative; power is the
  price of derandomizing.)

- **Luo, Ebadi, He, Emery, Noble, Keich — "Competition-based control of
  the false discovery proportion"** (arXiv:2011.11939; Biometrics 2023,
  FDP-SD). Upgrade path, not a current need: confidence bounds on the
  realized FDP in the TDC/knockoff setting, stronger than
  FDR-in-expectation.

- **Keich, Tamura, Noble — aTDC** (bioRxiv 440594; JPR). Averages many
  SINGLE competitions to reduce TDC's variance; built for settings where
  iid decoys fail; Emery et al. report their direct multi-competition
  beats it. Not a candidate here.

- Recency sweep (2024-2026): nothing found that overturns competition
  counting; the active directions are e-value aggregation and decoy
  QUALITY (learned/generated decoys, a 2026 bioRxiv benchmark line). The
  quality literature matters less for us than for proteomics: our decoys
  are real second runs of the same system, not constructed surrogates.

## Verdict on the audit's prior

"The literature is competition-counting, not division" — **confirmed in
substance, refined in one detail.** Valid division by the decoy count
exists in both literatures (Emery's max-method factor 1/d; Gimenez-Zou's
1/kappa), but it always divides a count of within-hypothesis COMPETITION
OUTCOMES under a joint exchangeability condition, with the +1 (or 1/kappa
offset) intact. What nothing in the literature licenses is exactly C' as
parked: counting every decoy score above a pooled threshold across inputs
and dividing by r. Three independent reasons it is anti-conservative or
invalid: (i) the Rajchert-Keich line — the effective offset of
(1+d)/(rt) in win units is 1/r < 1, which is the regime where control
provably fails; (ii) Emery's pooling caveat — per-input score
distributions are not calibrated across inputs (our mode statistics
certainly are not), and pooled counts of dependent decoys do not estimate
the null target count; (iii) our r star pairs share the A cloud, so the
pooled decoy count is over-dispersed relative to the binomial the
SeqStep+ bound needs.

## Mapping onto this project

- **The star design fits the competition form better than it fits
  pooling.** Per input, the r+1 scores {s(A,B), s(A,A'_1), ...,
  s(A,A'_r)} all share A's cloud. Conditional on A's cloud, under the
  cloud-level H0 (B, A'_1..A'_r exchangeable clouds, independent sampling
  within arms — the MTH-027 append's decision 2 wording), the r+1 scores
  are iid functions of iid clouds, hence exchangeable — the dependence
  through the shared A is harmless to WITHIN-INPUT competition while it
  is exactly what poisons pooled counting. This is a derivation, not a
  theorem for our statistic: it is what decision 4's all-null row must
  verify. Note (a') is untouched: sub-cloud sample dependence breaks
  cloud exchangeability one level down for every form equally.
- **The floor arithmetic C' promised survives under the legitimate
  form.** Max-method at r = 3 decoy pairs: zero decoy wins give estimate
  (1/T) * (1/3) <= 0.10 at T >= 4 — the floor of 4 that motivated C',
  reached without leaving the finite-sample guarantee. General rule:
  ceil(1/(q*r)) original wins minimum.
- **Compatibility note the un-parking append must state.** Our frozen
  r = 1 estimator counts targets and decoys separately above a shared
  cut (no within-input competition); the Emery family at d = 1 reduces
  to classical TDC (within-pair competition), which is not byte-identical
  to our rule. Paper one's estimator stays as validated (MTH-018) and
  frozen; the cross-system r > 1 selection adopts the competition form as
  a DIFFERENT, dated instrument. The two must not be silently treated as
  one estimator.
- **Randomization warning.** Emery's general (c, lambda) needs a
  randomized rank map (mirandom) and random tie-breaking; our pipeline is
  deliberately deterministic given recordings, and our statistics live on
  coarse grids with heavy ties (decision 3's gate). The max-method is the
  deterministic member of the family up to ties; the tie rule for ranks
  within an input must be declared alongside decision 4's
  `best_achievable` tie settlement.
- **e-values are the aggregation route, not the selection route, for
  us.** If the titration ever wants "run the whole selection several
  times and stabilise", Ren-Barber's e-BH aggregation is the valid
  construction; vote-counting across repeated selections is not.

## Graded recommendation for the un-parking append (not a decision)

1. **Adopt the Emery (c, lambda) within-input competition family for
   r > 1, instantiated as the max-method** (c = lambda = 1/(r+1)):
   deterministic up to ties, finite-sample theorem via NLCP, factor 1/r,
   floor ceil(1/(q*r)). Freeze: the family, the instantiation, the
   within-input rank tie rule, and the star-pair layout with its
   exchangeability argument written out. Grade: strong — two independent
   literatures converge on it, and it delivers exactly the resolution C'
   was parked for.
2. **Measure before freezing** on decision 4's all-null row: realized
   FDR of (i) the max-method and (ii) naive C', at b in {2, 3, 4} and
   k in {6, 20}, crossed with the (a') rho sweep. Expectation to file
   with the row: max-method controls everywhere sub-cloud dependence is
   absent; naive C' exceeds budget somewhere in the grid. If naive C'
   happens to control in our exact geometry, that is a finding about our
   geometry, not a licence — the append still adopts the form with the
   theorem.
3. **Keep r = 1 untouched** everywhere paper one's estimator is cited;
   the competition form enters only with cross-system r > 1 work, under
   its own dated entry and tests.
4. **Park e-value aggregation** as the named future route for
   derandomization (titration stability), with Ren-Barber as the anchor
   citation; nothing adopts it yet.

## Reopen if

- Decision 4's all-null row contradicts max-method control in our
  geometry (then the exchangeability derivation above is wrong somewhere
  and the read reopens);
- a post-2024 e-value TDC construction supersedes the competition family
  for within-run multi-decoy selection (the sweep found none through
  2026);
- the dense-grid tie behaviour (decision 3's gate) makes within-input
  ranks unstable at k >= 20, in which case the tie rule, not the family,
  is the problem;
- anyone proposes applying this read's forms at r = 1 in place of the
  frozen paper-one estimator — that is a different decision and needs
  its own entry.
