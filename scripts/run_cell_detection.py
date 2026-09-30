"""End-to-end detector run against a real system under test, pausable.

The detector has only ever run on a stub with known ground truth, and the cells
have only ever run with no detector attached. This is where the two meet, and
where clustering and conformance execute on outputs a model actually produced
rather than on a synthetic corpus.

**This is a cost and integration run, not a validation run.** No threshold is
chosen here. The clustering threshold is 0.7 from MTH-020, q is 0.10 as
everywhere else, and the injected fault is one already in the frozen taxonomy.
Nothing observed here may be used to tune a channel.

## Pausing

Recording is the expensive half by two orders of magnitude, so it is
checkpointed and it can be stopped at a triple boundary and picked up later.

    python scripts/run_cell_detection.py             # start, or resume
    python scripts/run_cell_detection.py --status    # how far along, no GPU
    python scripts/run_cell_detection.py --stop      # ask a running one to stop
    python scripts/run_cell_detection.py --clear-stop

The checkpoint is keyed on the **configuration hash**, not on the run
timestamp, because a checkpoint that no rerun can find is not a checkpoint.
Change the corpus, k, the fault or an instrument and the key changes with it, so
a resume can never silently mix work from two different configurations.

## The arms

A and A-prime are the same clean cell. B is the same cell reading from a stale
knowledge base, which is fault classes F5 and F11. Seeds are left **unset on
every arm**: that is the ordinary deployment case, and MTH-023 requires it,
because two baseline arms sharing a pinned seed collapse the decoy arm, and the
decoy arm is the null.

## Ground truth

A stale view only matters where the staleness changes an answer. Asking a stale
tool about a record whose value already matches the stale one returns the truth,
and the fault has not fired. `FaultActivation` replays every tool call against
both a clean and a stale toolset and records where they actually diverged.

**Those labels are persisted next to the checkpoint.** A resumed session never
re-invokes the triples it skips, so activation learned in an earlier session
would otherwise be lost and the run would report the fault as firing on less of
the corpus than it did. It is a bench privilege no real system gives you, and
losing half of it silently would be worse than not having it at all.
"""

from __future__ import annotations

import argparse
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
from aprime.probes.channels import (  # noqa: E402
    NLI_MODELS,
    NLIChannel,
    _resolve_revision,
)
from aprime.provenance import capture, corpus_fingerprint  # noqa: E402
from aprime.recorder import (  # noqa: E402
    RunPaused,
    record,
    recording_progress,
    stop_requested,
)

HOST = "http://127.0.0.1:11434"
MODEL = "granite4.2:8b"
DOMAIN = "banking"
FORMAT = "summary"

# A stale knowledge base is stale for every read from it, not for one tool.
# Staling a single shape fired on 2 of 12 inputs (run 20260929T230714Z), and the
# floor below cannot be reached at that activation rate. The broad version is
# also the more realistic reading of fault classes F5 and F11.
STALE_SHAPES = frozenset({"lookup", "search", "history", "verify"})

# Sizing follows from the FDR estimator rather than from taste. The
# Barber-Candes correction makes the estimate (1 + decoys_above) / targets_above
# (fdr.py:52), so even with zero decoys above the threshold the best achievable
# estimate is 1/targets_above. At q=0.10 nothing can be reported until ten
# inputs are selected, so at least ten inputs must genuinely have changed, and
# with activation rate `a` the corpus must be at least 10/a. The first run had
# a=0.17 and n=12, where flagging anything was arithmetically impossible
# (MTH-024).
N, K, Q = 40, 6, 0.10

RUNS = ROOT / "results" / "recordings"

# Measured on this machine against this model, summary format: 4.1s per
# invocation, three arms per triple. Used only to estimate time remaining.
SECONDS_PER_INVOCATION = 4.1


def _ollama_digest(model: str) -> str:
    """The digest of the model actually loaded, so that the tag is a pin.

    A tag can be repointed at new weights without changing its name, which is
    exactly the silent instrument change the pinned-instruments rail exists to
    prevent. Ollama returns it as bare hex, not sha256-prefixed (BCH-012).
    """
    import urllib.request

    try:
        req = urllib.request.Request(
            HOST + "/api/show",
            data=json.dumps({"model": model}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as r:
            body = json.loads(r.read().decode())
        for key in ("digest", "sha256"):
            if body.get(key):
                return str(body[key])
        return str((body.get("details") or {}).get("digest") or "unresolved")
    except Exception:  # noqa: BLE001
        return "unresolved"


class FaultActivation:
    """The candidate arm, plus a durable record of where the fault fired.

    Wrapping rather than instrumenting the cell, because the cell is the system
    under test and must not know that it is being measured.
    """

    def __init__(self, cell: Cell, clean: ToolSet, faulty: ToolSet, store: Path):
        self.cell = cell
        self.arm = cell.arm
        # Separate toolsets purely for the comparison, so that replaying a call
        # in order to diff it does not pollute the log of the ones under test.
        self._clean = clean
        self._faulty = faulty
        self._store = store
        self.calls_seen = 0
        self.fired: dict[str, bool] = {}
        if store.exists():
            try:
                loaded = json.loads(store.read_text(encoding="utf-8"))
                self.fired = {k: bool(v) for k, v in loaded.items()}
            except (ValueError, OSError):
                self.fired = {}

    def invoke(self, inv):
        log = self.cell.tools.calls
        before = len(log)
        r = self.cell.invoke(inv)
        differed = False
        for name, args in log[before:]:
            self.calls_seen += 1
            clean = self._clean.call(name, dict(args))
            faulty = self._faulty.call(name, dict(args))
            if clean != faulty:
                differed = True
        self.fired[inv.input_id] = self.fired.get(inv.input_id, False) or differed
        self._save()
        return r

    def _save(self) -> None:
        # Written every invocation. It is a few hundred bytes, and the
        # alternative is losing the labels to whatever stops the run.
        try:
            self._store.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._store.with_suffix(".tmp")
            tmp.write_text(json.dumps(self.fired), encoding="utf-8")
            tmp.replace(self._store)
        except OSError:
            pass


def short(input_id: str) -> str:
    """banking-summary-lookup-000 -> lookup-000, for a readable listing."""
    parts = input_id.split("-")
    return "-".join(parts[-2:]) if len(parts) >= 2 else input_id


def minutes_left(remaining_triples: int) -> float:
    return remaining_triples * 3 * SECONDS_PER_INVOCATION / 60


def build() -> dict:
    """Everything the run needs, plus its configuration identity."""
    pack = build_pack(DOMAIN, n_entities=18, seed=1)
    inputs = build_inputs(pack, n=N, seed=1, output_format=FORMAT)
    fault = "stale:" + ",".join(sorted(STALE_SHAPES))

    nli_spec = next(s for s in NLI_MODELS if s.key == "deberta_mnli")
    nli_revision = _resolve_revision(nli_spec.hub_id)
    system_digest = _ollama_digest(MODEL)

    prov = capture(
        instruments={"predicate": "NLIEquivalence@0.7 on " + nli_spec.hub_id,
                     "nli_revision": str(nli_revision),
                     "system_model": MODEL + "@" + system_digest[:16]},
        params={"k": K, "q": Q, "n_inputs": N, "domain": DOMAIN,
                "output_format": FORMAT, "fault": fault,
                "seed_policy": "unset on every arm (MTH-023)"},
        corpus=corpus_fingerprint([i.input_id for i in inputs]),
        notes={"purpose": "end-to-end detector run on a real system"},
    )
    return {"pack": pack, "inputs": inputs, "fault": fault, "prov": prov,
            "nli_spec": nli_spec, "nli_revision": nli_revision,
            "system_digest": system_digest,
            "checkpoint": RUNS / (prov.config_hash + ".jsonl"),
            "activation": RUNS / (prov.config_hash + ".activation.json"),
            "stop_flag": RUNS / (prov.config_hash + ".STOP")}


def cmd_status(cfg: dict) -> int:
    p = recording_progress(cfg["checkpoint"], cfg["inputs"], K)
    print("config " + cfg["prov"].config_hash)
    print(f"{DOMAIN}/{FORMAT}, {N} inputs, k={K}, {cfg['fault']}")
    print(f"recorded {p['done']}/{p['planned']} triples "
          f"({p['fraction']:.0%}), {p['remaining']} to go, "
          f"{p.get('sessions', 0)} session(s) so far")
    if p.get("stale_triples"):
        print(f"  {p['stale_triples']} triples on disk belong to a different "
              f"plan and are ignored")
    print(f"  roughly {minutes_left(p['remaining']):.0f} min of GPU left")
    print(f"  stop flag {'SET' if cfg['stop_flag'].exists() else 'not set'}")
    print("  checkpoint " + str(cfg["checkpoint"]))
    return 0


def cmd_stop(cfg: dict) -> int:
    cfg["stop_flag"].parent.mkdir(parents=True, exist_ok=True)
    cfg["stop_flag"].write_text("stop requested\n", encoding="utf-8")
    print("stop requested. A running recording will finish the triple it is on "
          "and exit, leaving everything it has on disk.")
    print("clear it with --clear-stop before starting again, or the next run "
          "will stop immediately.")
    return 0


def cmd_clear_stop(cfg: dict) -> int:
    cfg["stop_flag"].unlink(missing_ok=True)
    print("stop flag cleared")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="End-to-end detector run against a real cell, pausable.")
    parser.add_argument("--status", action="store_true",
                        help="report progress and exit, touching no model")
    parser.add_argument("--stop", action="store_true",
                        help="ask a running recording to stop at the next triple")
    parser.add_argument("--clear-stop", action="store_true",
                        help="clear the stop flag so a run can start")
    args = parser.parse_args()

    t0 = time.perf_counter()
    cfg = build()
    if args.status:
        return cmd_status(cfg)
    if args.stop:
        return cmd_stop(cfg)
    if args.clear_stop:
        return cmd_clear_stop(cfg)

    prov, inputs, pack = cfg["prov"], cfg["inputs"], cfg["pack"]
    if cfg["stop_flag"].exists():
        print("the stop flag is set, so this run would stop immediately. "
              "Clear it with --clear-stop.")
        return 1

    def chat():
        # seed deliberately unset; see the module docstring and MTH-023
        return OllamaChat(model=MODEL, host=HOST, keep_alive="10m",
                          num_ctx=8192, temperature=0.2, num_predict=512,
                          seed=None)

    a = Cell(pack, FORMAT, chat(), "A", tools=ToolSet(pack))
    ap = Cell(pack, FORMAT, chat(), "A_prime", tools=ToolSet(pack))
    b_cell = Cell(pack, FORMAT, chat(), "B",
                  tools=ToolSet(pack, stale=STALE_SHAPES))
    b = FaultActivation(b_cell, ToolSet(pack),
                        ToolSet(pack, stale=STALE_SHAPES), cfg["activation"])

    print("run " + prov.run_id)
    print("config " + prov.config_hash)
    print("git " + str(prov.git_commit)[:8] + ("  DIRTY" if prov.git_dirty else ""))
    print("nli " + cfg["nli_spec"].hub_id + " @ " + str(cfg["nli_revision"])[:12])
    print("system " + MODEL + " @ " + cfg["system_digest"][:12])
    print()
    print(f"{DOMAIN}/{FORMAT}, {N} inputs, k={K}, {cfg['fault']}, seeds unset")
    before = recording_progress(cfg["checkpoint"], inputs, K)
    if before["done"]:
        print(f"resuming: {before['done']}/{before['planned']} triples already "
              f"on disk, roughly {minutes_left(before['remaining']):.0f} min left")
    print()

    t_rec = time.perf_counter()
    try:
        rec = record(inputs, {"A": a, "A_prime": ap, "B": b}, k=K,
                     checkpoint=cfg["checkpoint"], progress_every=10,
                     should_stop=stop_requested(cfg["stop_flag"]))
    except RunPaused as paused:
        OllamaChat(model=MODEL, host=HOST).release()
        p = recording_progress(cfg["checkpoint"], inputs, K)
        print()
        print("PAUSED. " + str(paused))
        print(f"  {p['done']}/{p['planned']} triples done ({p['fraction']:.0%}), "
              f"roughly {minutes_left(p['remaining']):.0f} min of GPU left")
        print("  nothing was analysed. A partial recording gives the detector "
              "short clouds and fewer decoys, and its report would look "
              "completely ordinary.")
        print("  resume with --clear-stop, then rerun this script.")
        return 2
    rec_s = time.perf_counter() - t_rec
    per = rec_s / max(1, len(rec.samples))
    print(f"recorded {len(rec.samples)} samples, {rec_s:.0f}s this session "
          f"({per:.1f}s each), interleaving gap {rec.interleaving_gap()}, "
          f"{rec.sessions} session(s)")
    print()

    activated = {i for i, fired in b.fired.items() if fired}
    quiet = set(b.fired) - activated
    print(f"fault fired on {len(activated)}/{len(b.fired)} labelled inputs "
          f"({b.calls_seen} tool calls seen this session)")
    if len(b.fired) < N:
        print(f"  {N - len(b.fired)} inputs carry no label: recorded before the "
              f"labels were persisted, so treat the rate as a lower bound")
    print("  fired:     " + ", ".join(sorted(short(i) for i in activated)))
    print("  not fired: " + ", ".join(sorted(short(i) for i in quiet)))
    print()

    # Ollama first: the cell is done with, and leaving 6.5 GB resident while a
    # second model loads is how an 8 GB card runs out.
    OllamaChat(model=MODEL, host=HOST).release()
    nli = NLIChannel(cfg["nli_spec"])
    t_det = time.perf_counter()
    # Both, and they are not the same argument. `predicate` decides whether two
    # outputs are the same mode; `nli_channel` scores contradiction and
    # directional entailment. The first run passed only the predicate, so the
    # two channels the inventory says carry the load reported themselves
    # skipped and the run measured the structured path alone.
    rep = detect(rec, predicate=NLIEquivalence(nli, threshold=0.7),
                 nli_channel=nli, q=Q)
    det_s = time.perf_counter() - t_det
    print(rep.text())
    print()
    print(f"detector stage {det_s:.0f}s")

    flagged = {f.input_id for f in rep.findings}
    if flagged:
        tp = len(flagged & activated)
        print()
        print("against per-input activation (a bench privilege):")
        print(f"  {tp}/{len(flagged)} flagged inputs had the fault fire "
              f"-> realised FDR {1 - tp / len(flagged):.3f} against q={Q}")
        if activated:
            print(f"  recall {tp}/{len(activated)} = {tp / len(activated):.0%}")
    else:
        print()
        print(f"nothing flagged. At q={Q} the estimator cannot report fewer "
              f"than {int(round(1 / Q))} findings (MTH-024), so an empty report "
              f"says nothing unless at least that many inputs genuinely "
              f"changed. {len(activated)} did.")

    out = ROOT / "results" / ("cell_detection_" + prov.run_id + ".json")
    out.write_text(json.dumps({
        "run_id": prov.run_id, "config_hash": prov.config_hash,
        "git_commit": prov.git_commit, "git_dirty": prov.git_dirty,
        "params": {"domain": DOMAIN, "output_format": FORMAT, "n": N, "k": K,
                   "q": Q, "fault": cfg["fault"], "seed_policy": "unset"},
        "instruments": {"system": MODEL, "system_digest": cfg["system_digest"],
                        "nli": cfg["nli_spec"].hub_id,
                        "nli_revision": str(cfg["nli_revision"]),
                        "threshold": 0.7},
        "timing_s": {"record_this_session": round(rec_s, 1),
                     "detect": round(det_s, 1),
                     "total_this_session": round(time.perf_counter() - t0, 1)},
        "samples": len(rec.samples),
        "sessions": rec.sessions,
        "activation": {i: bool(v) for i, v in sorted(b.fired.items())},
        "cost": rep.cost,
        "channels": {n: {"flagged": c.n_flagged, "skipped": c.skipped}
                     for n, c in rep.channels.items()},
        "findings": [{"input_id": f.input_id, "channel": f.channel}
                     for f in rep.findings],
        "notes": rep.notes,
    }, indent=2), encoding="utf-8")
    print("wrote " + out.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
