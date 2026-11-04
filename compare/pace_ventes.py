"""Pace and footprint pass for the assistante-ventes campaign (CMP seat).

Measures, per 1-4B candidate, what the reference office PC cares about: how
long a translation or an e-mail draft takes on CPU ONLY (`num_gpu: 0`, so
the dev machine's GPU flatters nobody), tokens per second, and the model's
resident size. No aprime imports: measurement plan item 1 of
docs/compare/campaign-assistante.md needs no detector, and
tests/test_compare_boundary.py holds the seat to that.

Resumable: a model already in the results file is skipped, so a stopped run
relaunches without repeating pulls or calls. Pull failures are recorded as
results ("unavailable"), never fatal: a candidate whose Ollama tag does not
exist is a finding about the pool, not a crash.

    python compare/pace_ventes.py            # pulls missing models, measures all
    python compare/pace_ventes.py --no-pull  # measure only what is on disk
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "messages.json"
RESULTS = HERE / "results" / "pace-2026-11.json"
OLLAMA = "http://127.0.0.1:11434"

# (name we report, Ollama tags to try in order). Tags come from the 2026
# research pass and may be wrong: a miss is recorded, not fixed silently.
CANDIDATES = [
    ("qwen3.5-4b",    ["qwen3.5:4b"]),
    ("llama3.2-3b",   ["llama3.2:3b"]),
    ("smollm3-3b",    ["smollm3:3b", "smollm3"]),
    ("phi4-mini",     ["phi4-mini", "phi4-mini:3.8b", "phi-4-mini"]),
    ("lfm2.5-2.6b",   ["lfm2.5:2.6b", "lfm2.5"]),
    ("ministral3-3b", ["ministral-3:3b"]),
]

PROMPT_TRADUIRE = (
    "Tu es l'assistante d'une société française de pièces aéronautiques. "
    "Traduis fidèlement le message client suivant en français professionnel. "
    "Ne commente pas, n'ajoute rien, donne seulement la traduction.\n\n"
    "Message:\n{texte}")
PROMPT_REDIGER = (
    "Tu es l'assistante des ventes d'une société française de pièces "
    "aéronautiques. Rédige un e-mail professionnel, poli et concis en "
    "français selon la consigne. Donne uniquement l'e-mail, avec un objet "
    "sur la première ligne.\n\nConsigne:\n{consigne}")


def api(path: str, payload: dict | None = None, timeout: int = 600):
    if payload is None:
        req = urllib.request.Request(OLLAMA + path)
    else:
        req = urllib.request.Request(
            OLLAMA + path, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def on_disk() -> dict[str, int]:
    return {m["name"]: m.get("size", 0) for m in api("/api/tags").get("models", [])}


def ensure(tags: list[str], pull: bool) -> tuple[str | None, str]:
    have = on_disk()
    for tag in tags:
        if tag in have:
            return tag, "already on disk"
    if not pull:
        return None, "not on disk (--no-pull)"
    for tag in tags:
        proc = subprocess.run(["ollama", "pull", tag],
                              capture_output=True, text=True, timeout=3600)
        if proc.returncode == 0:
            return tag, "pulled"
    return None, "no tag found: " + ", ".join(tags)


def tasks() -> list[tuple[str, str]]:
    msgs = json.loads(FIXTURES.read_text(encoding="utf-8"))
    out = [(m["id"], PROMPT_TRADUIRE.format(texte=m["text"]))
           for m in msgs["inbound"]]
    out += [(o["id"], PROMPT_REDIGER.format(consigne=o["brief"]))
            for o in msgs["outbound"]]
    return out


def measure(tag: str) -> dict:
    rows = []
    for task_id, prompt in tasks():
        t0 = time.perf_counter()
        r = api("/api/generate", {
            "model": tag, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.2, "num_predict": 400, "num_gpu": 0},
            "keep_alive": "2m"})
        wall = time.perf_counter() - t0
        evald = r.get("eval_duration", 0)
        rows.append({
            "task": task_id, "wall_s": round(wall, 2),
            "out_tokens": r.get("eval_count"),
            "tok_per_s": round(r.get("eval_count", 0) / (evald / 1e9), 2)
                         if evald else None,
            "out_chars": len(r.get("response", "")),
        })
        print(f"    {task_id}: {wall:6.1f}s  "
              f"{rows[-1]['tok_per_s'] or '?'} tok/s", flush=True)
    subprocess.run(["ollama", "stop", tag], capture_output=True, timeout=120)
    walls = sorted(x["wall_s"] for x in rows)
    toks = sorted(x["tok_per_s"] for x in rows if x["tok_per_s"])
    return {"tasks": rows,
            "median_wall_s": walls[len(walls) // 2],
            "median_tok_per_s": toks[len(toks) // 2] if toks else None}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--no-pull", action="store_true")
    args = ap.parse_args()

    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    results = (json.loads(RESULTS.read_text(encoding="utf-8"))
               if RESULTS.exists() else
               {"purpose": "pace pass, campaign-assistante measurement plan 1",
                "mode": "CPU only (num_gpu: 0) on the dev machine",
                "models": {}})

    for name, tags in CANDIDATES:
        if results["models"].get(name, {}).get("status") == "complete":
            print(f"{name}: already measured, skipping")
            continue
        print(f"{name}: resolving ({', '.join(tags)})", flush=True)
        tag, how = ensure(tags, pull=not args.no_pull)
        if tag is None:
            results["models"][name] = {"status": "unavailable", "detail": how}
        else:
            size = on_disk().get(tag, 0)
            print(f"  {tag} ({how}), {size / 1e9:.1f} GB — measuring 14 tasks")
            try:
                m = measure(tag)
                results["models"][name] = {
                    "status": "complete", "tag": tag, "size_gb":
                    round(size / 1e9, 2), **m}
            except Exception as e:  # noqa: BLE001
                results["models"][name] = {"status": "errored",
                                           "detail": str(e)[:300]}
        RESULTS.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        print(f"  saved -> {RESULTS.name}", flush=True)

    print("\nSummary (median per task, CPU only):")
    for name, r in results["models"].items():
        if r.get("status") == "complete":
            print(f"  {name:<14} {r['size_gb']:>5.2f} GB  "
                  f"{r['median_wall_s']:>6.1f} s/task  "
                  f"{r['median_tok_per_s'] or '?':>6} tok/s")
        else:
            print(f"  {name:<14} {r['status']}: {r.get('detail', '')[:60]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
