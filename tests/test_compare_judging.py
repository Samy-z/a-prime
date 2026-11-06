"""The judging queue must be blind, complete, and faithful to the store.

Runs the emitter against the real committed store and report (no models,
fast). Blindness is the validity property: a queue that leaks which side
is which model measures the judge's priors, not the outputs.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _mod():
    spec = importlib.util.spec_from_file_location(
        "emit_judging_queue", ROOT / "compare" / "emit_judging_queue.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _primary_ids() -> set[str]:
    rep = json.loads(
        (ROOT / "compare" / "results" / "pairwise-ventes.report.json")
        .read_text(encoding="utf-8"))
    return {f["input_id"] for f in rep["pairings"]["primary"]["findings"]}


def test_emit_covers_the_primary_selection_and_stays_blind(tmp_path):
    mod = _mod()
    queue, key_p = tmp_path / "q.md", tmp_path / "k.json"
    assert mod.emit(queue_path=queue, key_path=key_p) == 0

    body = queue.read_text(encoding="utf-8")
    ids = re.findall(r"^## Cas \d+ \(id: ([a-z0-9-]+)\)$", body, re.M)
    assert set(ids) == _primary_ids() and len(ids) == len(set(ids))
    assert not mod.FORBIDDEN.search(body)

    key = json.loads(key_p.read_text(encoding="utf-8"))
    idx = mod._store_index()
    for case in key["cases"]:
        assert {case["X"], case["Y"]} == set(mod.ARMS)
        for side in ("X", "Y"):
            for arm, sidx in case["draws"][side]:
                assert idx[(case["input_id"], arm, sidx)].strip() in body


def test_overwrite_guard_protects_filled_verdicts(tmp_path):
    mod = _mod()
    queue, key_p = tmp_path / "q.md", tmp_path / "k.json"
    assert mod.emit(queue_path=queue, key_path=key_p) == 0
    body = queue.read_text(encoding="utf-8")
    queue.write_text(body.replace("verdict:\n", "verdict: X\n", 1),
                     encoding="utf-8")
    assert mod.emit(queue_path=queue, key_path=key_p) == 2
    assert mod.emit(queue_path=queue, key_path=key_p, force=True) == 0


def test_score_unblinds_against_the_key(tmp_path):
    mod = _mod()
    queue, key_p, out = tmp_path / "q.md", tmp_path / "k.json", tmp_path / "v.json"
    mod.emit(queue_path=queue, key_path=key_p)
    body = queue.read_text(encoding="utf-8").replace("verdict:\n", "verdict: X\n")
    queue.write_text(body, encoding="utf-8")

    assert mod.score(queue_path=queue, key_path=key_p, out_path=out) == 0
    verdict = json.loads(out.read_text(encoding="utf-8"))
    key = json.loads(key_p.read_text(encoding="utf-8"))
    x_of = {c["input_id"]: c["X"] for c in key["cases"]}
    assert all(c["judged_model"] == x_of[c["input_id"]]
               for c in verdict["cases"])
    assert sum(verdict["totals"].values()) == len(key["cases"])
