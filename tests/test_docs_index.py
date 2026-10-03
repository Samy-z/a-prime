"""The knowledge index must agree with the directory it indexes.

A row that says "done" is a claim, and for nine days one of them named a file
that did not exist while another said GAP about a file that did (RDR-008).
This closes the gap between "the file is there" and "the index says so". It
cannot tell whether a doc that exists is current.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "docs" / "knowledge"
INDEX = KNOWLEDGE / "README.md"

_ROW = re.compile(r"^\|\s*`([^`]+\.md)`[^|]*\|\s*([^|]*)\|\s*([^|]*)\|")


def _rows() -> dict[str, str]:
    """Filename -> status cell, for every table row naming a `.md` file."""
    out: dict[str, str] = {}
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        m = _ROW.match(line)
        if m:
            out[m.group(1)] = m.group(3).strip()
    return out


def _is_claimed_written(status: str) -> bool:
    s = status.lower()
    return s.startswith("**done**") or s.startswith("**frozen**")


def test_index_has_rows():
    assert len(_rows()) >= 10


def test_every_row_marked_done_or_frozen_names_a_file_that_exists():
    missing = [name for name, status in _rows().items()
               if _is_claimed_written(status) and not (KNOWLEDGE / name).exists()]
    assert not missing, f"index says done, file absent: {missing}"


def test_every_row_marked_gap_names_a_file_that_does_not_exist():
    present = [name for name, status in _rows().items()
               if status.upper().startswith("GAP") and (KNOWLEDGE / name).exists()]
    assert not present, f"index says GAP, file present: {present}"


def test_every_knowledge_doc_has_a_row():
    docs = {p.name for p in KNOWLEDGE.glob("*.md")} - {"README.md"}
    unlisted = sorted(docs - set(_rows()))
    assert not unlisted, f"docs with no index row: {unlisted}"
