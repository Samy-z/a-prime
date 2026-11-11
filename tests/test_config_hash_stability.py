"""Sampling parameters enter the config hash without orphaning anything.

The rule (frozen 2026-11-11, docs/knowledge/provenance.md): a sampling value
equal to its historical default stays out of the hash, one moved off it
enters as `sampling.<name>`. The proof is recomputing committed cells' config
hashes through the runner's own `make_job`: if either moves, checkpoints on
disk are orphaned and this test fails before any night does.

Also the digest guard: an unfinished sibling recording of the same
configuration under other weights is named, and nothing else is.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# The committed identity of the recordings these hashes name.
DEBERTA = "6f5cf0a2b59cabb106aca4c287eed12e357e90eb"
DIGEST16 = "f586c02fdecdf151"
AGENT_K20 = "808db78857a32149"      # banking-agent, n=40 k=20 (STD-015)
SUMMARY_K6 = "60ac20518858cf53"     # banking-summary, n=40 k=6 (STD-010)


def _runner():
    spec = importlib.util.spec_from_file_location(
        "run_study", ROOT / "scripts" / "run_study.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_committed_hashes_recompute_unchanged():
    rs = _runner()
    rs.configure(n=40, k=20)
    job = rs.make_job("banking", "agent", DIGEST16, DEBERTA)
    assert job.prov.config_hash == AGENT_K20
    rs.configure(n=40, k=6)
    job = rs.make_job("banking", "summary", DIGEST16, DEBERTA)
    assert job.prov.config_hash == SUMMARY_K6


def test_default_sampling_adds_no_hash_params():
    rs = _runner()
    assert rs.sampling_hash_params() == {}


def test_off_default_temperature_is_its_own_configuration():
    rs = _runner()
    rs.configure(n=40, k=6)
    rs.configure_sampling(temperature=0.9)
    assert rs.sampling_hash_params() == {"sampling.temperature": 0.9}
    hot = rs.make_job("banking", "summary", DIGEST16, DEBERTA)
    assert hot.prov.config_hash != SUMMARY_K6
    assert hot.prov.params["sampling.temperature"] == 0.9
    rs.configure_sampling(temperature=0.2)
    back = rs.make_job("banking", "summary", DIGEST16, DEBERTA)
    assert back.prov.config_hash == SUMMARY_K6


def test_temperature_bounds():
    rs = _runner()
    with pytest.raises(ValueError, match="temperature"):
        rs.configure_sampling(temperature=2.5)


def _sibling(rs, job, digest, params=None, finished=False,
             config_hash="feedfacefeedface"):
    meta = {"config_hash": config_hash, "digest": digest,
            "params": params if params is not None else dict(job.prov.params)}
    (rs.RUNS / f"{job.name}.{config_hash}.meta.json").write_text(
        json.dumps(meta), encoding="utf-8")
    (rs.RUNS / f"{job.name}.{config_hash}.jsonl").write_text(
        "", encoding="utf-8")
    if finished:
        (rs.RUNS / f"{job.name}.{config_hash}.report.json").write_text(
            "{}", encoding="utf-8")


def test_digest_guard_names_exactly_the_orphaning_case(tmp_path, monkeypatch):
    rs = _runner()
    monkeypatch.setattr(rs, "RUNS", tmp_path / "study")
    rs.RUNS.mkdir(parents=True)
    rs.configure(n=40, k=6)
    job = rs.make_job("banking", "summary", DIGEST16, DEBERTA)

    # Same params, other weights, unfinished: the one case that refuses.
    _sibling(rs, job, digest="OTHERWEIGHTS0000")
    complaints = rs.digest_guard([job], DIGEST16)
    assert len(complaints) == 1 and "unfinished" in complaints[0]

    # Finished sibling under other weights: history, not a hazard.
    _sibling(rs, job, digest="OTHERWEIGHTS0000", finished=True,
             config_hash="feedfacefeedfac2")
    # Same weights sibling: not a version change.
    _sibling(rs, job, digest=DIGEST16, config_hash="feedfacefeedfac3")
    # Different params sibling (another k): a different configuration.
    other = dict(job.prov.params)
    other["k"] = 20
    _sibling(rs, job, params=other, digest="OTHERWEIGHTS0000",
             config_hash="feedfacefeedfac4")
    complaints = rs.digest_guard([job], DIGEST16)
    assert len(complaints) == 1, "only the unfinished same-config sibling counts"


def test_write_meta_is_additive_and_idempotent(tmp_path, monkeypatch):
    rs = _runner()
    monkeypatch.setattr(rs, "RUNS", tmp_path / "study")
    rs.RUNS.mkdir(parents=True)
    rs.configure(n=40, k=6)
    job = rs.make_job("banking", "summary", DIGEST16, DEBERTA)
    rs.write_meta(job)
    p = rs.RUNS / f"{job.name}.{job.prov.config_hash}.meta.json"
    first = p.read_text(encoding="utf-8")
    meta = json.loads(first)
    assert meta["digest"] == DIGEST16
    assert meta["params"] == job.prov.params
    rs.write_meta(job)
    assert p.read_text(encoding="utf-8") == first
