# Decoy calibration and FDR — current state

How a raw statistic becomes a flag with a stated false-alarm rate.
`src/aprime/fdr.py`, `src/aprime/stats.py`.

## The mechanism

Run the baseline twice. A-vs-A_prime is noise by construction, so the decoy
scores *are* the null distribution — measured on the same corpus, the same
models and the same day, and subject to the same dependence between inputs.

At threshold `t`:

    FDR_hat(t) = (1 + #decoys >= t) / max(1, #targets >= t)

`select()` returns the most permissive `t` whose estimate stays within `q`, and
an **empty selection** when none qualifies. A detector that reports nothing is
telling the truth; one that lowers its bar until it finds something is not.

The `+1` is the Barber-Candès conservative correction. It matters most in the
regime we care about — few discoveries — where omitting it lets one lucky
threshold report an FDR of zero off no evidence.

No null model, no distributional assumption, no p-values. Any statistic works
provided larger means more different.

## Ties are compared as values, not as floats

`tv_distance` is `0.5 * sum(abs(...))` over a set of mode keys, so the same
rational value can arrive on two adjacent floats depending on the summation
order: 5/6 is `0.8333333333333333` from one pair of clouds and
`0.8333333333333334` from another. Until 2026-10-16 the estimator compared raw
floats, `np.unique` produced two cuts where there was one, and at the upper cut
every score on the lower float, target or decoy alike, counted as below it
(ENG-010). Every public function in `fdr.py` (`estimate_fdr`, `select`,
`discoveries`, `best_achievable`, `select_stratified`) now rounds its inputs
to `SCORE_DECIMALS = 9` places before `np.unique` and before every comparison,
and thresholds are reported at that precision. Nine decimals is three orders
below what the artifacts store (six) and seven above the float noise that
caused it (about 1e-16); no channel resolves a difference below 1e-6.

- **Membership goes through `discoveries`.** A raw `targets >= sel.threshold`
  compares a 9-place threshold against unrounded scores and reintroduces the
  split in the other direction. `select_stratified` uses `discoveries` for the
  same reason.
- **The correction runs one way.** A cut the old code evaluated with some tied
  decoys missing is a cut the new code evaluates with all of them, and the old
  candidate set contained every value-consistent cut. So flagged counts can
  only fall and best-achievable estimates can only rise; a report or diagnosis
  written before the fix overstates at worst, never understates.
- **What it moved**, each re-derived without a model: the hospitality-agent
  `mode_share` diagnosis from 0.375 at cut 5/6 with 8 targets above 2 decoys to
  0.4 at cut 1.0 with 5 above 1 (STD-011 third append); the stub demo's
  dispersion line from "6 above every baseline score, 4 short of the floor" to
  "13 above 3 baseline scores, estimate 0.31" (README and paper appendix
  refreshed); the hospitality-agent decision-level best estimate from 0.4 to
  0.6 (`.decisions.json` regenerated). The 24 exact-match titration rows did
  not move. Regression test: `tests/test_fdr_ties.py`, built from real clouds
  through the real statistic.

## Statistics currently implemented

Clouds are distributions over modes, never a point with a radius (MTH-005).

| Statistic | Answers |
|---|---|
| `tv_distance` | Did the mix of answers change? Fraction of probability mass that moved. |
| `dispersion` | How wide is this cloud? Probability two draws differ. The measured noise floor for that input. |
| `dispersion_ratio` | Did the spread change, holding the mix aside? Catches collapse and explosion alike. |
| `novel_mode_mass` | Is the candidate saying things the baseline never said? Asymmetric, and uninformative at small k. |

Modes are exact-match strings. That is correct for structured output and for
the stub. **Free text needs semantic equivalence classes first**, and that
clustering is not built.

## Validation: control holds

Checked against ground truth on the stub, where the truly-changed set is known.
Across nine (k, severity) cells, mean realised FDR was **at or below 0.101**
against a target of 0.10. The calibration delivers what it claims.

This is the one claim that cannot be checked on a real system, because a real
system never says which inputs genuinely changed. It gets checked here or
nowhere.

## Validation: the power envelope, measured

Control and power are separate properties. Conflating them is how a detector
ends up with its budget quietly widened to hit a power target, so they have
separate tests.

Detection rate, 400 inputs, 40 truly changed, q=0.10, mean of 5 seeds:

| k | severity 0.3 | 0.6 | 0.9 | decoy p95 |
|---|---|---|---|---|
| 10 | 0.00 | **0.08** | 0.83 | 0.480 |
| 20 | 0.00 | **0.73** | 0.99 | 0.310 |
| 40 | 0.21 | 0.98 | 1.00 | 0.215 |

Three things follow.

**k=10 is not enough for a moderate shift.** MTH-006 derived k=10 as a floor
from combinatorics and k=20 for 40-point mode-share shifts. Measured on our
actual statistic, k=10 detects 8% of moderate shifts — indistinguishable from
nothing. **k=20 is the real operating point**, and that is 60 model calls per
input rather than 30.

**A severity floor exists and it is high.** A 0.3 mode-share shift is
undetectable at every k tested, reaching only 0.21 at k=40. Below roughly a
0.5 shift this statistic has nothing to say, and that belongs in the blind-spot
map next to the 10%-retrieval-noise floor (BCH-004).

**Failure is all-or-nothing per run.** Power at k=10 / severity 0.6 across five
seeds was [0.0, 0.0, 0.55, 0.0, 0.325]: either a qualifying threshold exists or
none does. Averaging across runs hides that a given run may return nothing at
all, so a single deployment's result should be read as a draw from this, not as
a point estimate.

**Re-measured 2026-10-16 on the tie-consistent estimator** (ENG-010; same
protocol, seeds 100 to 104, today's stub, which the 2026-09-24 sweep's seeds do
not reproduce to the digit either way). Before and after the fix on the same
seeds: k=10 severity 0.9 0.78 to 0.77; k=20 severity 0.6 0.785 to 0.71; k=20
severity 0.9 0.99 to 0.985; k=40 severity 0.3 0.145 to 0.14; the other five
cells unchanged. Realised FDR, mean of five seeds, is at or below 0.092 in
every cell after the fix (0.100 before). All three conclusions above stand;
the test asserts the gaps, not the figures (MTH-018 amendment).

## Known gaps

- Exact-match modes only. Semantic clustering for free text is the blocker on
  applying any of this to prose.
- The envelope was measured on one perturbation type (`mode_share`). Add-mode
  and collapse are implemented in the stub and not yet swept.
- No stratification yet. Thresholds are global; probes.md showed the NLI
  channel needs shape-stratified thresholds spanning a factor of eighty, and
  the same will apply here.
