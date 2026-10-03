"""Draw the blind-spot map from the probe runs already under results/.

    python scripts/draw_blind_spot_map.py            # write the figure and its data
    python scripts/draw_blind_spot_map.py --table    # print it as a markdown table

No models, no network. Reads the three reference probe runs named in
`aprime.probes.blindspot.SOURCES`, recomputes every cell from the stored scores,
and writes:

    docs/figures/blind_spot_map.svg   the figure
    results/blind_spot_map.json       the same numbers as data, with the run ids
                                      and config hashes they came from

Rerunning is idempotent as long as the source files are unchanged. If a probe
run is redone, point SOURCES at the new files and the figure follows.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.probes import blindspot  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", action="store_true", help="print a markdown table")
    args = ap.parse_args()

    m = blindspot.build_map(ROOT / "results")

    if args.table:
        print(blindspot.markdown_table(m))
        return 0

    svg_path = ROOT / "docs" / "figures" / "blind_spot_map.svg"
    json_path = ROOT / "results" / "blind_spot_map.json"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(blindspot.render_svg(m), encoding="utf-8")
    json_path.write_text(json.dumps(m, indent=2), encoding="utf-8")

    print("sources")
    for s in m["sources"]:
        print(f"  {s['run_id']}  {s['config_hash']}  {s['file']}")
    print(f"rows {len(m['rows'])}  columns "
          f"{sum(len(g['keys']) for g in m['columns'])}  floors {len(m['floors'])}")
    print(f"wrote {svg_path.relative_to(ROOT)}")
    print(f"wrote {json_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
