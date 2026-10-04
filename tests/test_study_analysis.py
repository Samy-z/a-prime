"""Phase 2 of the study runner, driven end to end without a model.

`results/study/matrix.json` had never been written and nothing tested the
path that writes it: the first time it would have run was at about four in
the morning after twelve hours of recording. This lays a synthetic recording
on disk under the runner's own file names and config hash, runs the runner's
own `analyse()` on the exact-match path, and checks what comes out and what
is refused. No GPU, no model server, a few seconds.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.provenance import REQUIRED_ROW_PROVENANCE, check_row_provenance  # noqa: E402
from aprime.recorder import record  # noqa: E402
from aprime.stub import build_arms  # noqa: E402


def _load_runner():
    spec = importlib.util.spec_from_file_location(
        "run_study", ROOT / "scripts" / "run_study.py")
    mod = importlib.util.module_from_spec(spec)
    # Registered before executing: dataclasses resolve the module's string
    # annotations through sys.modules, and the script is not a package.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def runner(tmp_path, monkeypatch):
    rs = _load_runner()
    monkeypatch.setattr(rs, "RUNS", tmp_path / "study")
    rs.RUNS.mkdir(parents=True)
    return rs


DIGEST = "sha256:0123456789abcdef0123456789abcdef"


def _lay_down_cell(rs, domain: str, fmt: str, n_affected: int = 12):
    """A cell recorded to disk exactly as phase 1 would leave it."""
    job = rs.make_job(domain, fmt, DIGEST, nli_rev="testrev")
    paths = job.paths()
    ids = [i.input_id for i in job.inputs]
    affected = set(ids[:n_affected])
    a, ap, b = build_arms(ids, affected, "mode_share", strength=0.9, seed=7)
    record(job.inputs, {"A": a, "A_prime": ap, "B": b}, k=rs.K,
           checkpoint=paths["checkpoint"])
    # The fault wrapper's own label store: "<input_id>#<sample_idx>": fired.
    paths["activation"].write_text(
        json.dumps({f"{iid}#0": (iid in affected) for iid in ids}),
        encoding="utf-8")
    return job, affected


def test_the_checkpoint_is_keyed_on_the_cell_name_and_config_hash(runner):
    job, _ = _lay_down_cell(runner, "banking", "summary")
    paths = job.paths()
    assert paths["checkpoint"].name == f"banking-summary.{job.prov.config_hash}.jsonl"
    assert paths["checkpoint"].exists() and paths["activation"].exists()
    assert paths["checkpoint"].parent == runner.RUNS


def test_analyse_writes_a_matrix_whose_rows_are_fully_traceable(runner):
    jobs = [_lay_down_cell(runner, "banking", "summary")[0],
            _lay_down_cell(runner, "logistics", "summary")[0]]
    out = runner.RUNS / "matrix.json"
    rc = runner.analyse(jobs, predicate=None, nli=None, digest=DIGEST, out=out)
    assert rc == 0
    assert out.exists()
    m = json.loads(out.read_text(encoding="utf-8"))
    assert m["model"] == runner.MODEL and m["digest"] == DIGEST
    assert m["n"] == runner.N and m["k"] == runner.K and m["q"] == runner.Q
    rows = m["rows"]
    assert [r["cell"] for r in rows] == ["banking-summary", "logistics-summary"]
    assert check_row_provenance(rows) == []
    for row, job in zip(rows, jobs):
        for key in REQUIRED_ROW_PROVENANCE:
            assert row.get(key) is not None, key
        assert row["run_id"] == job.prov.run_id
        assert row["config_hash"] == job.prov.config_hash
        assert row["system"] == runner.MODEL and row["system_digest"] == DIGEST
        assert row["sessions"] >= 1 and row["analysed_utc"].endswith("Z")
        assert row["n_inputs"] == runner.N and row["k"] == runner.K
        assert "gradable" in row and "channels" in row and "cost" in row
        # The per-cell report carries the same traceable row.
        rep = json.loads(job.paths()["report"].read_text(encoding="utf-8"))
        assert rep["config_hash"] == job.prov.config_hash


def test_activation_labels_on_disk_are_read_back_as_ground_truth(runner):
    job, affected = _lay_down_cell(runner, "hospitality", "summary", n_affected=15)
    out = runner.RUNS / "matrix.json"
    assert runner.analyse([job], None, None, DIGEST, out=out) == 0
    row = json.loads(out.read_text(encoding="utf-8"))["rows"][0]
    assert row["activated"] == 15
    # A strong fault on fifteen inputs at k=6 should be gradable and seen.
    assert row["gradable"] is True
    assert row["flagged"] >= 1 and row["true_positives"] >= 1


def test_a_row_that_cannot_be_traced_is_refused_and_nothing_is_written(runner, monkeypatch):
    job, _ = _lay_down_cell(runner, "banking", "summary")
    real = runner.row_provenance

    def broken(prov, **extra):  # the shape 75081ad fixed: hash only
        row = real(prov, **extra)
        row.pop("git_commit")
        row.pop("run_id")
        return row

    monkeypatch.setattr(runner, "row_provenance", broken)
    out = runner.RUNS / "matrix.json"
    rc = runner.analyse([job], predicate=None, nli=None, digest=DIGEST, out=out)
    assert rc == 4
    assert not out.exists(), "a refused analysis must not leave a matrix behind"
    assert not job.paths()["report"].exists(), (
        "a refused row must not leave its own report file behind either")


def test_refusal_on_the_second_cell_still_writes_nothing(runner, monkeypatch):
    """The check is per row, before that row's file; a late failure must not
    leave a half-written matrix or the earlier cell's report orphaned from it."""
    jobs = [_lay_down_cell(runner, "banking", "summary")[0],
            _lay_down_cell(runner, "logistics", "summary")[0]]
    real = runner.row_provenance
    calls = {"n": 0}

    def flaky(prov, **extra):
        calls["n"] += 1
        row = real(prov, **extra)
        if calls["n"] == 2:
            row["git_dirty"] = None
        return row

    monkeypatch.setattr(runner, "row_provenance", flaky)
    out = runner.RUNS / "matrix.json"
    assert runner.analyse(jobs, None, None, DIGEST, out=out) == 4
    assert not out.exists()
    # The first cell's report was written before the second failed. That file
    # is itself traceable, so it is kept; the matrix that would have pointed
    # at it is not.
    assert jobs[0].paths()["report"].exists()
    assert not jobs[1].paths()["report"].exists()
