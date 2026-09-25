"""Induced structural conformance.

Rules about a system's output are **induced from what it actually produces**,
not written by hand. Nothing in the tooling landscape does this (STD-003); the
nearest ancestor is Daikon, which watched a program run and inferred the
invariants its variables obeyed, and which nobody has ported to LLM outputs.

## The failure mode we inherit, and the fix

Daikon's well-known problem is over-generation: fit rules tightly to observed
data and you get far more candidates than a human can triage, most of them true
by coincidence. Two mechanisms cut that from both sides.

**The decoy arm prunes coincidence.** Every rule induced from the baseline is
re-checked against A_prime — an independent re-run of the *same* system. A rule
that holds on A and breaks on A_prime was never structural; it was an accident
of one sample. This is the decoy arm doing a second job beyond FDR calibration,
and it costs nothing extra because the samples already exist.

**The middle band puts the human where the data is genuinely undecided.**
Rules split three ways rather than two:

| Support on A *and* A_prime | Treatment |
|---|---|
| at or above `hard_min` | Hard invariant. Enforced, no human involved. |
| `band_lo` to `hard_min` | Surfaced: "this holds 87% of the time — rule or variation?" |
| below `band_lo` | Discarded silently. |

The human is never handed a thousand candidates. They answer a few dozen
questions the system has already established are worth asking.

## What the rules check

Every rule kind here corresponds to a documented fault class in the frozen
taxonomy. These are not invented checks — they are checks for things that have
actually broken in production:

- JSON validity, key presence, value types, enum domains — F3 (tool surface
  change), where LinkedIn measured schema errors from ~10% down to ~0.01%
- script and charset consistency, literal unicode escapes — F7, where three
  unrelated causes (TPU misconfiguration, quantization, compiler bug) all
  surfaced as character-level corruption
- output termination — F12 (output-side truncation), whose signature is a
  mid-sentence stop
- refusal markers — F13 (refusal drift)
- length bounds — F10 and F12

Nothing here reads meaning. That is the point: this channel covers the failures
the semantic channels structurally cannot see.
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Sequence

# Lexical refusal signature. Deliberately narrow: a broad list would fire on
# ordinary hedging and turn F13 into noise.
_REFUSAL = re.compile(
    r"\b(i (?:can(?:no|')t|am unable to|won'?t) (?:help|assist|provide|comply)"
    r"|as an ai\b|i'?m sorry,? but\b)",
    re.IGNORECASE,
)
_UNICODE_ESCAPE = re.compile(r"\\u[0-9a-fA-F]{4}")
_TERMINATOR = re.compile(r"[.!?\"')\]}…]\s*$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def script_families(text: str) -> frozenset[str]:
    """Unicode script families present, ignoring punctuation and digits.

    The F7 signature is Thai or Chinese characters appearing in an English
    response, or CJK arriving as raw escapes. Both are visible here without any
    idea what the text says.
    """
    fams: set[str] = set()
    for ch in text:
        if not ch.isalpha():
            continue
        try:
            name = unicodedata.name(ch)
        except ValueError:
            fams.add("UNKNOWN")
            continue
        fams.add(name.split()[0])
    return frozenset(fams)


# --------------------------------------------------------------------------
# rules
# --------------------------------------------------------------------------

_CHECKS: dict[str, Callable[[str, tuple], bool]] = {}


def _check(kind: str):
    def deco(fn):
        _CHECKS[kind] = fn
        return fn

    return deco


@_check("parses_json")
def _parses_json(out: str, _p: tuple) -> bool:
    try:
        json.loads(out)
        return True
    except (ValueError, TypeError):
        return False


@_check("json_key_present")
def _json_key(out: str, p: tuple) -> bool:
    try:
        obj = json.loads(out)
    except (ValueError, TypeError):
        return False
    return isinstance(obj, dict) and p[0] in obj


@_check("json_key_type")
def _json_key_type(out: str, p: tuple) -> bool:
    key, tname = p
    try:
        obj = json.loads(out)
    except (ValueError, TypeError):
        return False
    if not isinstance(obj, dict) or key not in obj:
        return False
    return type(obj[key]).__name__ == tname


@_check("json_enum")
def _json_enum(out: str, p: tuple) -> bool:
    key, allowed = p
    try:
        obj = json.loads(out)
    except (ValueError, TypeError):
        return False
    if not isinstance(obj, dict) or key not in obj:
        return False
    return str(obj[key]) in allowed


@_check("word_count_range")
def _wc(out: str, p: tuple) -> bool:
    return p[0] <= len(out.split()) <= p[1]


@_check("line_count_range")
def _lc(out: str, p: tuple) -> bool:
    return p[0] <= len(out.splitlines()) <= p[1]


@_check("script_subset")
def _script(out: str, p: tuple) -> bool:
    return script_families(out) <= frozenset(p[0])


@_check("no_unicode_escape")
def _no_esc(out: str, _p: tuple) -> bool:
    return _UNICODE_ESCAPE.search(out) is None


@_check("no_control_chars")
def _no_ctrl(out: str, _p: tuple) -> bool:
    return _CONTROL.search(out) is None


@_check("no_refusal_marker")
def _no_refusal(out: str, _p: tuple) -> bool:
    return _REFUSAL.search(out) is None


@_check("ends_with_terminator")
def _terminated(out: str, _p: tuple) -> bool:
    s = out.rstrip()
    return bool(s) and bool(_TERMINATOR.search(s))


@_check("nonempty")
def _nonempty(out: str, _p: tuple) -> bool:
    return bool(out.strip())


@dataclass(frozen=True)
class Rule:
    kind: str
    params: tuple = ()
    fault_class: str = ""

    def holds(self, output: str) -> bool:
        return _CHECKS[self.kind](output, self.params)

    def support(self, outputs: Sequence[str]) -> float:
        if not outputs:
            return 0.0
        return sum(self.holds(o) for o in outputs) / len(outputs)

    def __str__(self) -> str:
        p = f"({', '.join(map(str, self.params))})" if self.params else ""
        tag = f" [{self.fault_class}]" if self.fault_class else ""
        return f"{self.kind}{p}{tag}"


# --------------------------------------------------------------------------
# induction
# --------------------------------------------------------------------------


def candidate_rules(outputs: Sequence[str], max_enum: int = 6) -> list[Rule]:
    """Propose the tightest rules consistent with the baseline.

    Tight by design, Daikon-style: a range fitted exactly to what was observed
    is the strongest claim the data supports, and letting the decoy arm knock
    down the coincidental ones is cheaper and more honest than guessing a margin
    up front. Ranges in particular rarely survive, and that is informative
    rather than a defect.
    """
    if not outputs:
        return []
    rules: list[Rule] = [
        Rule("nonempty", (), "F3"),
        Rule("no_control_chars", (), "F7"),
        Rule("no_unicode_escape", (), "F7"),
        Rule("no_refusal_marker", (), "F13"),
        Rule("ends_with_terminator", (), "F12"),
    ]

    wc = [len(o.split()) for o in outputs]
    rules.append(Rule("word_count_range", (min(wc), max(wc)), "F10/F12"))
    lc = [len(o.splitlines()) for o in outputs]
    rules.append(Rule("line_count_range", (min(lc), max(lc)), "F12"))

    fams = frozenset().union(*(script_families(o) for o in outputs))
    if fams:
        rules.append(Rule("script_subset", (tuple(sorted(fams)),), "F7"))

    parsed = []
    for o in outputs:
        try:
            parsed.append(json.loads(o))
        except (ValueError, TypeError):
            parsed.append(None)
    if any(isinstance(x, dict) for x in parsed):
        rules.append(Rule("parses_json", (), "F3"))
        dicts = [x for x in parsed if isinstance(x, dict)]
        keys = Counter(k for d in dicts for k in d)
        for key, n in keys.items():
            if n < len(dicts):
                continue  # only keys seen in every object are candidates
            rules.append(Rule("json_key_present", (key,), "F3"))
            types = {type(d[key]).__name__ for d in dicts}
            if len(types) == 1:
                rules.append(Rule("json_key_type", (key, types.pop()), "F3"))
            vals = {str(d[key]) for d in dicts}
            if 1 < len(vals) <= max_enum:
                rules.append(Rule("json_enum", (key, tuple(sorted(vals))), "F3"))
    return rules


@dataclass
class InducedContract:
    hard: list[Rule] = field(default_factory=list)
    band: list[tuple[Rule, float, float]] = field(default_factory=list)
    discarded: list[tuple[Rule, float]] = field(default_factory=list)
    pruned_by_decoy: list[tuple[Rule, float]] = field(default_factory=list)
    n_baseline: int = 0
    n_decoy: int = 0

    @property
    def n_candidates(self) -> int:
        return (
            len(self.hard) + len(self.band) + len(self.discarded)
        )

    def summary(self) -> str:
        return (
            f"{self.n_candidates} candidates -> {len(self.hard)} hard, "
            f"{len(self.band)} surfaced, {len(self.discarded)} discarded "
            f"({len(self.pruned_by_decoy)} of those knocked down by the decoy arm)"
        )


def induce(
    baseline: Sequence[str],
    decoy: Sequence[str] | None = None,
    hard_min: float = 0.99,
    band_lo: float = 0.60,
) -> InducedContract:
    """Induce a contract from the baseline, pruned by the decoy.

    A rule reaches `hard` only if it clears `hard_min` on **both** arms. One
    that clears it on the baseline and fails on the decoy is demoted to the
    band, not discarded — the data says something is going on, just not that it
    is an invariant.
    """
    contract = InducedContract(n_baseline=len(baseline), n_decoy=len(decoy or []))
    for rule in candidate_rules(baseline):
        s_base = rule.support(baseline)
        s_decoy = rule.support(decoy) if decoy else s_base
        s_min = min(s_base, s_decoy)

        if s_base >= hard_min and s_decoy < hard_min:
            # Held on one sample of the system and not on another: coincidence,
            # which is exactly what the decoy arm is here to catch.
            contract.pruned_by_decoy.append((rule, s_decoy))

        if s_min >= hard_min:
            contract.hard.append(rule)
        elif s_min >= band_lo:
            contract.band.append((rule, s_base, s_decoy))
        else:
            contract.discarded.append((rule, s_min))
    return contract


@dataclass(frozen=True)
class Violation:
    rule: Rule
    rate: float
    n_violating: int
    n_total: int
    examples: tuple[str, ...] = ()


def check(
    contract: InducedContract,
    outputs: Sequence[str],
    max_examples: int = 3,
) -> list[Violation]:
    """Find hard invariants the candidate breaks.

    Only hard invariants are enforced. Band rules are questions for a human, and
    firing on them automatically would reintroduce the over-generation the band
    exists to prevent.
    """
    out: list[Violation] = []
    for rule in contract.hard:
        bad = [o for o in outputs if not rule.holds(o)]
        if bad:
            out.append(
                Violation(
                    rule=rule,
                    rate=len(bad) / len(outputs),
                    n_violating=len(bad),
                    n_total=len(outputs),
                    examples=tuple(b[:160] for b in bad[:max_examples]),
                )
            )
    return sorted(out, key=lambda v: -v.rate)
