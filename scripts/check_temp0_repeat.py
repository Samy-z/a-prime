"""Eight identical calls at temperature 0: is this serving stack repeatable?

The titration protocol's temperature point needs this measured before any
temperature dial turns (methods STATE): MTH-015 recorded that temperature-0
decoding is NOT deterministic on batched serving infrastructure in general
(1000 completions of one prompt gave 80 unique outputs elsewhere), and the
design of the entropy dial reads differently depending on whether THIS stack
at temperature 0 collapses to one output, a few, or many.

Eight sequential invocations of one banking-agent input, temperature 0, seed
unset, same options otherwise as the study's `chat()`. Deliberately NOT an
interleaved recording and not a study arm: a determinism probe, where
back-to-back same-arm calls are exactly the point. Output lands under
`results/study/` with full provenance (runtime state is data).

    python scripts/check_temp0_repeat.py        # plan only
    python scripts/check_temp0_repeat.py --go   # ~3 min of GPU
"""

from __future__ import annotations

import argparse
import json
import subprocess
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
from aprime.normalize import normalise  # noqa: E402
from aprime.provenance import capture, corpus_fingerprint, row_provenance  # noqa: E402

HOST = __import__("os").environ.get("APRIME_OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL = "granite4.2:8b"
REPEATS = 8
OUT_DIR = ROOT / "results" / "study"

# Matches the recorder-collision guard every night wrapper uses. This script's
# own command line contains none of these names.
_RECORDER_MATCH = "run_study|run_cell_detection|run_drift_control|pairwise_ventes"


def recorders_running() -> int:
    """How many recorder processes are live; -1 when the check itself failed."""
    cmd = ["powershell", "-NoProfile", "-Command",
           "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "
           f"'python.exe' -and $_.CommandLine -match '{_RECORDER_MATCH}' "
           "}).Count"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return int(out.stdout.strip() or "0")
    except Exception:  # noqa: BLE001
        return -1


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


def common_prefix_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--go", action="store_true",
                    help="actually call the model; without it, print the plan")
    args = ap.parse_args()

    pack = build_pack("banking", n_entities=18, seed=1)
    inputs = build_inputs(pack, n=40, seed=1, output_format="agent")
    inv = inputs[0]

    print(f"temperature-0 repeat check: {REPEATS} identical calls, input "
          f"{inv.input_id!r}, banking-agent, {MODEL} at {HOST}")
    if not args.go:
        print("this is a plan, not a run. Add --go to call the model "
              f"({REPEATS} agent episodes, roughly 3 minutes).")
        return 0

    n = recorders_running()
    if n != 0:
        print(f"REFUSING: recorder check reports {n} "
              f"({'live recorder process(es)' if n > 0 else 'check failed'}). "
              "A determinism probe must not share the server with a "
              "recording (MTH-015).")
        return 3

    digest = ollama_digest()
    if digest == "unresolved":
        print(f"REFUSING: {MODEL} is not served at {HOST}.")
        return 3

    chat = OllamaChat(model=MODEL, host=HOST, keep_alive="2m", num_ctx=8192,
                      temperature=0.0, top_p=0.9, top_k=40, num_predict=512,
                      seed=None, think=False)
    cell = Cell(pack, "agent", chat, "A", tools=ToolSet(pack))

    rows = []
    for i in range(REPEATS):
        t0 = time.perf_counter()
        try:
            resp = cell.invoke(inv)
            rows.append({"repeat": i, "output": resp.output,
                         "latency_ms": resp.trace.latency_ms,
                         "finish_reason": resp.trace.finish_reason,
                         "steps": resp.trace.steps,
                         "tools_called": list(resp.trace.tools_called),
                         "error": resp.trace.error})
        except Exception as exc:  # noqa: BLE001
            rows.append({"repeat": i, "output": "",
                         "latency_ms": (time.perf_counter() - t0) * 1000.0,
                         "finish_reason": None, "steps": 0,
                         "tools_called": [],
                         "error": f"{type(exc).__name__}: {exc}"})
        print(f"  call {i + 1}/{REPEATS}: "
              f"{(time.perf_counter() - t0):.1f}s, "
              f"{len(rows[-1]['output'])} chars"
              f"{', ERROR' if rows[-1]['error'] else ''}")
    chat.release()

    good = [r["output"] for r in rows if not r["error"]]
    raw_distinct = len(set(good))
    norm_distinct = len({normalise(o) for o in good})
    prefixes = ([common_prefix_len(good[0], o) for o in good[1:]]
                if len(good) > 1 else [])

    prov = capture(
        instruments={"system_model": MODEL + "@" + digest[:16]},
        params={"purpose": "temperature-0 repeat check (titration prerequisite)",
                "repeats": REPEATS, "temperature": 0.0, "seed": None,
                "input_id": inv.input_id, "domain": "banking",
                "output_format": "agent"},
        corpus=corpus_fingerprint([inv.input_id]),
        notes={"model_host": HOST},
        warn_if_dirty=False,
    )
    verdict = {
        **row_provenance(prov, system=MODEL, system_digest=digest),
        "repeats": REPEATS, "errored": sum(1 for r in rows if r["error"]),
        "raw_distinct": raw_distinct, "normalised_distinct": norm_distinct,
        "output_lengths": [len(r["output"]) for r in rows],
        "common_prefix_with_first": prefixes,
        "outputs": rows,
        "analysed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"temp0-repeat.{prov.config_hash}.json"
    out.write_text(json.dumps(verdict, indent=2), encoding="utf-8")

    print()
    print(f"of {len(good)} usable outputs: {raw_distinct} distinct raw, "
          f"{norm_distinct} distinct after normalisation")
    if prefixes:
        print(f"divergence from the first output starts at character "
              f"{min(prefixes)} (earliest) / {max(prefixes)} (latest)")
    print("reading: 1 distinct means this stack is repeatable at temperature "
          "0 and the dial's low end is a point mass; more than 1 means "
          "temperature 0 still carries serving noise here (MTH-015's general "
          "finding), and the titration's entropy dial starts above a floor.")
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
