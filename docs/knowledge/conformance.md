# Induced structural conformance — current state

`src/aprime/conformance.py`. The one mechanism the landscape survey found
unoccupied (STD-003).

Rules about a system's output are **induced from what it actually produces**,
never hand-written. Hand-authored schemas remain available as an override; they
are not the default, because a detector that requires a schema per customer is
a detector that does not scale past the first customer.

## Ancestry and the problem inherited with it

The right ancestor is Daikon (2001), which watched a program run and inferred
the invariants its variables obeyed. Nobody has ported that to LLM output
distributions.

Daikon's well-known failure is over-generation: fit rules tightly to observed
data and you get far more candidates than a human can triage, most true by
coincidence. Two mechanisms cut that from both sides.

### The decoy arm prunes coincidence

Every induced rule is re-checked against A_prime — an independent re-run of the
*same* system. A rule that holds on A and breaks on A_prime was never
structural; it was an accident of one sample.

This is the decoy arm doing a second job beyond FDR calibration, at no extra
cost, because those samples already exist. It is also the piece that connects
the two mechanisms the landscape survey called unoccupied and unclaimed into one
machine.

### The middle band puts the human where the data is undecided

| Support on A **and** A_prime | Treatment |
|---|---|
| ≥ `hard_min` (default 0.99) | Hard invariant. Enforced, no human involved. |
| `band_lo`–`hard_min` (default 0.60–0.99) | Surfaced: "holds 87% of the time — rule or variation?" |
| < `band_lo` | Discarded silently. |

A rule clearing `hard_min` on the baseline but failing on the decoy is
**demoted to the band, not discarded** — the data says something is going on,
just not that it is an invariant.

The human never sees a thousand candidates. They answer a few dozen questions
the system has already established are worth asking.

## Rule kinds, and why each exists

Every kind maps to a documented fault class in the frozen taxonomy. These are
not invented checks; they are checks for things that have actually broken.

| Rule | Fault class | What it caught in the wild |
|---|---|---|
| `parses_json`, `json_key_present`, `json_key_type`, `json_enum` | F3 | LinkedIn measured schema errors at ~10%, cut to ~0.01% by a defensive parser |
| `script_subset`, `no_unicode_escape`, `no_control_chars` | F7 | Thai characters in English replies (Anthropic TPU); raw `\uXXXX` instead of CJK glyphs (OpenRouter FP4) |
| `ends_with_terminator` | F12 | Output-side truncation, whose signature is a mid-sentence stop |
| `no_refusal_marker` | F13 | Refusal drift |
| `word_count_range`, `line_count_range` | F10, F12 | Truncation of either kind |

**Nothing here reads meaning.** That is the point: this channel covers failures
the semantic channels structurally cannot see. F7 in particular is invisible to
contradiction and to entailment — a corrupted character is not a claim.

## Design notes

**Rules are fitted tight, Daikon-style.** A range fitted exactly to the observed
minimum and maximum is the strongest claim the data supports. Guessing a safety
margin up front would be inventing a number; letting the decoy knock down the
coincidental ones is cheaper and more honest. Ranges rarely survive as hard
invariants, and that is informative rather than a defect.

**Only keys present in every baseline object become candidates.** A key seen in
90% of outputs is a band question, not an invariant.

**The refusal pattern is deliberately narrow.** A broad list fires on ordinary
hedging and turns F13 into noise; there is a test asserting it does not fire on
*"Based on the information available…"* or on *"I cannot confirm the amount
without the invoice."*

**Only hard invariants are enforced at check time.** Firing automatically on
band rules would reintroduce exactly the over-generation the band prevents.

## Known limits

- Never run inside the detector on real outputs. All figures so far are from
  unit tests with synthetic corpora.
- No per-input rules. Everything is corpus-level — the system's output contract,
  not "for this input the answer always mentions 42,000". Per-input induction is
  plausible at k=20 and untried.
- `script_subset` will misfire on genuinely multilingual systems. It needs the
  baseline to establish the language mix, which it does, but a system that
  legitimately switches language per input will produce a permissive rule that
  catches nothing.
- Enum induction caps at 6 distinct values, which is a guess, not a measurement.
