# The cross-system null — PROPOSAL, awaiting owner ratification

**Status: PROPOSAL, drafted 2026-10-20 by the cloud session. Not a decision.
Nothing here is frozen; nothing may be recorded against it until an owner
ratification is appended to this file with a date and the methods STATE
points at that append.** Written to the methods STATE queue opened
2026-10-16 (HANDOFF §24 amendment), which gates paper two's pre-registration
(`docs/study/preregistration-2-draft.md`).

The question: A versus A-prime calibrates one system against its own
variation. A versus B, where B is a different system, has two self-variances
and no entry says whose null certifies the comparison. This proposal names
three candidate designs, says what each does to the estimator in
`src/aprime/fdr.py`, what the recorder needs to generalise, and how the
stored-baseline regime fits, and recommends one.

## 1. What the estimator assumes, read from the code

`fdr.estimate_fdr` is `(1 + d) / max(t, 1)` with `t` the targets and `d` the
decoys at or above a cut, both compared as values (ENG-010). `select` takes
the most permissive cut with the estimate at or under `q`; `best_achievable`
reports the lowest estimate any cut reaches. Three consequences carry over
unchanged into any cross-system design:

1. **The floor.** With no decoys above the cut the estimate is `1 / t`, so
   nothing is reportable below `1/q` findings (MTH-024). No design below
   changes this, because the `+1` is per selection, not per decoy.
2. **The null is the decoys' order statistics.** The estimate at a cut is
   set by how many decoys sit at or above it, so the resolution of the
   estimate is the step `1 / t` in the numerator per decoy. At k=6 the
   partition statistics take seven values and the decoys crowd them; the
   extraction cells were silent at best estimates 0.111 and 0.176 and
   detected fully at k=20 (STD-010, STD-013). **Resolution, not separation,
   was the binding limit in every silent cell except the agent row**, where
   the decoys cover the fired-target range (STD-011 appends).
3. **Validity rests on exchangeability.** For an input where the null is
   true, the target score and the decoy score must have the same
   distribution. The code never checks this; the design has to deliver it.

What the null *is* for a cross-system comparison has to be said before the
designs can be compared. Per input `i`, let `H0_i` be: **A and B have the
same output distribution on `i` at the level the channel reads.** For the
partition channels (share of answers, new answers, spread) that level is
the mode distribution after the judge merges paraphrases, so two models
giving the same answer in different words satisfy `H0_i`. For the
text-level channels (contradiction, information direction) it is the
pairwise relation between samples, where two models' house styles can
differ with no difference in answer; see §5.

Under `H0_i`, every two-cloud score among `{A_i, A'_i, B_i, B'_i}` has the
same marginal distribution, because the four clouds are draws from one
distribution. That single fact is what each design below spends.

## 2. The three candidate designs

Notation: clouds `A, A', B, B'` of `k` samples per input; `s(X, Y)` a
channel's score, larger meaning more different; targets `T_i = s(A_i, B_i)`;
within-system decoys `D_i^A = s(A_i, A'_i)` and `D_i^B = s(B_i, B'_i)`.

### Design 1 — four arms, pooled null, ratio-adjusted estimator

Decoys: both within-system scores, pooled, so `2n` decoys stand against
`n` targets. Estimator:

    FDR_hat_r(t) = (1 + d(t) / r) / max(t(t), 1),    r = 2

with `d(t)` the pooled decoy count at or above the cut. Under `H0_i` the
expected number of null targets above a cut equals the expected number of
either decoy set above it, hence equals the pooled count divided by `r`;
the numerator estimates the same quantity as today with half the variance,
and the `+1` offset is unchanged. The pooled estimator is the "separate
decoy search with a decoy-to-target ratio" form that proteomics uses when
the decoy database is larger than the target one: the decoy count is
divided by the ratio before it stands for the false matches (Elias and
Gygi 2007; Käll et al. 2008; the variance reduction from several decoys is
the point of the averaged and multiple-competition methods, Keich et al.
2019 and Emery et al. 2020; see §7 on what was and was not verified).

What it does to the estimate: the numerator moves in half-steps. A cut
with 15 targets and one of the two decoy sets above it reads
`(1 + 0.5) / 15 = 0.100`, reportable at `q = 0.10`, where today's estimator
reads `2 / 15 = 0.133` and reports nothing. The floor is untouched. The
gain is exactly at the margin the silent cells sat on.

What it does not do: it does not separate what is not separated. In the
agent cells the decoys span the fired targets' range; adding the second
system's decoys adds coverage, not clearance. Pooling helps resolution and
only resolution.

Validity: exact under `H0_i` by the exchangeability argument above. The
pooled null is a mixture of the two self-variances, and where the two
differ (one system tight, one loose) the mixture is wrong only on inputs
where `H0_i` is false, which are the inputs the comparison is meant to
flag; a mixture affects power there, never the false-discovery count.
**This is an argument, not a proof.** The guarantee for the single-decoy
form rests on Barber and Candès; the ratio form with the `+1` is standard
practice in proteomics rather than a theorem for this score. Paper two's
pre-registration therefore includes a null pair, one model recorded as
both A and B under two names, whose realised false-discovery rate must
come in at or under `q`, exactly as MTH-018 validated the single-decoy form
on the stub.

Symmetry: `T_i = s(A_i, B_i)` is one of four cross pairs. The other three,
`s(A, B')`, `s(A', B)`, `s(A', B')`, are not pooled into the target: an
average of four correlated draws does not share a distribution with
single-draw decoys and would break exchangeability. They are **replicate
target sets**, selected separately and reported as a stability check, the
way MTH-018 reported power per seed: four selections from one recording
say whether a flagged set is a property of the pair or of one draw.

### Design 2 — per-input maximum

Decoy per input `D_i = max(D_i^A, D_i^B)`; estimator unchanged. Under
`H0_i` the three scores are exchangeable and the maximum of two of them
exceeds the third two times in three, so in the tail the decoy count runs
at about twice the null target count: the estimate is conservative by a
factor approaching two, the realised rate runs near `q / 2`, and the
reportable set shrinks accordingly. Valid, symmetric, no new estimator,
and no resolution gain: the numerator still moves in whole steps. It buys
safety the single-decoy form already has and pays for it in power.

### Design 3 — two one-sided selections

Run `select` twice: targets against `D^A` (is B further from A than A is
from itself) and against `D^B` (than B is from itself). Each selection is
valid at `q` on its own. The union is not controlled. The intersection is
not controlled either in general: the false discoveries of each set can
coincide while the true ones do not, and no bound follows from the two
`q`s. Each selection carries the full `1/q` floor, so the intersection
needs ten clean of each null. Its merit is interpretive: the two sets
answer two questions a user may want answered separately. **Recommended
as a report, never as a selection rule**: the per-system self-variance and
the two one-sided counts are printed beside the pooled selection, which
is the one that flags.

### Not proposed: head-to-head competition

Proteomics' target-decoy competition pits each target against its own
decoy and keeps the winner. Applied per input it discards the score
ordering across inputs that `select` works from, and it reduces to a
sign test at `k` small. The pooled separate-search form keeps the order
statistics the whole method is built on.

## 3. Recommendation

**Design 1, with Design 3's two one-sided counts and each system's
self-variance reported beside it.** Four grounds:

1. It is the only candidate that adds resolution, and resolution was the
   binding limit in five of the six silent cells of paper one.
2. It is valid under the same assumption the current estimator already
   makes, and symmetric in the two systems.
3. It degrades gracefully: with one within-system pair missing it is
   today's estimator (`r = 1`), which is what the stored-baseline regime
   needs (§5).
4. It is the `m = 1` case of the generalised estimator the agent titration
   needs (`docs/methods/agent-self-variance-titration-proposal.md`, dial
   `m`): with `m` baseline runs of one system the within pairs number
   `m(m+1)/2` and `r` is the number of decoy pairs per target, all
   exchangeable with the target under `H0_i` though not independent of one
   another. One estimator serves both studies, which is one thing to
   freeze rather than two.

The combination rule, to be frozen before any cross-model tuple is
recorded: **targets `s(A, B)`; decoys the union of all within-system pairs;
`r` the number of decoy pairs per target; estimate `(1 + d/r) / t`; cuts,
ties and membership as in `fdr.py` today.** Nothing in the rule depends on
which system is called A.

## 4. What the recorder needs

`record` requires exactly `ARMS = ("A", "A_prime", "B")` (`adapter.py`),
rotates the lead arm by `idx % 3`, writes the three samples of an
`(input, sample_idx)` together or not at all, and `load_checkpoint` calls
a triple complete when `set(ARMS)` is present and dead when every arm
errored. Generalising is a roster change, not a redesign:

- the arm roster becomes a property of the run, derived from the `arms`
  mapping passed to `record`, with at least one system carrying a second
  run (the decoy requirement generalised: no roster without a within pair);
- the atomic unit is the full roster for one `(input, sample_idx)`:
  rotation over `len(roster)`, completeness as all arms present, dead as
  all arms errored, resume unchanged;
- the roster enters the configuration hash, because a recording with
  four arms is a different configuration from one with three;
- `detect` takes the roster's pairing (which arms are targets, which pairs
  are decoys) instead of reading `clouds("A")`, `clouds("A_prime")`,
  `clouds("B")` by name; `Recording.clouds` needs nothing;
- the preflight asks one question per arm; the cost is `len(roster) / 3`
  of today's per-input time, 4/3 for the four-arm design.

The existing three-arm tests must pass unchanged with the default roster,
plus a four-arm round trip through checkpoint, pause and resume. The
library exposes any roster, because a user may want `m` baseline runs;
the study fixes the roster in its registration (CLAUDE.md, study
constraints are configuration).

MTH-015 applies to every arm: all four interleaved, same load regime,
same triple-group. The agent cells' per-call time makes a four-arm agent
tuple four times 15 to 65 seconds (the measured means per cell, STD-011
and the titration proposal's cost table), which is the honest budget line.

## 5. The stored-baseline regime, and the text channels

**Version bump.** The flagship scenario is a model updated under the user:
A was recorded weeks ago, B is live, and the arms cannot be interleaved.
The target `s(A_p1, B_p2)` spans two periods. The stored pair `(A, A')_p1`
is a valid null for A's self-variance under period-one load; the live pair
`(B, B')_p2` for B's under period-two load; neither contains the term that
time alone adds, and MTH-015 says a decoy from another load regime
mis-calibrates. There is no decoy that shares the target's regime, because
the target has two.

What the design can do: pool both pairs (`r = 2`), disclose the regime
mismatch, and gate certification on the drift negative control (MTH-026),
whose three comparisons are exactly the missing term measured on the same
system: cross-period with the stored pair as null, cross-period with the
live pair as null, within-period as sanity. If the control flags nothing
in both cross-period comparisons, the time term is below the certification
floor for this system, corpus and gap, and a stored-baseline comparison
may be certified with that disclosure. If it flags, the count and the best
estimates quantify the term, and the comparison is reported with the
control's numbers beside it and not certified at `q`. If A is no longer
servable, the control cannot run; the design degrades to `r = 1` on the
live pair alone and the report says the null is one-sided and the time
term unmeasured.

The period-two recording for the first control sits at 212 of 240 triples
on main (`results/drift/drift-p2.4366ced9c36980a3.jsonl`); its report is
the first number this regime gets.

**The text channels carry a style confound no within-system decoy
calibrates.** Two models that give the same answer in different house
styles satisfy `H0_i` at the mode level and not at the pairwise text
level: the contradiction and information-direction scores between an A
sample and a B sample can exceed those between two A samples with no
difference in answer, and `D^A`, `D^B` are both within one style. For
cross-system use the partition channels select; the text channels are
reported, not selected on, until the null-pair check in the
pre-registration shows what their realised false-alarm rate is across two
styles. This is a limitation of the method's decoy construction, not of
the estimator, and it belongs in paper two's limits.

## 6. What this proposal asks the owner to ratify

1. Design 1 as the cross-system null, with the combination rule in §3
   frozen by a dated append here before any cross-model tuple is recorded.
2. The generalised estimator `(1 + d/r) / t` as a change to `fdr.py` under
   an engine entry, with the three-arm case (`r = 1`) byte-identical in
   behaviour and a test asserting it.
3. The recorder roster change (§4) as an engine entry, three-arm behaviour
   unchanged.
4. The stored-baseline gate (§5): certification only when the drift
   control is silent, disclosure otherwise.
5. The text channels reported and not selected on in cross-system runs
   until the null-pair check has run.

## 7. Evidence, and what was not verified

`src/aprime/fdr.py` at the commit this file lands in; MTH-007, MTH-015,
MTH-018, MTH-023 and its correction, MTH-024 and its correction, MTH-025,
MTH-026; STD-010, STD-011 appends, STD-012, STD-013; the recorder's
`record` and `load_checkpoint`.

Proteomics references, from a web search on 2026-10-20 that confirmed each
paper's existence and gist but not its exact estimator: Elias and Gygi
2007, *Nature Methods* 4:207, the target-decoy strategy and the
concatenated-versus-separate distinction; Käll, Storey, MacCoss and Noble
2008, *J. Proteome Res.* 7:29, decoy databases as the null with FDR
analysis; Keich, Tamura and Noble 2019, *J. Proteome Res.*, averaged
target-decoy competition over several decoy sets to cut the estimate's
variability; Emery, Hasam, Noble and Keich 2020, multiple competition-based
FDR control, relating the construction to Barber and Candès's knockoffs.
**Before paper two cites any of them for the ratio form of the estimator,
the full texts are to be read for the exact formula and its conditions.**

**Reopen if:** the null-pair check in paper two's pre-registration realises
a false-discovery rate above `q` under Design 1, which would mean the
pooled exchangeability argument does not hold for these scores; or the
drift control flags in a within-period comparison, which indicts the
harness rather than the design.
