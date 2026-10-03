"""The family STATE files, checked for the one thing a script can check.

The cloud session built `test_docs_index.py` after finding four stale status
claims in one week, and named the family `STATE.md` files as the obvious next
place it does not cover. This is that, and it is deliberately weaker, because
the two are not the same shape.

The knowledge index is one table with one status vocabulary, so status can be
checked against the directory: `done` means the file exists, `GAP` means it does
not. The STATE files are not that. Five status words appear across them (GAP,
done, frozen, live, reviewed), the columns differ per family, and many rows
describe a capability or a figure rather than a file. "Domain x format factorial
| GAP" names no path, so no script can confirm or deny it.

**So this checks path references and nothing else.** When a STATE row mentions a
file, that file has to exist. When a row says GAP and names a file, that file
has to not exist.

What it cannot check, and what therefore still needs a person: whether a status
is *current*. A row saying `live` about a subsystem that was frozen last week
will pass every test here. The failure this suite catches is the narrow one
where the prose and the filesystem disagree outright.

**It would have caught none of the four failures that prompted it.** Three were
in the knowledge index rather than a STATE file, which `test_docs_index.py`
covers. The fourth was in `reader/STATE.md` and was a prose contradiction: the
row said the paper "needs its own contract row" while `reader/METHODS.md` had
one. No path was wrong, so nothing here fires.

That is stated plainly because this project has already learned the expensive
version of the lesson twice (RDR-004, RDR-006): a check that returns clean on
the problem it was built for is worse than no check, since it converts an open
question into false reassurance. This suite guards a failure mode that has not
happened yet. The one that has keeps needing a reader.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

STATE_FILES = sorted((ROOT / "docs").glob("*/STATE.md"))

# A path reference inside a table cell or prose: backticked, with a slash or a
# known extension. Deliberately narrow, so a bare word like "recorder" is not
# mistaken for `recorder.py`.
_PATH = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|py|json|jsonl|svg|txt))`")
_GAP = re.compile(r"\bGAP\b")


def _rows(path: Path) -> list[str]:
    """Table rows and block quotes, which is where status claims live."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("|") or stripped.startswith(">"):
            out.append(stripped)
    return out


def test_there_are_state_files_to_check():
    assert STATE_FILES, "expected docs/<family>/STATE.md"
    assert len(STATE_FILES) >= 5, [p.parent.name for p in STATE_FILES]


@pytest.mark.parametrize("state", STATE_FILES, ids=lambda p: p.parent.name)
def test_every_file_a_state_row_names_exists(state: Path):
    """A STATE file pointing at something that is not there is worse than one
    that says nothing, because a reader trusts it and stops looking."""
    missing = []
    for row in _rows(state):
        for ref in _PATH.findall(row):
            # Paths are written relative to the repo root or to the doc.
            if (ROOT / ref).exists() or (state.parent / ref).exists():
                continue
            # A row declaring the thing absent is allowed to name it.
            if _GAP.search(row):
                continue
            missing.append(f"{ref} in: {row[:90]}")
    assert not missing, f"{state.relative_to(ROOT)} names files that do not exist:\n" + "\n".join(missing)


@pytest.mark.parametrize("state", STATE_FILES, ids=lambda p: p.parent.name)
def test_a_row_saying_gap_does_not_name_a_file_that_exists(state: Path):
    """The failure that actually happened, four times in one week: the work
    landed and the status line did not move."""
    wrong = []
    for row in _rows(state):
        if not _GAP.search(row):
            continue
        for ref in _PATH.findall(row):
            if (ROOT / ref).exists() or (state.parent / ref).exists():
                wrong.append(f"{ref} exists, but: {row[:90]}")
    assert not wrong, (
        f"{state.relative_to(ROOT)} calls something a GAP that is on disk:\n"
        + "\n".join(wrong))


def test_the_suite_states_what_it_cannot_check():
    """A guard against this file being read as more than it is.

    Somebody will eventually see a green suite and conclude the STATE files are
    accurate. They are not checked for accuracy, only for outright
    contradiction with the filesystem, and the docstring has to keep saying so.
    """
    doc = Path(__file__).read_text(encoding="utf-8")
    assert "cannot check" in doc
    assert "needs a person" in doc
