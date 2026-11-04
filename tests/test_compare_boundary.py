"""The compare seat's first guardrail, promised in docs/compare/METHODS.md:
comparator code imports aprime through its public API only.

Today the whitelist is empty because nothing in compare/ needs the detector
yet. When the campaign's pairwise stage arrives, the names it may import get
added HERE, deliberately, one by one — a deep import failing this test is the
boundary doing its job, not an obstacle to route around (ENG-006, HANDOFF
§24).
"""

from __future__ import annotations

import re
from pathlib import Path

COMPARE = Path(__file__).resolve().parents[1] / "compare"
ALLOWED_IMPORTS: set[str] = set()  # grows deliberately, never by convenience

_IMPORT = re.compile(r"^\s*(?:from|import)\s+(aprime[\w.]*)", re.M)


def test_compare_package_imports_only_the_public_api():
    offenders = []
    for py in COMPARE.rglob("*.py"):
        for name in _IMPORT.findall(py.read_text(encoding="utf-8")):
            if name not in ALLOWED_IMPORTS:
                offenders.append(f"{py.name}: {name}")
    assert not offenders, (
        "compare/ imports aprime outside the whitelist: "
        f"{offenders}. Add the name to ALLOWED_IMPORTS only if it is public "
        "API, per docs/compare/METHODS.md guardrail 1.")


def test_fixture_generation_is_deterministic(tmp_path, monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "fixtures_ventes", COMPARE / "fixtures_ventes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    monkeypatch.setattr(mod, "OUT", tmp_path / "a")
    first = {p.name: p.read_bytes() for p in mod.write_fixtures()}
    monkeypatch.setattr(mod, "OUT", tmp_path / "b")
    second = {p.name: p.read_bytes() for p in mod.write_fixtures()}
    assert first == second

    header = (tmp_path / "a" / "orders.csv").read_text(encoding="utf-8").splitlines()[0]
    assert header == ("order_id,order_date,client_id,product_id,qty,"
                      "unit_price_eur,tax_rate_pct,total_eur,status,"
                      "payment_due")
