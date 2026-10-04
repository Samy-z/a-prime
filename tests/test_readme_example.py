"""The README's worked example must be what the program prints.

The report format changed on 2026-10-04 and the README went on showing the
old one for several commits, because nothing compared the two (RDR-009). This
runs the demo, which is model-free and takes under a second, and checks that
every line of the README's example block appears verbatim in its output.
Lines that legitimately vary (the run id line) or elide (`...`) are skipped.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"


def _example_block() -> list[str]:
    text = README.read_text(encoding="utf-8")
    m = re.search(r"```bash\npython scripts/demo_detect\.py\n```\n\n```\n(.*?)\n```",
                  text, re.DOTALL)
    assert m, "README has no demo_detect example block"
    return m.group(1).splitlines()


def test_readme_example_matches_the_demo_output():
    out = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "demo_detect.py")],
        capture_output=True, text=True, timeout=120, cwd=ROOT,
    )
    assert out.returncode == 0, out.stderr[-2000:]
    printed = out.stdout.splitlines()
    missing = [ln for ln in _example_block()
               if ln.strip() and ln.strip() != "..." and not ln.strip().startswith("run ")
               and ln not in printed]
    assert not missing, "README example lines the demo did not print:\n" + "\n".join(missing)


def test_readme_example_is_not_trivially_short():
    assert len(_example_block()) >= 12
