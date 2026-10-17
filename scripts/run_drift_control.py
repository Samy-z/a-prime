"""The drift negative control: the same system, weeks apart, expecting silence.

STD-008 scoped it; MTH-026 is the frozen protocol and carries the filed
expectations. The question: how much "difference" does time alone produce?
The detector's flagship scenario (a model updated under you) can never
interleave its arms, because the baseline is weeks old by definition. Before
any stored-baseline comparison can be trusted, the no-change case has to be
measured: compare a system against its own recording from weeks ago, with
nothing changed, and see whether the detector stays silent.

Period one is the banking-summary k=6 baseline pair recorded 2026-10-04
(checkpoint `banking-summary.60ac20518858cf53.jsonl`, arms A and A_prime; the
faulted B arm of that recording is ignored here). Period two is recorded by
this script: three fresh arms of the SAME cell with NO fault, today. Three
comparisons are then scored through the ordinary detector:

  cross-p1null   period-1 A vs period-2 A, nulled by period-1's own pair
  cross-p2null   period-2 A vs period-1 A, nulled by period-2's own pair
  within-p2      the three fresh arms against each other, same day

Expectations, filed in MTH-026 before this ever ran: zero flagged in all
three at q=0.10. A nonzero count in the cross-period comparisons with a zero
within-period count IS the drift measurement, not a failure of the run.

Guards that make it a negative control rather than noise:
- the model digest must equal period one's; a changed digest means the weights
  moved and the run aborts (exit 5), because that would be a positive case;
- the corpus is rebuilt from the same seeds and every input id must match the
  period-1 checkpoint exactly (exit 4 otherwise);
- the recording is checkpointed, resumable and respects run_study's stop flag.

    python scripts/run_drift_control.py            # plan only, no calls
    python scripts/run_drift_control.py --go       # record (~1 h) and score
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.net import enable_os_truststore  # noqa: E402

enable_os_truststore()

from aprime.cells.cell import Cell, build_inputs  # noqa: E402
from aprime.cells.chat import OllamaChat  # noqa: E402
from aprime.cells.packs import build_pack  # noqa: E402
from aprime.cells.tools import ToolSet  # noqa: E402
from aprime.clustering import NLIEquivalence  # noqa: E402
from aprime.detect import detect  # noqa: E402
from aprime.probes.channels import NLI_MODELS, NLIChannel, _resolve_revision  # noqa: E402
from aprime.provenance import capture, corpus_fingerprint  # noqa: E402
from aprime.recorder import (  # noqa: E402
    PreflightFailed,
    Recording,
    RecordingFailed,
    RunPaused,
    load_checkpoint,
    record,
    recording_progress,
    stop_requested,
)

HOST = __import__("os").environ.get("APRIME_OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL = "granite4.2:8b"
DOMAIN, FMT = "banking", "summary"
N, K, Q = 40, 6, 0.10
N_ENTITIES = 18

P1_STEM = "banking-summary.60ac20518858cf53"
P1_CHECKPOINT = ROOT / "results" / "study" / f"{P1_STEM}.jsonl"
P1_REPORT = ROOT / "results" / "study" / f"{P1_STEM}.report.json"
P1_RECORDED = "2026-10-04"

OUT_DIR = ROOT / "results" / "drift"
STOP_FLAG = ROOT / "results" / "study" / "STUDY.STOP"
SECONDS_PER_CALL = 4.8


def ollama_digest() -> str:
    import urllib.request

    try:
        with urllib.request.urlopen(HOST + "/api/tags", timeout=30) as r:
            for m in json.loads(r.read().decode()).get("models", []):
                if m.get("name") == MODEL:
                    return str(m.get("digest") or "unresolved")
    except Exception:  # noqa: BLE001
        pass
    return "unresolved"


def chat() -> OllamaChat:
    # Mirrors run_study.chat(): seed unset on every arm (MTH-023).
    return OllamaChat(model=MODEL, host=HOST, keep_alive="10m", num_ctx=8192,
                      temperature=0.2, num_predict=512, seed=None)


def relabel(samples, arm: str):
    return [dataclasses.replace(s, arm=arm) for s in samples]


def by_arm(samples, arm: str):
    return [s for s in samples if s.arm == arm]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--go", action="store_true",
                    help="record and score; without it, print the plan")
    args = ap.parse_args()

    if not P1_CHECKPOINT.exists():
        print(f"period-1 checkpoint missing: {P1_CHECKPOINT}")
        return 1
    p1_samples, _, _ = load_checkpoint(P1_CHECKPOINT)
    p1_ids = list(dict.fromkeys(s.input_id for s in p1_samples))
    p1_digest = json.loads(P1_REPORT.read_text(encoding="utf-8"))["system_digest"]

    pack = build_pack(DOMAIN, n_entities=N_ENTITIES, seed=1)
    inputs = build_inputs(pack, n=N, seed=1, output_format=FMT)
    ids = [i.input_id for i in inputs]
    if ids != p1_ids:
        print("REFUSING: the rebuilt corpus does not match the period-1 "
              "checkpoint input ids. Same seeds should give the same corpus; "
              "something drifted in the generator, and comparing across it "
              "would not be a negative control.")
        return 4

    prov = capture(
        instruments={"predicate": "NLIEquivalence@0.7",
                     "system_model": MODEL + "@" + p1_digest[:16]},
        params={"k": K, "q": Q, "n_inputs": N, "domain": DOMAIN,
                "output_format": FMT, "fault": "none (drift negative control)",
                "period1": P1_STEM, "period1_recorded": P1_RECORDED,
                "seed_policy": "unset on every arm (MTH-023)"},
        corpus=corpus_fingerprint(ids),
        notes={"purpose": "drift negative control (STD-008, MTH-026)",
               "model_host": HOST},
        warn_if_dirty=False,
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    p2_checkpoint = OUT_DIR / f"drift-p2.{prov.config_hash}.jsonl"
    report_path = OUT_DIR / f"drift-control.{prov.config_hash}.report.json"

    progress = recording_progress(p2_checkpoint, inputs, K)
    print(f"drift negative control: {DOMAIN}-{FMT}, n={N} k={K}, "
          f"period 1 recorded {P1_RECORDED}")
    print(f"period-2 recording: {progress['remaining']} of {progress['planned']} "
          f"triples left (~{progress['remaining'] * 3 * SECONDS_PER_CALL / 60:.0f} min)")
    if not args.go:
        print("this is a plan, not a run. Add --go to record and score.")
        return 0

    digest = ollama_digest()
    if digest != p1_digest:
        print(f"REFUSING: the model digest changed ({digest[:12]} now, "
              f"{p1_digest[:12]} in period 1). The weights moved, so this "
              "would be a positive case, not a negative control. Record it as "
              "a version-change observation instead.")
        return 5

    # Three fresh arms, all baseline, no fault anywhere.
    arms = {"A": Cell(pack, FMT, chat(), "A", tools=ToolSet(pack)),
            "A_prime": Cell(pack, FMT, chat(), "A_prime", tools=ToolSet(pack)),
            "B": Cell(pack, FMT, chat(), "B", tools=ToolSet(pack))}
    try:
        record(inputs, arms, k=K, checkpoint=p2_checkpoint, progress_every=25,
               should_stop=stop_requested(STOP_FLAG))
    except PreflightFailed as dead:
        OllamaChat(model=MODEL, host=HOST).release()
        print("PREFLIGHT FAILED, nothing recorded:")
        for probe in dead.result.failed:
            print(f"  {probe.arm}: {probe.error}")
        return 3
    except RecordingFailed as died:
        OllamaChat(model=MODEL, host=HOST).release()
        print(f"SERVER DIED mid-recording: {died}. Recorded triples are on "
              "disk and resume.")
        return 6
    except RunPaused as paused:
        OllamaChat(model=MODEL, host=HOST).release()
        print(f"PAUSED: {paused}. Resume by rerunning with --go.")
        return 2
    OllamaChat(model=MODEL, host=HOST).release()

    p2_samples, _, _ = load_checkpoint(p2_checkpoint)
    print("scoring (system model released, NLI model loaded once)")
    nli_spec = next(s for s in NLI_MODELS if s.key == "deberta_mnli")
    nli = NLIChannel(nli_spec)
    predicate = NLIEquivalence(nli, threshold=0.7)

    comparisons = {
        # Old baseline pair as the null; today's system as the candidate.
        "cross-p1null": (by_arm(p1_samples, "A")
                         + by_arm(p1_samples, "A_prime")
                         + relabel(by_arm(p2_samples, "A"), "B")),
        # Today's own pair as the null; the old recording as the candidate.
        "cross-p2null": (by_arm(p2_samples, "A")
                         + by_arm(p2_samples, "A_prime")
                         + relabel(by_arm(p1_samples, "A"), "B")),
        # Same-day sanity: three baseline arms, nothing should separate.
        "within-p2": list(p2_samples),
    }
    results = {}
    for name, samples in comparisons.items():
        rec = Recording(samples=samples, k=K, input_ids=ids)
        rep = detect(rec, predicate=predicate, nli_channel=nli, q=Q)
        results[name] = {
            "flagged": len(rep.findings),
            "findings": [{"input_id": f.input_id,
                          "channels": sorted(f.channels)}
                         for f in rep.findings],
            "channels": {n: {"flagged": c.n_flagged, "skipped": c.skipped}
                         for n, c in rep.channels.items()},
        }
        print(f"  {name:<14} flagged {len(rep.findings):>3}  "
              f"(expectation on record: 0)")

    gap_days = (time.time() - P1_CHECKPOINT.stat().st_mtime) / 86400
    report = {
        "purpose": "drift negative control (STD-008 protocol, MTH-026)",
        "run_id": prov.run_id, "config_hash": prov.config_hash,
        "git_commit": prov.git_commit, "git_dirty": prov.git_dirty,
        "system": MODEL, "system_digest": digest,
        "period1": {"stem": P1_STEM, "recorded": P1_RECORDED,
                    "digest": p1_digest},
        "gap_days": round(gap_days, 1),
        "n_inputs": N, "k": K, "q": Q,
        "nli_revision": str(_resolve_revision(nli_spec.hub_id)),
        "analysed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "comparisons": results,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"wrote {report_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
