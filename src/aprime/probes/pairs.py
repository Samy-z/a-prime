"""Probe pair construction.

A probe pair is two texts plus a known ground-truth relation between them:

    PRESERVING  the two texts mean the same thing; a channel that scores this
                pair as "changed" is producing a false alarm
    BREAKING    the two texts differ in a way that would matter to whoever
                reads the output; a channel that scores this pair as "unchanged"
                is blind

Both arms of every pair are produced by the same renderer from the same seed,
so the only difference between them is the intended one. Preserving
perturbations vary the rendering and hold the facts fixed; breaking
perturbations vary the facts and hold the rendering fixed.

This asymmetry is deliberate and is the whole point: it is exactly the
situation a regression detector faces in production, where a model swap
rewrites the surface of every output while changing the substance of a few.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable, Literal

from .seeds import SEEDS, Seed

Shape = Literal["short_answer", "json", "summary", "reasoning"]
Relation = Literal["PRESERVING", "BREAKING"]

SHAPES: tuple[Shape, ...] = ("short_answer", "json", "summary", "reasoning")

# Meaning-preserving lexical swaps, one per seed, each targeting a phrase in
# that seed's `detail1`.
#
# Targeting detail1 is deliberate: it is the only content field rendered by all
# four shapes, including JSON, where template-level connectives do not survive.
# An earlier version keyed the swaps on template wording and silently became a
# no-op on JSON — a broken probe and a blind channel are indistinguishable in
# the results table, which is why test_synonym_actually_substitutes_something
# exists.
#
# Exactly one phrase changes per pair, which makes this the minimum-dose
# preserving perturbation: it sets the floor of what any channel must ignore.
SYNONYMS: dict[str, str] = {
    "sits within": "falls within",                    # bank_01
    "nine-year history": "nine-year record",          # bank_02
    "holds two existing": "has two existing",         # bank_03
    "submitted through": "filed through",             # bank_04
    "The vessel": "The ship",                         # logi_01
    "Driver hours fit": "Driver hours stay",          # logi_02
    "was recertified": "was re-approved",             # logi_03
    "confirmed against": "booked against",            # logi_04
    "matches the original": "corresponds to the original",  # hosp_01
    "made through the direct": "placed through the direct",  # hosp_02
    "step-free access": "level access",               # hosp_03
    "includes two children": "contains two children",  # hosp_04
    "stayed below": "remained below",                 # tech_01
    "ran to completion": "ran to the end",            # tech_02
    "runs inside": "runs within",                     # tech_03
    "resolves to": "chains to",                       # tech_04
}

HEDGE = "Based on the information available at the time of review, "


@dataclass(frozen=True)
class Pair:
    seed_id: str
    domain: str
    shape: Shape
    category: str
    relation: Relation
    text_a: str
    text_b: str

    @property
    def words_a(self) -> int:
        return len(self.text_a.split())


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------


def _cap(s: str) -> str:
    return s[0].upper() + s[1:] if s else s


def _render_short(f: dict[str, str], v: int, swap: bool, hedge: bool, drop: bool) -> str:
    d1, d2 = (f["detail2"], f["detail1"]) if swap else (f["detail1"], f["detail2"])
    tail = "" if drop else " " + f["caveat"]
    if v == 0:
        body = (
            f"{_cap(f['action'])} for {f['subject']}: {f['number']} {f['unit']}, "
            f"{f['verdict']} as of {f['date']}. Requirements reviewed: "
            f"{f['quantifier']}. {d1}{tail}"
        )
    else:
        body = (
            f"{f['subject']} — {f['action']}, {f['number']} {f['unit']}: "
            f"{f['verdict']} ({f['date']}). Requirements reviewed: "
            f"{f['quantifier']}. {d1}{tail}"
        )
    return (HEDGE + body[0].lower() + body[1:]) if hedge else body


def _render_summary(f: dict[str, str], v: int, swap: bool, hedge: bool, drop: bool) -> str:
    d1, d2 = (f["detail2"], f["detail1"]) if swap else (f["detail1"], f["detail2"])
    tail = "" if drop else " " + f["caveat"]
    # The framing sentences below carry no perturbable content and are identical
    # in both arms. That is deliberate: they are the dilution the summary shape
    # is here to supply. A one-word factual change inside 150 words of shared
    # prose is the realistic hard case, and a channel that only works on short
    # outputs needs to be caught saying so.
    if v == 0:
        body = (
            f"This note records the outcome of the {f['action']} raised for "
            f"{f['subject']}, together with the reasoning behind it. The review "
            f"followed the standard assessment path, and no expedited handling "
            f"was requested by any party at any point in the process. Supporting "
            f"documentation was read in full before a determination was reached. "
            f"The request covering {f['number']} {f['unit']} was {f['verdict']} "
            f"as of {f['date']}. {d1} {d2} Where figures appear here they are "
            f"taken from the source system as it stood at the time of review, "
            f"and they have not been restated since. On that basis "
            f"{f['quantifier']} of the stated requirements are met, and the "
            f"position therefore remains as described above. This record is "
            f"intended for internal reference and supersedes any earlier draft "
            f"circulated on the same matter.{tail}"
        )
    else:
        body = (
            f"Summarised below is the outcome of the {f['action']} concerning "
            f"{f['subject']}, along with the reasoning that supports it. The "
            f"assessment ran through the usual path, and at no stage did any "
            f"party ask for expedited handling. All supporting material was "
            f"reviewed in full ahead of the determination. Effective "
            f"{f['date']}, the request spanning {f['number']} {f['unit']} was "
            f"{f['verdict']}. {d1} {d2} Figures given here reflect the source "
            f"system as of the review date and have not been restated in the "
            f"interim. This indicates that {f['quantifier']} of the stated "
            f"requirements are satisfied, and accordingly the position stays as "
            f"set out. The note is for internal reference and replaces any "
            f"earlier draft issued on the same matter.{tail}"
        )
    return (HEDGE + body[0].lower() + body[1:]) if hedge else body


def _render_reasoning(f: dict[str, str], v: int, swap: bool, hedge: bool, drop: bool) -> str:
    d1, d2 = (f["detail2"], f["detail1"]) if swap else (f["detail1"], f["detail2"])
    tail = "" if drop else f"\n5. Note: {f['caveat']}"
    if v == 0:
        body = (
            f"1. The {f['action']} concerns {f['subject']}, as of {f['date']}.\n"
            f"2. {d1}\n"
            f"3. {d2}\n"
            f"4. Taken together, {f['quantifier']} of the criteria are met "
            f"across {f['number']} {f['unit']}, so the outcome is "
            f"{f['verdict']}.{tail}"
        )
    else:
        body = (
            f"1. Subject of the {f['action']}: {f['subject']}, effective "
            f"{f['date']}.\n"
            f"2. {d1}\n"
            f"3. {d2}\n"
            f"4. Reading these together, {f['quantifier']} of the criteria hold "
            f"over {f['number']} {f['unit']}, and the outcome is therefore "
            f"{f['verdict']}.{tail}"
        )
    return (HEDGE + body[0].lower() + body[1:]) if hedge else body


def _render_json(
    f: dict[str, str], v: int, swap: bool, hedge: bool, drop: bool, compact: bool
) -> str:
    d1, d2 = (f["detail2"], f["detail1"]) if swap else (f["detail1"], f["detail2"])
    if v == 0:
        obj: dict[str, object] = {
            "subject": f["subject"],
            "action": f["action"],
            "quantity": f["number"],
            "unit": f["unit"],
            "status": f["verdict"],
            "effective": f["date"],
            "coverage": f["quantifier"],
            "findings": [d1, d2],
        }
    else:
        obj = {
            "entity": f["subject"],
            "request_type": f["action"],
            "amount": f["number"],
            "measure": f["unit"],
            "outcome": f["verdict"],
            "as_of": f["date"],
            "scope": f["quantifier"],
            "observations": [d1, d2],
        }
    if not drop:
        obj["condition"] = f["caveat"]
    if hedge:
        obj["note"] = "Based on the information available at the time of review."
    if compact:
        return json.dumps(obj, separators=(",", ":"), sort_keys=True)
    return json.dumps(obj, indent=2)


def _as_bullets(text: str) -> str:
    """Re-present prose as a markdown bullet list, changing nothing else.

    This is the `format` perturbation for prose shapes. Collapsing whitespace
    was the first attempt and was a no-op on single-line output, so the
    perturbation silently measured nothing — the same class of bug as the
    synonym map. Reformatting is also the more realistic change: swapping
    models routinely alters presentation habits while leaving content intact.
    """
    if "\n" in text:
        lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
        return "\n".join("- " + re.sub(r"^\d+\.\s*", "", ln) for ln in lines)
    parts = [p for p in re.split(r"(?<=[.!?])\s+", text.strip()) if p]
    return "\n".join("- " + p for p in parts)


def render(
    shape: Shape,
    f: dict[str, str],
    variant: int = 0,
    *,
    swap_details: bool = False,
    hedge: bool = False,
    drop_caveat: bool = False,
    compact: bool = False,
) -> str:
    if shape == "json":
        return _render_json(f, variant, swap_details, hedge, drop_caveat, compact)
    text = {
        "short_answer": _render_short,
        "summary": _render_summary,
        "reasoning": _render_reasoning,
    }[shape](f, variant, swap_details, hedge, drop_caveat)
    if compact:
        text = _as_bullets(text)
    return text


def synonymize(text: str) -> str:
    for a, b in SYNONYMS.items():
        text = text.replace(a, b)
    return text


# --------------------------------------------------------------------------
# perturbations
# --------------------------------------------------------------------------

Builder = Callable[[Shape, dict[str, str]], tuple[str, str]]


def _swap(f: dict[str, str], key: str) -> dict[str, str]:
    g = dict(f)
    g[key] = f[f"{key}_alt"]
    return g


PRESERVING: dict[str, Builder] = {
    "paraphrase": lambda s, f: (render(s, f, 0), render(s, f, 1)),
    "reorder": lambda s, f: (render(s, f, 0), render(s, f, 0, swap_details=True)),
    "format": lambda s, f: (render(s, f, 0), render(s, f, 0, compact=True)),
    "synonym": lambda s, f: (render(s, f, 0), synonymize(render(s, f, 0))),
    "verbosity": lambda s, f: (render(s, f, 0), render(s, f, 0, hedge=True)),
}

BREAKING: dict[str, Builder] = {
    "polarity": lambda s, f: (render(s, f, 0), render(s, _swap(f, "verdict"), 0)),
    "negation": lambda s, f: (render(s, f, 0), render(s, _swap(f, "detail1"), 0)),
    "number": lambda s, f: (render(s, f, 0), render(s, _swap(f, "number"), 0)),
    "entity": lambda s, f: (render(s, f, 0), render(s, _swap(f, "subject"), 0)),
    "quantifier": lambda s, f: (render(s, f, 0), render(s, _swap(f, "quantifier"), 0)),
    "temporal": lambda s, f: (render(s, f, 0), render(s, _swap(f, "date"), 0)),
    "unit": lambda s, f: (render(s, f, 0), render(s, _swap(f, "unit"), 0)),
    "omission": lambda s, f: (render(s, f, 0), render(s, f, 0, drop_caveat=True)),
}

CATEGORIES: dict[str, Relation] = {
    **{k: "PRESERVING" for k in PRESERVING},
    **{k: "BREAKING" for k in BREAKING},
}


def build_pairs(seeds: list[Seed] | None = None) -> list[Pair]:
    """Full factorial: seed x shape x category."""
    seeds = SEEDS if seeds is None else seeds
    out: list[Pair] = []
    for seed in seeds:
        for shape in SHAPES:
            for name, builder in {**PRESERVING, **BREAKING}.items():
                a, b = builder(shape, seed.fields)
                out.append(
                    Pair(
                        seed_id=seed.id,
                        domain=seed.domain,
                        shape=shape,
                        category=name,
                        relation=CATEGORIES[name],
                        text_a=a,
                        text_b=b,
                    )
                )
    return out


def degenerate(pairs: list[Pair]) -> list[Pair]:
    """Pairs whose two arms are byte-identical.

    Any such pair is a construction bug, not a finding: a preserving pair with
    no surface difference measures nothing, and a breaking pair with no
    difference at all is not breaking. The suite must report zero of these
    before any result derived from it is trusted.
    """
    return [p for p in pairs if p.text_a == p.text_b]
