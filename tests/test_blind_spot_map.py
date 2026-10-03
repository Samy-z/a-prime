"""The blind-spot map is recomputed from committed probe runs, so it has to
agree with the ledger entries those runs produced. If this test fails, either
the probe files changed or the recomputation drifted; neither should go
unnoticed, because the figure is quoted in the paper.

No models. Reads about 1.3 MB of JSON and finishes in well under a second.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.probes import blindspot  # noqa: E402

RESULTS = ROOT / "results"


@pytest.fixture(scope="module")
def m() -> dict:
    return blindspot.build_map(RESULTS)


def _row(m: dict, label: str, group: str) -> dict:
    return next(r for r in m["rows"] if r["label"] == label and r["group"] == group)


def test_sources_are_the_reference_runs(m):
    ids = {s["run_id"]: s for s in m["sources"]}
    assert ids["20260925T041059Z"]["normalised"] is True
    assert ids["20260925T041059Z"]["relabelled_verbosity_as_hedging"] is False
    # The two runs made before MTH-021 are relabelled so every row shares one
    # preserving set.
    assert ids["20260924T031004Z"]["relabelled_verbosity_as_hedging"] is True
    assert ids["20260924T022150Z"]["relabelled_verbosity_as_hedging"] is True


def test_every_cell_has_sixty_four_pairs_or_was_not_run(m):
    for r in m["rows"]:
        for key, c in r["cells"].items():
            if c is None:
                # Only `overconfidence` is missing, and only from the two
                # runs made before the register class existed.
                assert key == "overconfidence" and r["run_id"] != "20260925T041059Z"
            else:
                assert c["n"] == 64, (r["label"], key, c["n"])


def test_shipped_contradiction_matches_mth_019_and_mth_021(m):
    r = _row(m, "contradiction", "shipped")
    for key in ("entity", "number", "temporal", "negation", "polarity",
                "quantifier", "unit"):
        assert r["cells"][key]["fired"] == 64, key
    # Omission on contradiction, normalised: 11 of 64 (17.2%, MTH-021 run).
    assert r["cells"]["omission"]["fired"] == 11
    # The relocated false alarms of MTH-019: synonym 14.1%, paraphrase 6.2%.
    assert r["cells"]["synonym"]["fired"] == 9
    assert r["cells"]["paraphrase"]["fired"] == 4
    assert r["cells"]["format"]["fired"] == 0


def test_two_tailed_thresholds_match_mth_022(m):
    loss = _row(m, "information loss", "shipped")
    gain = _row(m, "information gain", "shipped")
    assert loss["threshold_lower"] == pytest.approx(-0.055, abs=0.001)
    assert loss["threshold_upper"] == pytest.approx(0.096, abs=0.001)
    assert loss["budget"] == 0.025 and gain["budget"] == 0.025
    # Omission: 63 of 64 above the upper cut. Both register directions: 64 of
    # 64 below the lower cut.
    assert loss["cells"]["omission"]["fired"] == 63
    assert gain["cells"]["hedging"]["fired"] == 64
    assert gain["cells"]["overconfidence"]["fired"] == 64
    # And the tails do not leak into each other.
    assert loss["cells"]["hedging"]["fired"] == 0
    assert gain["cells"]["omission"]["fired"] == 0


def test_grid_rows_share_one_pair_set_and_the_shipped_rows_do_not(m):
    """STD-009 amendment: the grid is read across, so it is raw runs only."""
    grid = [r for r in m["rows"] if r["group"] in blindspot.GRID_GROUPS]
    shipped = [r for r in m["rows"] if r["group"] == "shipped"]
    assert len(grid) == 9 and len(shipped) == 3
    assert {r["run_id"] for r in grid} == {"20260924T031004Z", "20260924T022150Z"}
    assert {r["run_id"] for r in shipped} == {"20260925T041059Z"}


def test_raw_deberta_matches_the_mth_017_reconciliation(m):
    """The counts the dated append under MTH-017 publishes for the map's rule."""
    con = _row(m, "contradiction", "detector")
    loss = _row(m, "information loss", "detector")
    assert con["cells"]["unit"]["fired"] == 53
    assert con["cells"]["quantifier"]["fired"] == 57
    assert con["cells"]["polarity"]["fired"] == 63
    assert con["cells"]["format"]["fired"] == 9
    assert con["cells"]["omission"]["fired"] == 0
    assert loss["cells"]["omission"]["fired"] == 59


def test_second_checkpoint_reproduces_direction_not_magnitude(m):
    """MTH-017: RoBERTa agrees on which categories are hard, not on how hard.

    Compared against raw DeBERTa from the same run and the same pairs, never
    against the normalised rows, which would credit the model with what
    normalisation bought (MTH-019).
    """
    deb = _row(m, "contradiction", "detector")
    rob = _row(m, "contradiction", "replication")
    assert deb["run_id"] == rob["run_id"]
    assert rob["cells"]["omission"]["rate"] < 0.5  # still the hard case
    assert rob["cells"]["negation"]["rate"] == 1.0
    assert rob["cells"]["unit"]["fired"] == 23
    assert rob["cells"]["quantifier"]["fired"] == 37
    assert rob["cells"]["unit"]["rate"] < deb["cells"]["unit"]["rate"] - 0.4


def test_normalisation_buys_detection_is_visible(m):
    """MTH-019, read off the figure: shipped rows beat raw DeBERTa on coverage."""
    raw = _row(m, "contradiction", "detector")
    norm = _row(m, "contradiction", "shipped")
    for key in ("unit", "quantifier", "polarity"):
        assert norm["cells"][key]["fired"] >= raw["cells"][key]["fired"]
    assert norm["cells"]["unit"]["fired"] == 64 and raw["cells"]["unit"]["fired"] == 53


def test_embedding_rows_are_blind_to_fact_changes(m):
    """MTH-011: numbers, dates and negations move the vector less than rewording."""
    for detail in ("MiniLM-L6", "BGE-base", "E5-base"):
        r = next(r for r in m["rows"] if r["detail"].startswith(detail))
        for key in ("number", "temporal", "negation", "quantifier"):
            assert r["cells"][key]["rate"] <= 0.05, (detail, key)


def test_floors_name_their_ledger_entries(m):
    refs = {f["ref"] for f in m["floors"]}
    assert {"MTH-018", "MTH-024", "ENG-004", "BCH-004"} <= refs


def test_svg_is_well_formed_and_carries_provenance(m):
    svg = blindspot.render_svg(m)
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    for s in m["sources"]:
        assert s["run_id"] in svg and s["config_hash"] in svg
    # Every measured cell carries its denominator and interval in a tooltip.
    assert svg.count("95% interval") == sum(
        1 for r in m["rows"] for c in r["cells"].values() if c is not None
    )


def test_markdown_table_has_a_column_per_category(m):
    table = blindspot.markdown_table(m)
    head = table.splitlines()[0]
    n_cols = sum(len(g["keys"]) for g in m["columns"])
    assert head.count("|") == n_cols + 2
    assert "not run" in table
