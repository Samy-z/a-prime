"""The decision-variation instrument reads the recording the detector reads.

It drops the samples the detector drops (errored calls), scores the decision
token the way the partition statistics score a mode label, and writes its
numbers beside the checkpoint under the recording's own configuration hash.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location(
        "agent_decision_variation", ROOT / "scripts" / "agent_decision_variation.py"
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _record(iid, arm, idx, order, output, error=None, finish="stop"):
    return {"input_id": iid, "arm": arm, "sample_idx": idx, "order": order,
            "output": output, "latency_ms": 1.0, "ts": 0.0, "model_id": "toy-agent",
            "finish_reason": finish, "error": error, "session": 0}


def _toy_cell(tmp_path: Path) -> Path:
    clouds = {
        # the fault flips the decision outright; the two baselines agree
        "i1": {"A": ["APPROVE x", "APPROVE y"], "A_prime": ["APPROVE z", "APPROVE w"],
               "B": ["DECLINE q", "DECLINE r"]},
        # the same mix everywhere, in different words
        "i2": {"A": ["DECLINE a", "ESCALATE b"], "A_prime": ["ESCALATE c", "DECLINE d"],
               "B": ["DECLINE a", "ESCALATE b"]},
        # one candidate call errored and must not count as a sample
        "i3": {"A": ["APPROVE", "APPROVE"], "A_prime": ["APPROVE", "APPROVE"],
               "B": ["APPROVE", ("", "HTTPError: HTTP Error 500")]},
    }
    cp = tmp_path / "toy-agent.deadbeefdeadbeef.jsonl"
    lines, order = [], 0
    for iid, arms in clouds.items():
        for idx in range(2):
            for arm in ("A", "A_prime", "B"):
                out = arms[arm][idx]
                err = None
                if isinstance(out, tuple):
                    out, err = out
                lines.append(json.dumps(_record(iid, arm, idx, order, out, err)))
                order += 1
    cp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    act = {"i1#0": True, "i1#1": True, "i2#0": False, "i2#1": False,
           "i3#0": True, "i3#1": False}
    (tmp_path / "toy-agent.deadbeefdeadbeef.activation.json").write_text(
        json.dumps(act), encoding="utf-8")
    return cp


def test_decision_token_is_the_first_upper_case_verdict_anywhere_in_the_text():
    mod = _load()
    assert mod.decision("The ratio is 0.7.\n\n<decision>\nDECLINE - over limit") == "DECLINE"
    assert mod.decision("APPROVE The ratio 0.0 is below the limit.") == "APPROVE"
    assert mod.decision("we would decline this one") == "NONE"
    assert mod.decision("") == "NONE"


def test_scores_flips_and_dropped_samples_on_a_toy_cell(tmp_path):
    mod = _load()
    cp = _toy_cell(tmp_path)
    out = mod.analyse(cp)

    assert out["n_inputs"] == 3 and out["fired"] == 2 and out["quiet"] == 1
    assert out["live"]["errored_dropped"] == 1
    dec = out["decision"]
    assert dec["scores"]["targets"] == [1.0, 0.0, 0.0]
    assert dec["scores"]["decoys"] == [0.0, 0.0, 0.0]
    flips = dec["majority_flips"]
    assert flips["A_vs_A_prime"] == 0
    assert flips["A_vs_B_fired"] == 1 and flips["A_vs_B_quiet"] == 0
    assert dec["decoys_zero"] == 3

    # A sits in both arm pairs, so it is counted twice; the errored B sample
    # never enters a cloud: 2*6 + 6 + 5.
    assert out["exact_match"]["cost"]["samples_clustered"] == 23
    assert set(out["exact_match"]["channels"]) == {"mode_share", "dispersion", "novel_mode"}


def test_main_writes_the_file_beside_the_checkpoint(tmp_path, capsys):
    mod = _load()
    cp = _toy_cell(tmp_path)
    assert mod.main([str(cp)]) == 0
    dest = tmp_path / "toy-agent.deadbeefdeadbeef.decisions.json"
    assert dest.exists()
    written = json.loads(dest.read_text(encoding="utf-8"))
    assert written["checkpoint"] == cp.name
    assert written["decision"]["majority_flips"]["A_vs_B_fired"] == 1
    assert "wrote toy-agent.deadbeefdeadbeef.decisions.json" in capsys.readouterr().out
