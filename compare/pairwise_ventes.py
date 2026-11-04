"""Pairwise stage of the assistante-ventes campaign: Design R, four arms.

The pair is CMP-002's: llama3.2:3b (declared reference A, the app's
provisional default and pace leader) against phi4-mini (candidate B).
Sizing is CMP-001: n=40 language tasks, k=20 samples per arm, q=0.10.

Recording (CPU only, mirrors the deployment) is this file's own loop —
the engine's recorder speaks exactly three arms (ARMS, adapter.py §4 of
the cross-system proposal), and the comparator does not modify the
engine. Design R's layout is honoured directly: all four arms of one
(input, sample index) are called back to back in one atomic tuple, the
lead arm rotates over the roster, tuples are grouped by input (ENG-001),
and both models stay resident so no tuple straddles a model reload.

Scoring reuses the frozen pipeline through the public API: five
``detect()`` passes over arm relabelings of the same store —

  primary    A=m1a  A'=m1b  B=m2a   targets s(A,B), decoys s(A,A')  SELECTS
  reverse    A=m2a  A'=m2b  B=m1a   the reverse orientation         reported
  rep-AB'    A=m1a  A'=m1b  B=m2b   replicate target set s(A,B')    reported
  rep-A'B    A=m1b  A'=m1a  B=m2a   replicate target set s(A',B)    reported
  rep-A'B'   A=m1b  A'=m1a  B=m2b   replicate target set s(A',B')   reported

Two Design R reported quantities are NOT computed here and are named in
the report instead: the reverse selection against s(B,B') and the
cross-pooled (1+d/2)/t estimate both need the engine's pairing-aware
detect and r>1 estimator (proposal §4), which ride the MTH-027 freeze as
engine work. The arrays they need are in the store; computing them with
hand-rolled selector logic in a consumer seat would be exactly the
unvalidated statistics the rails forbid.

    python compare/pairwise_ventes.py              # plan, no calls
    python compare/pairwise_ventes.py --go         # record (CPU, ~2.6 h)
    python compare/pairwise_ventes.py --status     # progress of the store
    python compare/pairwise_ventes.py --stop       # stop at the next tuple
    python compare/pairwise_ventes.py --analyse    # score a complete store
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FIXTURES = HERE / "fixtures" / "messages.json"
RESULTS = HERE / "results"
STORE = RESULTS / "pairwise-ventes.jsonl"
META = RESULTS / "pairwise-ventes.meta.json"
REPORT = RESULTS / "pairwise-ventes.report.json"
REPORT_TXT = RESULTS / "pairwise-ventes.report.txt"
STOP_FLAG = RESULTS / "COMPARE.STOP"
OLLAMA = "http://127.0.0.1:11434"

REFERENCE = ("m1", "llama3.2:3b")   # A — declared before recording (CMP-003)
CANDIDATE = ("m2", "phi4-mini:latest")
ROSTER = ["m1a", "m1b", "m2a", "m2b"]
K, Q = 20, 0.10

# The deployment's own generation settings (ChatADV / the pace pass):
# temperature 0.2, 400-token budget, CPU only, no seed (MTH-023: mirror
# the deployment's seed policy and record the regime).
OPTIONS = {"temperature": 0.2, "num_predict": 400, "num_gpu": 0}
KEEP_ALIVE = "10m"
SECONDS_PER_TUPLE = 12.0  # pace medians: 2 x 2.8s + 2 x 3.0s, rounded up

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

PAIRINGS = {
    "primary":  {"m1a": "A", "m1b": "A_prime", "m2a": "B"},
    "reverse":  {"m2a": "A", "m2b": "A_prime", "m1a": "B"},
    "rep-AB2":  {"m1a": "A", "m1b": "A_prime", "m2b": "B"},
    "rep-A2B":  {"m1b": "A", "m1a": "A_prime", "m2a": "B"},
    "rep-A2B2": {"m1b": "A", "m1a": "A_prime", "m2b": "B"},
}


# ---------------------------------------------------------------- fixtures

def build_tasks() -> list[tuple[str, str]]:
    """(input_id, prompt) for all 40 language tasks, in fixture order."""
    msgs = json.loads(FIXTURES.read_text(encoding="utf-8"))
    out = [(m["id"], PROMPT_TRADUIRE.format(texte=m["text"]))
           for m in msgs["inbound"]]
    out += [(o["id"], PROMPT_REDIGER.format(consigne=o["brief"]))
            for o in msgs["outbound"]]
    return out


# ------------------------------------------------- pure planning helpers

def arm_order(tuple_index: int) -> list[str]:
    """Lead-arm rotation over the roster, one step per tuple.

    The engine rotates its three arms by idx %% 3 so no arm always pays
    the cold-start or the warm-cache position; the roster generalisation
    (proposal §4) is rotation over the roster's length."""
    off = tuple_index % len(ROSTER)
    return ROSTER[off:] + ROSTER[:off]


def complete_tuples(rows: list[dict]) -> set[tuple[str, int]]:
    """Tuples for which every roster arm holds a usable sample."""
    seen: dict[tuple[str, int], set[str]] = {}
    for r in rows:
        if r.get("error") is None and r.get("output"):
            seen.setdefault((r["input_id"], r["sample_idx"]), set()).add(r["arm"])
    return {key for key, arms in seen.items() if arms >= set(ROSTER)}


def plan_remaining(rows: list[dict], ids: list[str], k: int
                   ) -> list[tuple[int, str, int]]:
    """(global tuple index, input_id, sample_idx) still to record.

    Grouped by input, k tuples per input, in corpus order — the global
    index is stable across resumes, so the rotation each tuple gets does
    not depend on when it was recorded."""
    done = complete_tuples(rows)
    out = []
    g = 0
    for iid in ids:
        for s in range(k):
            if (iid, s) not in done:
                out.append((g, iid, s))
            g += 1
    return out


# ------------------------------------------------------------- ollama I/O

def api(path: str, payload: dict | None = None, timeout: int = 600):
    if payload is None:
        req = urllib.request.Request(OLLAMA + path)
    else:
        req = urllib.request.Request(
            OLLAMA + path, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def digests() -> dict[str, str]:
    have = {m["name"]: str(m.get("digest", "")) for m in
            api("/api/tags").get("models", [])}
    out = {}
    for _, tag in (REFERENCE, CANDIDATE):
        if tag not in have:
            raise SystemExit(f"model not on disk: {tag} (ollama pull it first)")
        out[tag] = have[tag]
    return out


def generate(tag: str, prompt: str) -> dict:
    t0 = time.perf_counter()
    r = api("/api/generate", {"model": tag, "prompt": prompt, "stream": False,
                              "options": OPTIONS, "keep_alive": KEEP_ALIVE})
    return {"output": r.get("response", ""),
            "latency_ms": round((time.perf_counter() - t0) * 1000, 1),
            "finish_reason": r.get("done_reason")}


def main_line_recorder_running() -> bool:
    """The night-chain collision guard, inverted: refuse to share Ollama
    with a main-line recording. One server serialises the two runs and
    pollutes both timings (MTH-015)."""
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "@(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq "
             "'python.exe' -and $_.CommandLine -match "
             "'run_study|run_cell_detection|run_drift_control' }).Count"],
            capture_output=True, text=True, timeout=60)
        return int(proc.stdout.strip() or 0) > 0
    except Exception:  # noqa: BLE001 — a broken guard must not block a run
        return False


# --------------------------------------------------------------- recording

def load_rows() -> list[dict]:
    if not STORE.exists():
        return []
    rows = []
    for line in STORE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def compact(rows: list[dict]) -> list[dict]:
    """Keep only samples belonging to complete tuples; drop partials so a
    resumed run re-records them whole (tuple-atomicity on read)."""
    done = complete_tuples(rows)
    return [r for r in rows if (r["input_id"], r["sample_idx"]) in done]


def cmd_record(go: bool) -> int:
    tasks = build_tasks()
    ids = [t[0] for t in tasks]
    prompts = dict(tasks)
    if len(set(prompts.values())) != len(ids):
        raise SystemExit("fixture prompts are not all distinct; dedup before "
                         "counting (study discipline) — fix the fixtures")

    rows = load_rows()
    todo = plan_remaining(rows, ids, K)
    total = len(ids) * K
    print(f"pairwise-ventes: {REFERENCE[1]} (A, reference) vs {CANDIDATE[1]} "
          f"(B), n={len(ids)} k={K} q={Q}")
    print(f"store: {len(complete_tuples(rows))}/{total} tuples complete, "
          f"{len(todo)} to record "
          f"(~{len(todo) * SECONDS_PER_TUPLE / 3600:.1f} h CPU)")
    if not go:
        print("plan only. Add --go to record.")
        return 0
    if STOP_FLAG.exists():
        print(f"stop flag present: {STOP_FLAG}. Delete it (--clear-stop) "
              "before recording.")
        return 2
    if main_line_recorder_running():
        print("REFUSING: a main-line recording (run_study / "
              "run_cell_detection / run_drift_control) is talking to this "
              "Ollama. One server would serialise both runs and pollute "
              "both timings (MTH-015). Rerun when it is done.")
        return 3
    if not todo:
        print("nothing to record; store is complete. Next: --analyse")
        return 0

    dig = digests()
    meta = {"reference": dict(zip(("key", "tag"), REFERENCE)),
            "candidate": dict(zip(("key", "tag"), CANDIDATE)),
            "roster": ROSTER, "n_inputs": len(ids), "k": K, "q": Q,
            "options": OPTIONS, "digests": dig,
            "seed_policy": "unset on every arm; mirrors the deployment "
                           "(MTH-023)",
            "mode": "CPU only (num_gpu: 0), both models resident",
            "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    if META.exists():
        old = json.loads(META.read_text(encoding="utf-8"))
        if old.get("digests") != dig:
            print("REFUSING: a model digest changed since this store was "
                  "started. Finishing the recording across a weight change "
                  "would hand the detector a drift it did not sign up for. "
                  "Archive the store and restart, or restore the weights.")
            print(f"  stored: {old.get('digests')}")
            print(f"  live:   {dig}")
            return 5
        meta["started_utc"] = old.get("started_utc", meta["started_utc"])
    META.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    # Preflight: one tiny call per model before a multi-hour run.
    for _, tag in (REFERENCE, CANDIDATE):
        r = generate(tag, "Réponds uniquement: OK")
        if not r["output"].strip():
            print(f"PREFLIGHT FAILED: {tag} returned empty text. Nothing "
                  "recorded.")
            return 4
    print("preflight ok; both models answering")

    rows = compact(rows)
    session = 1 + max((r.get("session", 0) for r in rows), default=-1)
    order = 1 + max((r.get("order", 0) for r in rows), default=-1)
    STORE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STORE.with_suffix(".jsonl.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(STORE)

    model_of = {"m1a": REFERENCE[1], "m1b": REFERENCE[1],
                "m2a": CANDIDATE[1], "m2b": CANDIDATE[1]}
    failures_in_a_row = 0
    t_start = time.perf_counter()
    done_now = 0
    with STORE.open("a", encoding="utf-8") as fh:
        for g, iid, s_idx in todo:
            if STOP_FLAG.exists():
                print(f"PAUSED by stop flag after {done_now} tuples. The "
                      "store resumes with --go.")
                break
            batch = []
            try:
                for arm in arm_order(g):
                    tag = model_of[arm]
                    r = generate(tag, prompts[iid])
                    if not r["output"].strip():
                        raise RuntimeError(f"{tag} returned empty text on "
                                           f"{iid}")
                    batch.append({"input_id": iid, "arm": arm,
                                  "sample_idx": s_idx, "order": order,
                                  "output": r["output"],
                                  "latency_ms": r["latency_ms"],
                                  "ts": time.time(),
                                  "model_id": f"{tag}@{dig[tag][:16]}",
                                  "finish_reason": r["finish_reason"],
                                  "error": None, "session": session})
                    order += 1
            except Exception as e:  # noqa: BLE001
                failures_in_a_row += 1
                print(f"  tuple ({iid}, {s_idx}) abandoned: {e} "
                      f"[{failures_in_a_row} in a row]")
                if failures_in_a_row >= 3:
                    print("three consecutive tuple failures; stopping. "
                          "Recorded tuples are on disk and resume.")
                    return 6
                continue
            failures_in_a_row = 0
            for row in batch:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            done_now += 1
            if done_now % 20 == 0:
                pace = (time.perf_counter() - t_start) / done_now
                left = (len(todo) - done_now) * pace / 3600
                print(f"  {done_now}/{len(todo)} tuples this session "
                      f"({pace:.1f}s/tuple, ~{left:.1f} h left)", flush=True)
    for _, tag in (REFERENCE, CANDIDATE):
        subprocess.run(["ollama", "stop", tag], capture_output=True,
                       timeout=120)
    rows = load_rows()
    n_done = len(complete_tuples(rows))
    print(f"store: {n_done}/{total} tuples complete")
    if n_done == total:
        print("recording COMPLETE. Next: --analyse (wants the GPU free "
              "for the NLI judge)")
    return 0


# ---------------------------------------------------------------- analyse

def cmd_analyse() -> int:
    sys.path.insert(0, str(ROOT / "src"))
    from aprime.net import enable_os_truststore
    enable_os_truststore()
    from aprime.clustering import NLIEquivalence
    from aprime.detect import detect
    from aprime.probes.channels import NLI_MODELS, NLIChannel
    from aprime.provenance import capture, corpus_fingerprint
    from aprime.recorder import Recording, Sample

    tasks = build_tasks()
    ids = [t[0] for t in tasks]
    rows = load_rows()
    done = complete_tuples(rows)
    total = len(ids) * K
    if len(done) != total:
        print(f"REFUSING to analyse a partial store: {len(done)}/{total} "
              "tuples. Both label losses were partial-state lessons "
              "(BCH-018); record to completion first (--go).")
        return 2
    meta = json.loads(META.read_text(encoding="utf-8"))

    prov = capture(
        instruments={"predicate": "NLIEquivalence@0.7",
                     "reference": f"{REFERENCE[1]}@"
                                  f"{meta['digests'][REFERENCE[1]][:16]}",
                     "candidate": f"{CANDIDATE[1]}@"
                                  f"{meta['digests'][CANDIDATE[1]][:16]}"},
        params={"design": "R (MTH-027)", "n_inputs": len(ids), "k": K,
                "q": Q, "roster": ROSTER,
                "seed_policy": meta["seed_policy"]},
        corpus=corpus_fingerprint(ids, dict(tasks)),
        notes={"purpose": "assistante-ventes pairwise (CMP-001/CMP-002)",
               "campaign": "docs/compare/campaign-assistante.md"},
        warn_if_dirty=False,
    )

    keep = {(r["input_id"], r["sample_idx"]) for r in rows} & done
    usable = [r for r in rows
              if (r["input_id"], r["sample_idx"]) in keep]
    nli_spec = next(s for s in NLI_MODELS if s.key == "deberta_mnli")
    nli = NLIChannel(nli_spec)
    predicate = NLIEquivalence(nli, threshold=0.7)

    results: dict[str, dict] = {}
    texts: dict[str, str] = {}
    for name, mapping in PAIRINGS.items():
        samples = [Sample(**{**r, "arm": mapping[r["arm"]]})
                   for r in usable if r["arm"] in mapping]
        rec = Recording(samples=samples, k=K, input_ids=ids)
        rep = detect(rec, predicate=predicate, nli_channel=nli, q=Q)
        results[name] = {
            "selects": name == "primary",
            "arms": mapping,
            "flagged": rep.n_flagged,
            "findings": [{"input_id": f.input_id, "stratum": f.stratum,
                          "channels": {k: float(v)
                                       for k, v in f.channels.items()}}
                         for f in rep.findings],
            "channels": {n: {"flagged": c.n_flagged,
                             "skipped": c.skipped,
                             "reading": c.reading(Q)}
                         for n, c in rep.channels.items()},
            "notes": rep.notes, "short_clouds": rep.short_clouds,
            "interleaving_gap": rec.interleaving_gap(),
            "cost": rep.cost,
        }
        texts[name] = rep.text()
        print(f"  {name:<9} flagged {rep.n_flagged:>3}"
              + ("  <- the selection" if name == "primary" else "  (reported)"))

    report = {
        "purpose": "assistante-ventes pairwise, Design R four-arm pair",
        "run_id": prov.run_id, "config_hash": prov.config_hash,
        "git_commit": prov.git_commit, "git_dirty": prov.git_dirty,
        "reference_A": meta["reference"], "candidate_B": meta["candidate"],
        "digests": meta["digests"], "n_inputs": len(ids), "k": K, "q": Q,
        "recorded": {"started_utc": meta.get("started_utc"),
                     "sessions": 1 + max(r.get("session", 0)
                                         for r in usable),
                     "mode": meta.get("mode")},
        "nli_hub_id": nli_spec.hub_id,
        "analysed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pairings": results,
        "pending_design_r_quantities": [
            "reverse selection against s(B,B') — needs detect() to take "
            "an explicit pairing (proposal §4); arrays are in the store",
            "cross-pooled (1+d/2)/t at the selection's cut — needs the "
            "r>1 estimator generalisation riding the MTH-027 freeze",
        ],
        "next": "flagged inputs go to blind human judgment "
                "(measurement plan item 3)",
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    REPORT_TXT.write_text(
        "\n\n".join(f"=== {n} ===\n{t}" for n, t in texts.items()),
        encoding="utf-8")
    print(f"wrote {REPORT.relative_to(ROOT)} and "
          f"{REPORT_TXT.relative_to(ROOT)}")
    print(f"primary flagged {results['primary']['flagged']} of {len(ids)} "
          f"inputs at q={Q}")
    return 0


# ------------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--go", action="store_true", help="record")
    ap.add_argument("--analyse", action="store_true",
                    help="score a complete store (loads the NLI judge)")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--stop", action="store_true",
                    help="ask a running recording to stop at the next tuple")
    ap.add_argument("--clear-stop", action="store_true")
    args = ap.parse_args()

    if args.stop:
        RESULTS.mkdir(parents=True, exist_ok=True)
        STOP_FLAG.write_text("stop", encoding="utf-8")
        print(f"stop flag written: {STOP_FLAG}")
        return 0
    if args.clear_stop:
        STOP_FLAG.unlink(missing_ok=True)
        print("stop flag cleared")
        return 0
    if args.status:
        ids = [t[0] for t in build_tasks()]
        n = len(complete_tuples(load_rows()))
        print(f"{n}/{len(ids) * K} tuples complete "
              f"({STORE if STORE.exists() else 'no store yet'})")
        return 0
    if args.analyse:
        return cmd_analyse()
    return cmd_record(go=args.go)


if __name__ == "__main__":
    raise SystemExit(main())
