"""Are the three output formats actually three different shapes?

`shape_ok` in the smoke script measures **compliance**: did the model produce
the form its format demanded. That is not the question the study rests on.

The grid is three domains by three output formats, and the detector fits a
separate threshold per output shape. That only buys anything if the three
formats really do produce three different shapes. A format that quietly emits the
same prose paragraphs as another costs the study an axis whether or not it
obeys its own rule, and it does so silently: every cell still runs, every
count still looks plausible.

So this asks the other question. Reads the saved outputs from a smoke run and
reports, per format, what the outputs look like and how far apart they are.
No model, no GPU.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECISIONS = ("APPROVE", "DECLINE", "ESCALATE")


def profile(texts: list[str]) -> dict:
    words = [len(t.split()) for t in texts if t.strip()]
    if not words:
        return {"n": 0}
    return {
        "n": len(words),
        "median_words": statistics.median(words),
        "min_words": min(words),
        "max_words": max(words),
        "starts_json": sum(t.strip().startswith("{") for t in texts),
        "parses_as_json": sum(_is_json(t) for t in texts),
        "leads_with_decision": sum(
            t.strip().upper().startswith(DECISIONS) for t in texts),
        "contains_decision": sum(
            any(d in t.upper() for d in DECISIONS) for t in texts),
        "multi_sentence": sum(t.count(".") >= 3 for t in texts),
    }


def _is_json(t: str) -> bool:
    s = t.strip()
    try:
        return isinstance(json.loads(s[s.index("{"): s.rindex("}") + 1]), dict)
    except (ValueError, TypeError):
        return False


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "results" / "cells_smoke.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data["rows"]
    if not any("outputs" in r for r in rows):
        print(f"{path.name} holds counts but no outputs. Re-run "
              f"scripts/smoke_cells.py to save them.")
        return 1

    print(f"{path.name}, model {data.get('model')}\n")
    by_fmt: dict[str, list[str]] = {}
    for r in rows:
        # Runs recorded before the rename carry "mode" for this.
        key = r.get("format") or r["mode"]
        by_fmt.setdefault(key, []).extend(
            o["output"] for o in r.get("outputs", []))

    hdr = (f"{'format':<12}{'n':>4}{'words':>16}{'json':>7}{'leads':>7}"
           f"{'has':>6}{'3+ sent':>9}")
    print(hdr)
    print("-" * len(hdr))
    profs = {}
    for fmt, texts in by_fmt.items():
        p = profs[fmt] = profile(texts)
        span = f"{p['median_words']} ({p['min_words']}-{p['max_words']})"
        print(f"{fmt:<12}{p['n']:>4}{span:>16}{p['parses_as_json']:>7}"
              f"{p['leads_with_decision']:>7}{p['contains_decision']:>6}"
              f"{p['multi_sentence']:>9}")

    print("\njson      = output parses as a JSON object")
    print("leads/has = begins with / contains APPROVE, DECLINE or ESCALATE")
    print("3+ sent   = three or more sentences, i.e. a paragraph not a line")

    a, s = profs.get("agent"), profs.get("summary")
    if a and s and a["n"] and s["n"]:
        # Length alone is a poor separator, and an earlier version of this
        # script used it alone with an invented 0.6 multiplier. It returned
        # "not distinct" on a run where the decision token separated the two
        # modes completely, which is the opposite of what the evidence said.
        # Presence of a decision is the discriminative feature; length only
        # corroborates it.
        sep = (a["contains_decision"] / a["n"]) - (s["contains_decision"] / s["n"])
        print("\nagent vs summary")
        print(f"  decision token present  {a['contains_decision']:>3}/{a['n']:<3}"
              f" vs {s['contains_decision']:>3}/{s['n']:<3} separation {sep:+.2f}")
        print(f"  median words            {a['median_words']:>7} "
              f"vs {s['median_words']:>7}")
        print(f"  paragraphs              {a['multi_sentence']:>3}/{a['n']:<3}"
              f" vs {s['multi_sentence']:>3}/{s['n']:<3}")
        print(f"  spread, words           {str(a['min_words'])+'-'+str(a['max_words']):>7} "
              f"vs {str(s['min_words'])+'-'+str(s['max_words']):>7}")

        if sep >= 0.5:
            print("\nVERDICT: the two modes are shape-distinct. A decision "
                  "token appears in one\nand not the other, which separates "
                  "them more cleanly than length does.")
            if a["leads_with_decision"] < a["n"] / 2:
                print("\n  Distinct is not the same as compliant. The decision "
                      "usually arrives at\n  the END of the output. The format "
                      "rule asks for a short line beginning\n  with the "
                      "decision; what it gets is a paragraph of reasoning with "
                      "the\n  decision appended.")
            if a["max_words"] > 4 * s["median_words"]:
                print("\n  The spread is its own problem. A format whose outputs "
                      "run from a clause to\n  several paragraphs gives a "
                      "shape-stratified threshold very little to\n  hold on to.")
        else:
            print("\nVERDICT: no clean separation. The third arm of the grid "
                  "is not doing the\nwork the design assigns it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
