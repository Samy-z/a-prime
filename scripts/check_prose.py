"""Report readability signals for an outward-facing document.

A report, never a gate. Every number here is advisory and a document can have a
good reason to break any of them. But this project measures things rather than
asserting they improved, and prose is no exception.

    python scripts/check_prose.py README.md
    python scripts/check_prose.py README.md --jargon-file docs/reader/jargon.txt

What it looks for comes from docs/reader/METHODS.md: the habits that read as
machine-written, and the failure the `reader` seat exists to catch, which is
using a term the writer has internalised and the reader has never seen.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Terms that mean nothing to a stranger unless the document defines them. Not an
# exhaustive list of hard words; a list of *this project's* vocabulary plus the
# statistics and ML terms it leans on.
JARGON = {
    "FDR": "false discovery rate",
    "false-discovery rate": "the share of flagged items that are not real changes",
    "null distribution": "what the scores look like when nothing changed",
    "NLI": "natural language inference",
    "entailment": "whether one text follows from another",
    "mode-share": "how often each distinct answer appears",
    "decoy": "a comparison where nothing changed, used as a baseline",
    "probe pairs": "hand-built text pairs with a known relationship",
    "separability": "how well a score tells two groups apart",
    "AUC": "area under the ROC curve",
    "logprobs": "the model's internal token probabilities",
    "Daikon": "a 2001 tool that inferred rules from program runs",
    "conformance": "checking output against rules inferred from the baseline",
    "stratified": "grouped, with a separate threshold per group",
    "dedup": "removing duplicate inputs",
    "metamorphic": "tests built from transformations that should not change output",
    "omission": "content present in the baseline and missing from the candidate",
    "anti-correlated": "moves in the opposite direction to what you want",
}

_CODE_FENCE = re.compile(r"```.*?```", re.DOTALL)
_INLINE = re.compile(r"`[^`]*`")
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_TABLE = re.compile(r"^\s*\|.*$", re.MULTILINE)
_HEADING = re.compile(r"^#{1,6}\s.*$", re.MULTILINE)
_BOLD = re.compile(r"\*\*[^*]+\*\*")
_EMPH = re.compile(r"\*{1,2}")
_SENT = re.compile(r"(?<=[.!?])\s+")
_ID = re.compile(r"\b(?:MTH|BCH|STD|ENG|RDR)-\d+\b|\bF\d{1,2}\b")


def prose_only(text: str) -> str:
    """Strip everything that is not running prose."""
    t = _CODE_FENCE.sub(" ", text)
    t = _TABLE.sub(" ", t)
    t = _HEADING.sub(" ", t)
    t = _LINK.sub(r"\1", t)
    t = _INLINE.sub(" ", t)
    # Emphasis markers sit between a term and its gloss, so they defeat the
    # adjacency test in defined_nearby: "**AUC**, area under the curve" looks
    # like it is followed by an asterisk rather than a comma. Stripped here for
    # analysis; bold is counted separately, from the raw text.
    t = _EMPH.sub("", t)
    return t


def _boundary(term: str) -> str:
    """Match a term as a whole word.

    Without this, "NLI" matches inside "DeBERTa-v3-base-MNLI" and the term is
    reported as undefined in a document that never uses the acronym at all.
    """
    lead = r"(?<![\w-])" if term[:1].isalnum() else ""
    trail = r"(?![\w-])" if term[-1:].isalnum() else ""
    return lead + re.escape(term) + trail


def defined_nearby(text: str, term: str) -> bool:
    """Is the term glossed immediately where it first appears?

    Deliberately strict. An earlier version accepted any of `is`, `:` or `(`
    within 240 characters, which matches almost any prose and passed a document
    with twenty undefined terms. A gloss has to be *adjacent* to the term, not
    merely somewhere in the same paragraph.

    Accepts four shapes, all of which put the explanation next to the word:
        term (explanation)
        term, the explanation
        term -- explanation        (em dash or double hyphen)
        term is/means explanation
    Plus a parenthetical expansion before an acronym: explanation (TERM).
    """
    m = re.search(_boundary(term), text, re.IGNORECASE)
    if not m:
        return True
    tail = text[m.end() : m.end() + 90]
    if re.match(r"\s*[\(\[]", tail):
        return True
    # "term, the explanation" / "term, which means ..." -- a determiner or
    # relative pronoun after the comma marks a gloss rather than a list.
    if re.match(r",\s+(?:the|which|meaning|a|an)\b", tail):
        return True
    # Appositive: "AUC, area under the curve, is ..." -- a short phrase fenced
    # by commas immediately after the term.
    if re.match(r",\s+[^,.;:]{3,60},", tail):
        return True
    # Deliberately NOT accepted: a dash. "null distribution -- measured on your
    # corpus" is an aside, not a definition, and dashes are used for asides
    # constantly. Accepting them made this function pass a document with eleven
    # undefined terms. This check errs toward flagging on purpose: a false alarm
    # costs a reader thirty seconds, a false pass ships a cryptic document.
    if re.match(r"\s+(?:is|are|means|stands for|refers to)\s+\w", tail):
        return True
    # "term: the explanation" -- a colon introduces a gloss as readably as a
    # comma does, and leaving it out flagged correctly-defined terms.
    if re.match(r"\s*:\s+\w", tail):
        return True
    # "natural language inference (NLI)" -- expansion precedes the acronym.
    head = text[max(0, m.start() - 70) : m.start()]
    if re.search(r"[\w\s]{6,}\s*\($", head):
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--em-dash-per-1000", type=float, default=3.3,
                    help="advisory ceiling, ~1 per 300 words")
    args = ap.parse_args()

    raw = Path(args.path).read_text(encoding="utf-8")
    prose = prose_only(raw)
    words = prose.split()
    n_words = len(words)
    if not n_words:
        print("no prose found")
        return 0

    print(f"{args.path}: {len(raw.splitlines())} lines, {n_words} words of prose\n")

    em = prose.count("—")
    rate = em / n_words * 1000
    verdict = "ok" if rate <= args.em_dash_per_1000 else "HIGH"
    print(f"em dashes          {em:>4}   {rate:>5.1f} per 1000 words   [{verdict}]"
          f"  (target <= {args.em_dash_per_1000})")

    sents = [s for s in (x.strip() for x in _SENT.split(prose)) if len(s.split()) > 2]
    lens = sorted(len(s.split()) for s in sents)
    if lens:
        short = sum(1 for x in lens if x < 8)
        long_ = sum(1 for x in lens if x > 35)
        med = lens[len(lens) // 2]
        print(f"sentences          {len(lens):>4}   median {med} words, "
              f"{short} under 8 ({short/len(lens):.0%}), {long_} over 35 "
              f"({long_/len(lens):.0%})")
        print(f"                          [{'ok' if short/len(lens) < 0.15 else 'MANY FRAGMENTS'}]"
              f" target: most sentences 15-25 words")

    bold = len(_BOLD.findall(raw))
    print(f"bold spans         {bold:>4}   {bold / n_words * 1000:>5.1f} per 1000 words"
          f"   [{'ok' if bold / n_words * 1000 <= 12 else 'HEAVY'}]")

    ids = _ID.findall(raw)
    print(f"internal ids       {len(ids):>4}   {sorted(set(ids)) if ids else '(none)'}")
    if ids:
        print("                          these must be pointers after a plain-words "
              "explanation, never the explanation")

    print("\nterms used without an explanation nearby:")
    missing = []
    for term, gloss in sorted(JARGON.items()):
        if re.search(_boundary(term), prose, re.IGNORECASE) and not defined_nearby(prose, term):
            missing.append((term, gloss))
    if not missing:
        print("  none found")
    else:
        for term, gloss in missing:
            print(f"  {term:<22} -> {gloss}")
    print(f"\n{len(missing)} undefined term(s). Advisory: this is a report, not a gate.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
