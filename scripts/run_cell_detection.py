"""First end-to-end detector run against a real system under test.

Everything before this has been the detector on a stub with known ground truth,
or the cells on their own with no detector attached. This is the first time the
two meet, and the first time clustering and conformance execute on outputs a
model actually produced rather than on a synthetic corpus.

**This is a cost and integration run, not a validation run.** No threshold is
chosen here. The clustering threshold is 0.7 from MTH-020, q is 0.10 as
everywhere else, and the injected fault is one already in the frozen taxonomy.
Nothing observed here may be used to tune a channel: this run exists to find out
whether the pipeline executes, what it costs, and whether its output is coherent.

## The arms

A and A-prime are the same clean cell. B is the same cell with one tool serving
a stale view, which is fault class F5 and F11. Seeds are left **unset on every
arm**, which is the ordinary deployment case and what MTH-023 requires: a pinned
seed shared between the two baseline arms collapses the decoy arm, and the decoy
arm is the null.

## Ground truth

A stale view only matters where the staleness changes an answer. Asking the
faulty tool about a record whose value already matches the stale value returns
the truth, and the fault has not fired. `FaultActivation` records, per input,
whether any tool call actually returned something different from what the clean
toolset would have returned. That is the per-input activation label, and it is a
bench privilege that no real system ever gives you.
"""

from __future__ import annotations

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
from aprime.recorder import record  # noqa: E402

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
# a=0.17 and n=12, where flagging anything was arithmetically impossible.
N, K, Q = 30, 4, 0.10



def _ollama_digest(model: str) -> str:
    """The digest of the model actually loaded, so the tag is a pin.

    A tag can be repointed at new weights without changing its name, which is
    exactly the silent instrument change the pinned-instruments rail exists to
    prevent.
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
        details = body.get("details") or {}
        return str(details.get("digest") or "unresolved")
    except Exception:  # noqa: BLE001
        return "unresolved"


class FaultActivation:
    """The candidate arm, plus a record of where the fault actually fired.

    Wrapping rather than instrumenting the cell, because the cell is the system
    under test and must not know that it is being measured.
    """

    def __init__(self, cell: Cell, clean: ToolSet, faulty: ToolSet):
        self.cell = cell
        self.arm = cell.arm
        # Separate toolsets purely for the comparison, so that replaying a call
        # in order to diff it does not pollute the log of the ones under test.
        self._clean = clean
        self._faulty = faulty
        self.fired: dict[str, bool] = {}
        self.calls_seen = 0

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
        return r


def short(input_id: str) -> str:
    """banking-summary-lookup-000 -> lookup-000, for a readable listing."""
    parts = input_id.split("-")
    return "-".join(parts[-2:]) if len(parts) >= 2 else input_id


def main() -> int:
    t0 = time.perf_counter()
    pack = build_pack(DOMAIN, n_entities=18, seed=1)
    inputs = build_inputs(pack, n=N, seed=1, output_format=FORMAT)

    def chat():
        # seed deliberately unset; see the module docstring and MTH-023
        return OllamaChat(model=MODEL, host=HOST, keep_alive="10m",
                          num_ctx=8192, temperature=0.2, num_predict=512,
                          seed=None)

    def clean_tools():
        return ToolSet(pack)

    def stale_tools():
        return ToolSet(pack, stale=STALE_SHAPES)

    a = Cell(pack, FORMAT, chat(), "A", tools=clean_tools())
    ap = Cell(pack, FORMAT, chat(), "A_prime", tools=clean_tools())
    b_cell = Cell(pack, FORMAT, chat(), "B", tools=stale_tools())
    b = FaultActivation(b_cell, clean_tools(), stale_tools())

    # The revision is resolved without loading the model, so provenance can be
    # captured and printed up front while the model itself is loaded only once
    # recording is done. Holding a second model resident through the recording
    # puts two of them on one 8 GB card for no reason.
    nli_spec = next(s for s in NLI_MODELS if s.key == "deberta_mnli")
    nli_revision = _resolve_revision(nli_spec.hub_id)
    # provenance warned, correctly, that a bare tag is not a pin. Ollama returns
    # the digest as bare hex rather than sha256-prefixed (BCH-012).
    system_digest = _ollama_digest(MODEL)
    prov = capture(
        instruments={"predicate": "NLIEquivalence@0.7 on " + nli_spec.hub_id,
                     "nli_revision": str(nli_revision),
                     "system_model": MODEL + "@" + system_digest[:16]},
        params={"k": K, "q": Q, "n_inputs": N, "domain": DOMAIN,
                "output_format": FORMAT,
                "fault": "stale:" + ",".join(sorted(STALE_SHAPES)),
                "seed_policy": "unset on every arm (MTH-023)"},
        corpus=corpus_fingerprint([i.input_id for i in inputs]),
        notes={"purpose": "first end-to-end detector run on a real system; "
                          "cost and integration only, not validation"},
    )
    dirty = "  DIRTY" if prov.git_dirty else ""
    print("run " + prov.run_id)
    print("config " + prov.config_hash)
    print("git " + str(prov.git_commit)[:8] + dirty)
    print("nli " + nli_spec.hub_id + " @ " + str(nli_revision)[:12])
    print()
    print(f"{DOMAIN}/{FORMAT}, {N} inputs, k={K}, "
          f"fault stale:{','.join(sorted(STALE_SHAPES))}, seeds unset")
    print()

    # Checkpointed because recording is the expensive half by a wide margin and
    # the detector stage that follows it can fail. Without this, a failure in
    # the cheap half throws away the costly one. Resumable: rerun and it skips
    # what is already on disk.
    cp = ROOT / "results" / ("cell_detection_" + prov.run_id + ".jsonl")
    t_rec = time.perf_counter()
    rec = record(inputs, {"A": a, "A_prime": ap, "B": b}, k=K, checkpoint=cp)
    rec_s = time.perf_counter() - t_rec
    per = rec_s / max(1, len(rec.samples))
    print(f"recorded {len(rec.samples)} samples in {rec_s:.0f}s "
          f"({per:.1f}s each), interleaving gap {rec.interleaving_gap()}")
    print()

    activated = {i for i, fired in b.fired.items() if fired}
    quiet = set(b.fired) - activated
    print(f"fault fired on {len(activated)}/{N} inputs "
          f"({b.calls_seen} tool calls seen on the candidate arm)")
    print("  fired:     " + ", ".join(sorted(short(i) for i in activated)))
    print("  not fired: " + ", ".join(sorted(short(i) for i in quiet)))
    print()

    # Ollama first: the cell is done with, and leaving 6.5 GB resident while a
    # second model loads is how an 8 GB card runs out.
    OllamaChat(model=MODEL, host=HOST).release()
    nli = NLIChannel(nli_spec)
    t_det = time.perf_counter()
    # Both, and they are not the same thing. `predicate` is what decides
    # whether two outputs are the same mode; `nli_channel` is what scores
    # contradiction and directional entailment. The first run passed only
    # the predicate, so the two channels the inventory says carry the load
    # reported themselves skipped and the run measured the structured path
    # alone.
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
        print("nothing flagged. With clouds of 4 and 12 inputs that is a "
              "plausible outcome rather than a failure: the decoy arm sets "
              "every threshold, and there are few decoy pairs to set it from.")

    out = ROOT / "results" / ("cell_detection_" + prov.run_id + ".json")
    out.write_text(json.dumps({
        "run_id": prov.run_id, "config_hash": prov.config_hash,
        "git_commit": prov.git_commit, "git_dirty": prov.git_dirty,
        "params": {"domain": DOMAIN, "output_format": FORMAT, "n": N, "k": K,
                   "q": Q, "fault": "stale:" + ",".join(sorted(STALE_SHAPES)),
                   "seed_policy": "unset"},
        "instruments": {"system": MODEL, "system_digest": system_digest, "nli": nli_spec.hub_id,
                        "nli_revision": str(nli_revision), "threshold": 0.7},
        "timing_s": {"record": round(rec_s, 1), "detect": round(det_s, 1),
                     "total": round(time.perf_counter() - t0, 1)},
        "samples": len(rec.samples),
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
