"""The blind-spot map: what each check sees, drawn from probe runs already on disk.

The map answers one question per cell: at a fixed false-alarm budget, how often
does this check fire on this kind of change? Dark cells in the left block are
coverage; dark cells in the right block are false alarms. A light cell in the
left block is a blind spot, and the point of publishing the figure is that
those cells are shown rather than described.

Nothing here runs a model. Every number is recomputed from the scores the probe
runs stored, so the figure can be regenerated anywhere the repository is, and
so a reader who doubts a cell can trace it to a run id and a config hash.

Two conventions, both stated on the figure:

- One-tailed checks (contradiction, embedding distance) take their threshold at
  the 95th percentile of the preserving pairs, so they fire on 5% of pure
  rewordings by construction. The signed directional check is read at both
  ends, 2.5% per tail (MTH-022): the upper tail is information loss, the lower
  tail is information gain.
- The two runs made before register became its own class (MTH-021) labelled
  hedging as `verbosity` under PRESERVING. They are relabelled here, so every
  row sets its threshold over the same 256 preserving pairs and the columns
  mean the same thing on every row. The stored `results_global` in those files
  were computed over 320 preserving pairs and differ slightly; the
  reconciliation is a dated append under MTH-017.

The grid and the shipped block are kept apart on purpose. Every grid row comes
from the raw, un-normalised pair set, which both raw runs share byte for byte,
so the grid can be read across: DeBERTa against RoBERTa against the embeddings
on the same inputs under the same rule. The detector ships with normalisation
on, and MTH-019 measured that normalisation buys detection, so a normalised
DeBERTa row inside that grid would flatter DeBERTa against RoBERTa and a reader
would credit the model. The shipped rows therefore sit below the grid, labelled
as a different run, and the gap between them and the raw DeBERTa rows is
MTH-019 made visible.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from aprime.probes.analysis import wilson

# Column groups. The key is the category as the pair builder names it, the
# label is what the figure prints. Order within a group is the order of the
# figure, roughly easiest-to-see first.
BREAKING: tuple[tuple[str, str], ...] = (
    ("entity", "name swapped"),
    ("number", "number changed"),
    ("temporal", "date changed"),
    ("negation", "negation inserted"),
    ("polarity", "decision flipped"),
    ("quantifier", "quantifier changed"),
    ("unit", "unit changed"),
    ("omission", "condition deleted"),
)
REGISTER: tuple[tuple[str, str], ...] = (
    ("hedging", "hedge added"),
    ("overconfidence", "confidence added"),
)
PRESERVING: tuple[tuple[str, str], ...] = (
    ("paraphrase", "reworded"),
    ("synonym", "synonym swapped"),
    ("reorder", "sentences reordered"),
    ("format", "reformatted"),
)
COLUMN_GROUPS: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...] = (
    ("breaking", "a fact changed: should fire", BREAKING),
    ("register", "only the tone changed", REGISTER),
    ("preserving", "only the wording changed: should not fire", PRESERVING),
)

ONE_TAIL_BUDGET = 0.05
PER_TAIL_BUDGET = 0.025


@dataclass
class RowSpec:
    """One row of the map: a logical check read from one stored channel."""

    label: str
    detail: str
    group: str  # "detector" | "replication" | "rejected" in the grid; "shipped" below it
    source: str  # key into the sources dict
    channel: str  # key into that file's "channels"
    tail: str  # "upper" (score > threshold), "lower" (score < threshold)
    two_tailed: bool = False


# The reference runs. Each is named by run id and config hash in the output,
# so a figure regenerated from these files says which files it came from.
SOURCES: dict[str, str] = {
    "nli_norm": "probes_20260925T041059Z_norm-e984a64fd95bf2ad.json",
    "nli_raw": "probes_20260924T031004Z_592763f4f2a8c4d7.json",
    "emb_raw": "probes_20260924T022150Z_eb95f0b802c4660a.json",
}

ROWS: tuple[RowSpec, ...] = (
    # The grid: one pair set, raw text, every row under the same rule.
    RowSpec("contradiction", "DeBERTa-v3-base, raw text",
            "detector", "nli_raw", "deberta_mnli:contradiction", "upper"),
    RowSpec("information loss", "same model, signed entailment, upper tail",
            "detector", "nli_raw", "deberta_mnli:directional", "upper", True),
    RowSpec("information gain", "same model, signed entailment, lower tail",
            "detector", "nli_raw", "deberta_mnli:directional", "lower", True),
    RowSpec("contradiction", "RoBERTa-large, raw text",
            "replication", "nli_raw", "roberta_mnli:contradiction", "upper"),
    RowSpec("information loss", "RoBERTa-large, upper tail",
            "replication", "nli_raw", "roberta_mnli:directional", "upper", True),
    RowSpec("information gain", "RoBERTa-large, lower tail",
            "replication", "nli_raw", "roberta_mnli:directional", "lower", True),
    RowSpec("embedding distance", "MiniLM-L6, ungated",
            "rejected", "emb_raw", "minilm", "upper"),
    RowSpec("embedding distance", "BGE-base, ungated",
            "rejected", "emb_raw", "bge_base", "upper"),
    RowSpec("embedding distance", "E5-base, ungated",
            "rejected", "emb_raw", "e5_base", "upper"),
    # Below the grid: the configuration the detector ships with. A different
    # run and a larger pair set, so not read across against the rows above.
    RowSpec("contradiction", "DeBERTa-v3-base, text normalised first",
            "shipped", "nli_norm", "deberta_mnli:contradiction", "upper"),
    RowSpec("information loss", "same, upper tail",
            "shipped", "nli_norm", "deberta_mnli:directional", "upper", True),
    RowSpec("information gain", "same, lower tail",
            "shipped", "nli_norm", "deberta_mnli:directional", "lower", True),
)

GRID_GROUPS = ("detector", "replication", "rejected")

GROUP_TITLES = {
    "detector": "the detector's judging model",
    "replication": "a second judging model, same inputs",
    "rejected": "measured and rejected",
    "shipped": "as shipped: the same model after normalisation",
}

# Sizes below which nothing fired. These do not come from the probe suite and
# are not recomputed here; each names the ledger entry that measured it, and
# the figure carries them because a map of what is seen is misleading without
# the floor under it.
FLOORS: tuple[dict, ...] = (
    {"what": "a shift in how often the system picks each answer, below about 0.5 "
             "of the share, at 20 samples per arm",
     "seen_by": "nothing: 0% at every sample size tested for a 0.3 shift",
     "ref": "MTH-018"},
    {"what": "fewer than ten changed inputs in the test set, at a 10% false "
             "discovery budget",
     "seen_by": "nothing can be reported, by arithmetic, however clean the separation",
     "ref": "MTH-024"},
    {"what": "a twelve-word hedge inside a 150-word output",
     "seen_by": "no meaning check; a length rule caught it incidentally",
     "ref": "ENG-004"},
    {"what": "corrupted characters appended to an otherwise correct output",
     "seen_by": "no meaning check; only the structural rules",
     "ref": "ENG-004"},
    {"what": "10% of retrieved rows corrupted",
     "seen_by": "no downstream metric in published work; a miss is not scored "
                "against the detector",
     "ref": "BCH-004"},
)


@dataclass
class Cell:
    n: int
    fired: int
    rate: float
    lo: float
    hi: float


@dataclass
class Row:
    label: str
    detail: str
    group: str
    run_id: str
    config_hash: str
    channel: str
    hub_id: str
    revision: str
    tail: str
    budget: float
    threshold: float
    threshold_lower: float | None
    threshold_upper: float | None
    cells: dict[str, Cell | None] = field(default_factory=dict)


def _relabel(pairs: list[dict]) -> tuple[list[dict], bool]:
    """Apply MTH-021 to a run made before it: `verbosity` was hedging."""
    changed = False
    out = []
    for p in pairs:
        if p["category"] == "verbosity":
            p = {**p, "category": "hedging", "relation": "REGISTER"}
            changed = True
        out.append(p)
    return out, changed


def _load(results_dir: Path) -> dict[str, dict]:
    loaded = {}
    for key, name in SOURCES.items():
        d = json.loads((results_dir / name).read_text(encoding="utf-8"))
        pairs, relabelled = _relabel(d["pairs"])
        d["pairs"] = pairs
        d["_relabelled"] = relabelled
        loaded[key] = d
    return loaded


def _row(spec: RowSpec, src: dict) -> Row:
    ch = src["channels"][spec.channel]
    scores = np.asarray(ch["scores"], dtype=float)
    rel = np.array([p["relation"] for p in src["pairs"]])
    cat = np.array([p["category"] for p in src["pairs"]])
    pres = scores[rel == "PRESERVING"]

    if spec.two_tailed:
        lower = float(np.quantile(pres, PER_TAIL_BUDGET))
        upper = float(np.quantile(pres, 1.0 - PER_TAIL_BUDGET))
        budget = PER_TAIL_BUDGET
        threshold = upper if spec.tail == "upper" else lower
    else:
        lower, upper = None, None
        budget = ONE_TAIL_BUDGET
        threshold = float(np.quantile(pres, 1.0 - ONE_TAIL_BUDGET))

    row = Row(
        label=spec.label, detail=spec.detail, group=spec.group,
        run_id=src["run_id"], config_hash=src["config_hash"],
        channel=spec.channel, hub_id=ch["hub_id"], revision=ch["revision"],
        tail=spec.tail, budget=budget, threshold=threshold,
        threshold_lower=lower, threshold_upper=upper,
    )
    for _, _, cols in COLUMN_GROUPS:
        for key, _ in cols:
            vals = scores[cat == key]
            if len(vals) == 0:
                row.cells[key] = None  # not in this run's pair set
                continue
            fired = int((vals > threshold).sum() if spec.tail == "upper"
                        else (vals < threshold).sum())
            lo, hi = wilson(fired, len(vals))
            row.cells[key] = Cell(len(vals), fired, fired / len(vals), lo, hi)
    return row


def build_map(results_dir: str | Path) -> dict:
    """Everything the figure shows, as data, with the runs it came from."""
    results_dir = Path(results_dir)
    sources = _load(results_dir)
    rows = [_row(spec, sources[spec.source]) for spec in ROWS]
    return {
        "sources": [
            {"key": k, "file": SOURCES[k], "run_id": s["run_id"],
             "config_hash": s["config_hash"], "n_pairs": s["n_pairs"],
             "normalised": bool(s.get("normalised", False)),
             "relabelled_verbosity_as_hedging": s["_relabelled"]}
            for k, s in sources.items()
        ],
        "budget": {"one_tailed": ONE_TAIL_BUDGET, "per_tail": PER_TAIL_BUDGET,
                   "threshold_source": "quantile of the preserving pairs, pooled "
                                       "over the four output shapes"},
        "columns": [{"group": g, "title": t, "keys": [k for k, _ in cols],
                     "labels": [lab for _, lab in cols]}
                    for g, t, cols in COLUMN_GROUPS],
        "rows": [
            {**{k: v for k, v in asdict(r).items() if k != "cells"},
             "cells": {k: (asdict(c) if c else None) for k, c in r.cells.items()}}
            for r in rows
        ],
        "floors": [dict(f) for f in FLOORS],
    }


def markdown_table(m: dict) -> str:
    """The same map as a table, for a document that cannot carry the figure."""
    cols = [(k, lab) for g in m["columns"] for k, lab in zip(g["keys"], g["labels"])]
    head = "| check | " + " | ".join(lab for _, lab in cols) + " |"
    sep = "|---|" + "|".join("---:" for _ in cols) + "|"
    lines = [head, sep]
    for r in m["rows"]:
        vals = []
        for k, _ in cols:
            c = r["cells"][k]
            vals.append("not run" if c is None else f"{c['rate']:.0%}")
        lines.append(f"| {r['label']} ({r['detail']}) | " + " | ".join(vals) + " |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Drawing. Plain SVG, no plotting library: the figure is a grid of rectangles
# and text, and a dependency for that would be a dependency for nothing.

_SURFACE = "#fcfcfb"
_INK = "#0b0b0b"
_INK2 = "#52514e"
_MUTED = "#898781"
_HAIRLINE = "#e1e0d9"
_AXIS = "#c3c2b7"
# One hue, light to dark, from the validated sequential ramp. Interpolated
# linearly between steps so a 37% cell sits between the 300 and 400 steps.
_RAMP = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
_FONT = "Inter, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _ramp(rate: float) -> str:
    x = min(max(rate, 0.0), 1.0) * (len(_RAMP) - 1)
    i = min(int(x), len(_RAMP) - 2)
    t = x - i
    a, b = _hex_to_rgb(_RAMP[i]), _hex_to_rgb(_RAMP[i + 1])
    return "#%02x%02x%02x" % tuple(round(a[j] + (b[j] - a[j]) * t) for j in range(3))


def _esc(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


def _text(x: float, y: float, s: str, size: int = 12, fill: str = _INK,
          anchor: str = "start", weight: str = "normal", extra: str = "") -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" {extra}>{_esc(s)}</text>')


def render_svg(m: dict) -> str:
    cols = [(g["group"], k, lab) for g in m["columns"]
            for k, lab in zip(g["keys"], g["labels"])]
    grid_rows = [r for r in m["rows"] if r["group"] in GRID_GROUPS]
    shipped_rows = [r for r in m["rows"] if r["group"] not in GRID_GROUPS]
    rows = grid_rows + shipped_rows

    label_w, cell_w, cell_h, gap, group_gap = 290, 66, 40, 2, 14
    top = 132  # title, subtitle, legend, column headers
    left = 24
    width = left + label_w + len(cols) * cell_w + 2 * group_gap + 24

    # Row y positions, with a gap and a group caption between groups. The
    # shipped block gets a wider gap, a rule, and a note, because it is a
    # different run and must not read as three more rows of the grid.
    y = top
    row_y: list[float] = []
    captions: list[tuple[float, str]] = []
    notes: list[tuple[float, str]] = []
    group_span: dict[str, tuple[float, float]] = {}
    last_group = None
    for r in rows:
        if r["group"] != last_group:
            if r["group"] not in GRID_GROUPS:
                y += 54
                notes.append((y - 22, "Different run, 896 pairs, thresholds set over "
                              "its own preserving pairs. Not read across against "
                              "the grid: the gap to the raw rows is what "
                              "normalisation buys (MTH-019)."))
            elif last_group is not None:
                y += 26
            captions.append((y - 6, GROUP_TITLES[r["group"]]))
            last_group = r["group"]
        row_y.append(y)
        lo, _ = group_span.get(r["group"], (y, y))
        group_span[r["group"]] = (lo, y + cell_h)
        y += cell_h + gap
    grid_bottom = y

    # Column x positions, with a gap between column groups.
    col_x: list[float] = []
    x = left + label_w
    last_group = None
    for g, _, _ in cols:
        if last_group is not None and g != last_group:
            x += group_gap
        col_x.append(x)
        x += cell_w
        last_group = g

    floors_top = grid_bottom + 48
    floors_h = 26 + 22 * len(m["floors"])
    footer_top = floors_top + floors_h + 18
    height = footer_top + 56

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="{_FONT}" '
        f'role="img" aria-label="Blind-spot map: how often each check fires, by kind of change">',
        f'<rect width="{width}" height="{height}" fill="{_SURFACE}"/>',
        _text(left, 34, "What each check sees, and what it misses", 20, _INK, weight="600"),
        _text(left, 56, "How often each check fired, out of 64 pairs per cell, at a "
              "fixed false-alarm budget: 5% of pure rewordings for one-tailed "
              "checks, 2.5% per tail for the signed one.", 12, _INK2),
        _text(left, 73, "Dark means it fired often. In the left block that is coverage; "
              "in the right block it is a false alarm. A light cell on the left "
              "is a blind spot.", 12, _INK2),
    ]

    # Legend: the ramp, top right.
    lg_w, lg_h = 160, 10
    lg_x, lg_y = width - 24 - lg_w, 26
    out.append('<defs><linearGradient id="ramp" x1="0" x2="1" y1="0" y2="0">'
               + "".join(f'<stop offset="{i / (len(_RAMP) - 1):.3f}" stop-color="{c}"/>'
                         for i, c in enumerate(_RAMP))
               + "</linearGradient></defs>")
    out.append(f'<rect x="{lg_x}" y="{lg_y}" width="{lg_w}" height="{lg_h}" '
               f'fill="url(#ramp)" rx="2"/>')
    out.append(_text(lg_x, lg_y + 24, "fired on 0%", 10, _MUTED))
    out.append(_text(lg_x + lg_w, lg_y + 24, "100% of pairs", 10, _MUTED, anchor="end"))

    # Column group titles and column labels.
    gi = 0
    for g in m["columns"]:
        n = len(g["keys"])
        x0, x1 = col_x[gi], col_x[gi + n - 1] + cell_w
        out.append(_text((x0 + x1) / 2, top - 44, g["title"], 11, _INK2,
                         anchor="middle", weight="600"))
        out.append(f'<line x1="{x0 + 4}" y1="{top - 36}" x2="{x1 - 4}" y2="{top - 36}" '
                   f'stroke="{_AXIS}" stroke-width="1"/>')
        gi += n
    for (g, k, lab), cx in zip(cols, col_x):
        words = lab.split(" ")
        line1, line2 = (words[0], " ".join(words[1:])) if len(words) > 1 else (lab, "")
        out.append(_text(cx + cell_w / 2, top - 20, line1, 10, _INK2, anchor="middle"))
        if line2:
            out.append(_text(cx + cell_w / 2, top - 8, line2, 10, _INK2,
                             anchor="middle"))

    # Group captions, the rule above the shipped block, and row labels.
    for cy, title in captions:
        out.append(_text(left, cy - 2, title, 10, _MUTED, weight="600",
                         extra='letter-spacing="0.06em" style="text-transform:uppercase"'))
    for ny, note in notes:
        out.append(f'<line x1="{left}" y1="{ny - 20}" x2="{width - 24}" y2="{ny - 20}" '
                   f'stroke="{_AXIS}" stroke-width="1"/>')
        out.append(_text(left, ny, note, 10, _INK2))
    for r, ry in zip(rows, row_y):
        out.append(_text(left, ry + 17, r["label"], 12, _INK, weight="600"))
        out.append(_text(left, ry + 31, r["detail"], 10, _INK2))

    # A column absent from a whole group's pair set is one box, not a stack
    # of nine "not run" cells.
    for (g, k, lab), cx in zip(cols, col_x):
        for grp, (y0, y1) in group_span.items():
            members = [r for r in rows if r["group"] == grp]
            if all(r["cells"][k] is None for r in members):
                out.append(f'<rect x="{cx + 1}" y="{y0 + 1}" width="{cell_w - 2}" '
                           f'height="{y1 - y0 - 2}" fill="none" stroke="{_HAIRLINE}" '
                           f'stroke-dasharray="3 3" rx="4"/>')
                mid = (y0 + y1) / 2
                out.append(_text(cx + cell_w / 2 + 3, mid, "not in this pair set", 9,
                                 _MUTED, anchor="middle",
                                 extra=f'transform="rotate(-90 {cx + cell_w / 2 + 3:.1f} {mid:.1f})"'))

    # Cells.
    for r, ry in zip(rows, row_y):
        for (g, k, lab), cx in zip(cols, col_x):
            c = r["cells"][k]
            if c is None:
                continue  # drawn once per group above
            fill = _ramp(c["rate"])
            ink = "#ffffff" if c["rate"] >= 0.55 else _INK
            title = (f"{lab}: fired on {c['fired']} of {c['n']} "
                     f"({c['rate']:.1%}, 95% interval {c['lo']:.0%} to {c['hi']:.0%}). "
                     f"{r['label']}, {r['detail']}. Run {r['run_id']}.")
            out.append(f'<rect x="{cx + 1}" y="{ry + 1}" width="{cell_w - 2}" '
                       f'height="{cell_h - 2}" fill="{fill}" rx="4">'
                       f'<title>{_esc(title)}</title></rect>')
            out.append(_text(cx + cell_w / 2, ry + cell_h / 2 + 4, f"{c['rate']:.0%}",
                             12, ink, anchor="middle",
                             extra='style="font-variant-numeric:tabular-nums"'))

    # Floors: the sizes under which nothing fired.
    out.append(_text(left, floors_top, "Below these sizes, nothing fired", 12, _INK,
                     weight="600"))
    out.append(_text(left + 520, floors_top, "what sees it", 10, _MUTED, weight="600",
                     extra='letter-spacing="0.06em" style="text-transform:uppercase"'))
    out.append(_text(width - 24, floors_top, "measured in", 10, _MUTED, weight="600",
                     anchor="end",
                     extra='letter-spacing="0.06em" style="text-transform:uppercase"'))
    fy = floors_top + 22
    for f in m["floors"]:
        out.append(_text(left, fy, f["what"], 11, _INK2))
        out.append(_text(left + 520, fy, f["seen_by"], 11, _INK2))
        out.append(_text(width - 24, fy, f["ref"], 10, _MUTED, anchor="end"))
        fy += 22

    # Provenance footer.
    out.append(f'<line x1="{left}" y1="{footer_top}" x2="{width - 24}" '
               f'y2="{footer_top}" stroke="{_HAIRLINE}" stroke-width="1"/>')
    srcs = "; ".join(f"{s['run_id']} ({s['config_hash']}"
                     + (", normalised" if s["normalised"] else "")
                     + (", hedging relabelled from verbosity" if s["relabelled_verbosity_as_hedging"] else "")
                     + ")" for s in m["sources"])
    out.append(_text(left, footer_top + 18, "Recomputed from stored scores. Runs: " + srcs,
                     9, _MUTED))
    out.append(_text(left, footer_top + 32,
                     "Thresholds are pooled over four output shapes. Per-shape "
                     "thresholds differ by a factor of eighty and are what the detector "
                     "uses; the pooled figure is the honest summary, not the operating "
                     "point.", 9, _MUTED))
    out.append("</svg>")
    return "\n".join(out)
