"""The cell factorial: every domain crossed with every output format, pausable.

One cell is a domain and an output format. Nine of them make the grid the
transfer question is asked over, and this records and analyses them as one job
that can be stopped and resumed.

## Read the estimate before starting

A full factorial is **not** an overnight job at useful sizes. Measured per
invocation against a live 8B model: summary 4.8s, extraction 7.1s, agent 16.9s.
Three arms per triple, k triples per input:

| size | nine cells, one candidate |
|---|---|
| n=30 k=4 | about 8.6 h |
| n=40 k=4 | about 11.5 h |
| n=40 k=6 | about 17.2 h |

The agent format alone is 3.5 times the cost of summary and accounts for well
over half of any full run. So this script always prints its estimate, and
refuses to start a job over `--max-hours` without being told to.

Scope it instead when that is enough. One domain across three formats tests the
shape-stratified path, which MTH-024 says is the riskiest part, for a third of
the time.

    python scripts/run_study.py --status
    python scripts/run_study.py --only-domain banking
    python scripts/run_study.py --only-format summary extraction
    python scripts/run_study.py --stop
    python scripts/run_study.py --clear-stop

## Two phases, so only one model is resident at a time

Recording holds the system under test on the GPU; detecting holds the NLI model.
On an 8 GB card the two together are tight, and there is no reason to overlap
them. So every selected cell is recorded first, then the system model is released
and the NLI model is loaded once for every cell's analysis.

That also means a pause during recording loses at most one triple, and a pause
between phases loses nothing at all: phase two reads checkpoints from disk and
needs no system under test.

## Per-cell checkpoints

Each cell's checkpoint is keyed on that cell's own configuration hash, so
stopping mid-study never risks a completed cell, and changing one cell's
configuration cannot invalidate another's work.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.net import enable_os_truststore  # noqa: E402

enable_os_truststore()

from aprime.cells.cell import FORMATS, Cell, build_inputs  # noqa: E402
from aprime.cells.chat import OllamaChat  # noqa: E402
from aprime.cells.packs import DOMAINS, build_pack  # noqa: E402
from aprime.cells.retrieval_faults import (  # noqa: E402
    activation_warnings,
    stale_view,
)
from aprime.cells.tools import ToolSet  # noqa: E402
from aprime.clustering import NLIEquivalence  # noqa: E402
from aprime.detect import detect  # noqa: E402
from aprime.probes.channels import (  # noqa: E402
    NLI_MODELS,
    NLIChannel,
    _resolve_revision,
)
from aprime.provenance import (  # noqa: E402
    capture,
    check_row_provenance,
    corpus_fingerprint,
    row_provenance,
)
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

# The model server. Overridable, because the system under test does not have to
# live on the machine driving the study: `host` has always been a parameter on
# the adapter, and only these runners assumed localhost.
#
#     APRIME_OLLAMA_HOST=http://192.168.1.50:11434 python scripts/...
#
# **The host is recorded in provenance but deliberately kept out of the config
# hash.** What has to match for two runs to be comparable is the weights, which
# the digest pins. Where those weights were served from does not change an
# output, and putting a hostname in the hash would make the same run on two
# boxes look like two different configurations.
HOST = os.environ.get("APRIME_OLLAMA_HOST", "http://127.0.0.1:11434")
MODEL = "granite4.2:8b"
STALE_SHAPES = frozenset({"lookup", "search", "history", "verify"})
N, K, Q = 40, 6, 0.10
N_ENTITIES = 18


def configure(n: int | None = None, k: int | None = None) -> None:
    """Set the corpus size and samples per cloud for this invocation.

    These are study configuration, never code (HANDOFF §10), and they are
    hashed: a different k or n is a different configuration with its own
    checkpoint filenames, which is intended (provenance.md). The defaults are
    the k=6 matrix of STD-010; `--k 20` is the D25 re-recording of the summary
    row, and it must not happen by editing the constants above.
    """
    global N, K
    if n is not None:
        if n < 1:
            raise ValueError(f"n must be at least 1, got {n}")
        N = int(n)
    if k is not None:
        if k < 2:
            raise ValueError(
                f"k must be at least 2, got {k}: one sample per cloud has no "
                "within-cloud variation for the decoy arm to measure")
        K = int(k)

# Seconds per single invocation, measured on this machine against this model in
# the nine-cell smoke run (results/cells_smoke.json). Used only for estimates,
# but they are the difference between a planned night and a surprised morning.
SECONDS_PER_INVOCATION = {"extraction": 7.1, "summary": 4.8, "agent": 16.9}

RUNS = ROOT / "results" / "study"
STOP_FLAG = RUNS / "STUDY.STOP"


def ollama_digest() -> str:
    """The digest of the loaded model, from /api/tags.

    `/api/show` does not carry one, which an earlier version of this assumed and
    silently recorded the model as "unresolved" into a config hash.
    """
    import urllib.request

    try:
        with urllib.request.urlopen(HOST + "/api/tags", timeout=30) as r:
            for m in json.loads(r.read().decode()).get("models", []):
                if m.get("name") == MODEL:
                    return str(m.get("digest") or "unresolved")
    except Exception:  # noqa: BLE001
        pass
    return "unresolved"


@dataclass
class CellJob:
    domain: str
    output_format: str
    digest: str
    inputs: list = field(default_factory=list)
    prov: object = None

    @property
    def name(self) -> str:
        return f"{self.domain}-{self.output_format}"

    @property
    def triples(self) -> int:
        return N * K

    @property
    def estimate_s(self) -> float:
        return self.triples * 3 * SECONDS_PER_INVOCATION[self.output_format]

    def paths(self) -> dict[str, Path]:
        h = self.prov.config_hash
        return {"checkpoint": RUNS / f"{self.name}.{h}.jsonl",
                "activation": RUNS / f"{self.name}.{h}.activation.json",
                "report": RUNS / f"{self.name}.{h}.report.json"}


def make_job(domain: str, output_format: str, digest: str, nli_rev: str) -> CellJob:
    job = CellJob(domain=domain, output_format=output_format, digest=digest)
    pack = build_pack(domain, n_entities=N_ENTITIES, seed=1)
    job.inputs = build_inputs(pack, n=N, seed=1, output_format=output_format)
    # DO NOT TIDY THE nli_revision FORMAT WHILE A RECORDING IS IN FLIGHT.
    #
    # `capture()` warns that a bare SHA is "not a pin" and wants the model id
    # alongside it. The warning is cosmetic: the SHA is the pin and it is
    # correct. The fix is not cosmetic. `instruments` feeds
    # `compute_config_hash`, so reformatting this string changes every cell's
    # config hash, which changes every checkpoint filename, which orphans the
    # recording on disk and starts the factorial again from zero.
    #
    # Measured 2026-10-04: the bare SHA hashes to 9864af6f7989ee8a and the
    # prefixed form to 9ed71b092eb45c10, on otherwise identical inputs.
    #
    # Change it at a boundary where nothing is part-recorded, and expect to
    # rerecord anything that was.
    job.prov = capture(
        instruments={"predicate": "NLIEquivalence@0.7",
                     "nli_revision": nli_rev,
                     "system_model": MODEL + "@" + digest[:16]},
        params={"k": K, "q": Q, "n_inputs": N, "domain": domain,
                "output_format": output_format,
                "fault": "F5:stale_view/" + ",".join(sorted(STALE_SHAPES)),
                "seed_policy": "unset on every arm (MTH-023)"},
        corpus=corpus_fingerprint([i.input_id for i in job.inputs]),
        notes={"purpose": "cell factorial", "model_host": HOST},
        warn_if_dirty=False,
    )
    return job


def select(args, digest: str, nli_rev: str) -> list[CellJob]:
    domains = args.only_domain or list(DOMAINS)
    formats = args.only_format or list(FORMATS)
    bad = set(domains) - set(DOMAINS)
    if bad:
        raise SystemExit(f"unknown domain(s) {sorted(bad)}; have {list(DOMAINS)}")
    bad = set(formats) - set(FORMATS)
    if bad:
        raise SystemExit(f"unknown format(s) {sorted(bad)}; have {list(FORMATS)}")
    # Format-major, cheapest format first, because this run gets stopped partway
    # by design.
    #
    # The study question is whether detection transfers ACROSS DOMAINS. One
    # format finished across all three domains answers that question for that
    # format: it is a complete row of the transfer matrix. One domain finished
    # across all three formats answers nothing about transfer, because there is
    # nothing to compare it against.
    #
    # Domain-major ordering was the original, and it would have spent the first
    # five hours producing a result that cannot be read. Cheapest first for the
    # same reason: summary is 2.9 h for all three domains, extraction 4.3 h,
    # agent 10.1 h, so the early hours buy whole rows rather than fractions.
    ordered = sorted(formats, key=lambda f: SECONDS_PER_INVOCATION[f])
    return [make_job(d, f, digest, nli_rev) for f in ordered for d in domains]


def chat() -> OllamaChat:
    # seed unset on every arm: MTH-023. Two baseline arms sharing a pinned seed
    # collapse the decoy arm, and the decoy arm is the null.
    return OllamaChat(model=MODEL, host=HOST, keep_alive="10m", num_ctx=8192,
                      temperature=0.2, num_predict=512, seed=None)


def arms_for(job: CellJob):
    pack = build_pack(job.domain, n_entities=N_ENTITIES, seed=1)
    fmt = job.output_format
    a = Cell(pack, fmt, chat(), "A", tools=ToolSet(pack))
    ap = Cell(pack, fmt, chat(), "A_prime", tools=ToolSet(pack))
    b = stale_view(pack,
                   lambda tools: Cell(pack, fmt, chat(), "B", tools=tools),
                   shapes=STALE_SHAPES)
    # The wrapper persists its own labels now, per invocation, so a kill loses
    # at most the triple in flight rather than the whole cell's ground truth.
    b.store = job.paths()["activation"]
    return {"A": a, "A_prime": ap, "B": b}, b


def cmd_status(jobs: list[CellJob]) -> int:
    print(f"{'cell':<26}{'triples':>12}{'done':>7}{'left, h':>9}")
    print("-" * 54)
    total_left = 0.0
    for job in jobs:
        p = recording_progress(job.paths()["checkpoint"], job.inputs, K)
        left_h = p["remaining"] * 3 * SECONDS_PER_INVOCATION[job.output_format] / 3600
        total_left += left_h
        done = "yes" if p["remaining"] == 0 else f"{p['fraction']:.0%}"
        print(f"{job.name:<26}{p['planned']:>12}{done:>7}{left_h:>9.1f}")
    print("-" * 54)
    print(f"{'total':<26}{'':>12}{'':>7}{total_left:>9.1f}")
    print(f"stop flag {'SET' if STOP_FLAG.exists() else 'not set'}")
    return 0


def main() -> int:
    ap_ = argparse.ArgumentParser(description="Record and analyse the cell factorial.")
    ap_.add_argument("--only-domain", nargs="*", help="restrict to these domains")
    ap_.add_argument("--only-format", nargs="*", help="restrict to these formats")
    ap_.add_argument("--status", action="store_true")
    ap_.add_argument("--stop", action="store_true")
    ap_.add_argument("--clear-stop", action="store_true")
    ap_.add_argument("--stop-after-hours", type=float, default=0.0,
                     help="stop cleanly after this many hours of recording. 0 "
                          "means run until the work is done or --stop is used. "
                          "A safety net for an unattended overnight run, not a "
                          "substitute for --stop.")
    ap_.add_argument("--go", action="store_true",
                     help="actually record; without it this prints the plan and "
                          "exits, because starting hours of GPU work should "
                          "never be the default")
    ap_.add_argument("--max-hours", type=float, default=3.0,
                     help="refuse to start a job estimated longer than this "
                          "even with --go")
    ap_.add_argument("--yes", action="store_true",
                     help="proceed past --max-hours")
    ap_.add_argument("--k", type=int, default=None,
                     help=f"samples per cloud (default {K}). A different k is a "
                          "different configuration: new config hash, new "
                          "checkpoint files, nothing shared with the k=6 matrix")
    ap_.add_argument("--n", type=int, default=None,
                     help=f"inputs per cell (default {N}). Hashed, like --k")
    args = ap_.parse_args()
    configure(n=args.n, k=args.k)

    RUNS.mkdir(parents=True, exist_ok=True)
    if args.stop:
        STOP_FLAG.write_text("stop requested\n", encoding="utf-8")
        print("stop requested. The recording will finish its current triple and "
              "exit, leaving every completed cell and triple on disk.")
        return 0
    if args.clear_stop:
        STOP_FLAG.unlink(missing_ok=True)
        print("stop flag cleared")
        return 0

    digest = ollama_digest()
    nli_spec = next(s for s in NLI_MODELS if s.key == "deberta_mnli")
    nli_rev = str(_resolve_revision(nli_spec.hub_id))
    jobs = select(args, digest, nli_rev)

    if args.status:
        return cmd_status(jobs)
    if STOP_FLAG.exists():
        print("the stop flag is set, so this would stop immediately. Clear it "
              "with --clear-stop.")
        return 1

    remaining_h = 0.0
    for job in jobs:
        p = recording_progress(job.paths()["checkpoint"], job.inputs, K)
        remaining_h += (p["remaining"] * 3
                        * SECONDS_PER_INVOCATION[job.output_format] / 3600)
    print(f"{len(jobs)} cell(s), n={N} k={K}, model {MODEL} @ {digest[:12]}")
    print(f"estimated {remaining_h:.1f} h of GPU still to record")
    if args.stop_after_hours:
        print(f"will stop itself after {args.stop_after_hours:.1f} h")
    # The schedule, cumulative, so stopping at any point is an informed choice
    # rather than a guess about what survived.
    print()
    print("order, and what is complete by when:")
    cum = 0.0
    for job in jobs:
        p_ = recording_progress(job.paths()["checkpoint"], job.inputs, K)
        left = (p_["remaining"] * 3
                * SECONDS_PER_INVOCATION[job.output_format] / 3600)
        cum += left
        done = " (already done)" if p_["remaining"] == 0 else ""
        print(f"  {cum:>5.1f} h  {job.name}{done}")
    # Dry run by default. An earlier version only gated on --max-hours, and a
    # scope whose estimate fell just under the default started recording on a
    # machine that was already busy. Hours of someone else's GPU is not a
    # sensible default for a bare invocation.
    if not args.go:
        print()
        print("this is a plan, not a run. Add --go to record.")
        for job in jobs:
            print(f"  {job.name:<26} {job.triples:>4} triples  "
                  f"~{job.estimate_s / 3600:.1f} h")
        return 0
    if remaining_h > args.max_hours and not args.yes:
        print(f"that is over --max-hours={args.max_hours}. Pass --yes to go "
              f"ahead, or scope it with --only-domain / --only-format.")
        print("the agent format is 3.5x the cost of summary and dominates any "
              "full run, so dropping it is the biggest single saving.")
        return 1
    print()

    # ---------------------------------------------------------------- phase 1
    # Two reasons to stop: somebody asked, or the clock ran out. Both checked at
    # triple boundaries, so either way the recording stops between triples and
    # loses at most one.
    flag_set = stop_requested(STOP_FLAG)
    deadline = (time.time() + args.stop_after_hours * 3600
                if args.stop_after_hours else None)

    def should_stop() -> bool:
        if flag_set():
            return True
        return deadline is not None and time.time() >= deadline
    recorded: dict[str, CellJob] = {}
    faults: dict[str, object] = {}
    for job in jobs:
        paths = job.paths()
        p = recording_progress(paths["checkpoint"], job.inputs, K)
        if p["remaining"] == 0:
            print(f"{job.name}: already complete, {p['done']} triples")
            recorded[job.name] = job
            continue
        arms, fault = arms_for(job)
        faults[job.name] = fault
        print(f"{job.name}: recording {p['remaining']} of {p['planned']} triples "
              f"(~{p['remaining'] * 3 * SECONDS_PER_INVOCATION[job.output_format] / 60:.0f} min)")
        t0 = time.perf_counter()
        try:
            record(job.inputs, arms, k=K, checkpoint=paths["checkpoint"],
                   progress_every=25, should_stop=should_stop)
        except PreflightFailed as dead:
            OllamaChat(model=MODEL, host=HOST).release()
            print(f"  PREFLIGHT FAILED in {job.name}, nothing recorded for it.")
            for probe in dead.result.failed:
                print(f"    {probe.arm}: {probe.error}")
            print(f"    is the model server up at {HOST}? Earlier cells are "
                  f"still on disk.")
            return 3
        except RecordingFailed as died:
            # The server was alive at preflight and died mid-recording. Last
            # seen 2026-10-05, when Ollama dropped the connection during a
            # call. Without this handler it surfaced as a raw traceback.
            OllamaChat(model=MODEL, host=HOST).release()
            print(f"  SERVER DIED mid-recording in {job.name}: {died}")
            print("    everything recorded so far is on disk and resumes.")
            return 6
        except RunPaused as paused:
            OllamaChat(model=MODEL, host=HOST).release()
            print(f"  PAUSED in {job.name}: {paused}")
            print("  every completed cell and triple is on disk. Resume with "
                  "--clear-stop then rerun.")
            return 2
        print(f"  done in {(time.perf_counter() - t0) / 60:.0f} min")
        recorded[job.name] = job
    OllamaChat(model=MODEL, host=HOST).release()
    print()

    # ---------------------------------------------------------------- phase 2
    print("analysing (system model released, NLI model loaded once)")
    nli = NLIChannel(nli_spec)
    predicate = NLIEquivalence(nli, threshold=0.7)
    return analyse(list(recorded.values()), predicate, nli, digest)


def analyse(jobs: list[CellJob], predicate, nli, digest: str,
            out: Path | None = None) -> int:
    """Phase 2: read every recorded cell from disk, detect, write the matrix.

    Separate from `main` so it can be driven without a model server or the
    NLI model: `predicate=None, nli=None` is the exact-match path, which is
    enough to exercise the file layout, the row construction and the refusal.
    This path had never run before the first factorial night and had no test;
    `tests/test_study_analysis.py` now runs it against a synthetic recording
    laid out exactly as the recorder lays out a real one.

    Returns 0 and writes `matrix.json`, or 4 and writes nothing when a row
    cannot be traced back. The check runs per row before that row's own report
    file is written, so a refusal leaves no untraceable file behind at all,
    not just no matrix.
    """
    out = out or (RUNS / "matrix.json")
    matrix = []
    for job in jobs:
        paths = job.paths()
        samples, _, _ = load_checkpoint(paths["checkpoint"])
        ids = list(dict.fromkeys(s.input_id for s in samples))
        rec = Recording(samples=samples, k=K, input_ids=ids)
        # Keys are "<input_id>#<sample_idx>": an input counts as touched when the
        # fault fired on any of its samples.
        fired: set[str] = set()
        if paths["activation"].exists():
            try:
                raw = json.loads(paths["activation"].read_text(encoding="utf-8"))
                for key, hit in raw.items():
                    if hit:
                        fired.add(key.rpartition("#")[0] or key)
            except ValueError:
                pass

        t0 = time.perf_counter()
        rep = detect(rec, predicate=predicate, nli_channel=nli, q=Q)
        secs = time.perf_counter() - t0
        flagged = {f.input_id for f in rep.findings}
        tp = len(flagged & fired)
        row = {
            "cell": job.name, "domain": job.domain,
            "output_format": job.output_format,
            # Full provenance, not just the config hash. See
            # provenance.row_provenance for why one helper rather than two
            # hand-written dicts.
            **row_provenance(job.prov, system=MODEL, system_digest=digest,
                             sessions=rec.sessions,
                             analysed_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                        time.gmtime())),
            "n_inputs": len(ids), "k": K, "q": Q,
            "activated": len(fired), "flagged": len(flagged),
            "true_positives": tp,
            # The flagged ids themselves, not only their count. Their absence
            # blocked an offline caught-versus-firing-fraction analysis on
            # 2026-10-05: counts cannot be joined with per-sample activation.
            "findings": [
                {"input_id": f.input_id, "channels": sorted(f.channels)}
                for f in rep.findings
            ],
            "realised_fdr": (1 - tp / len(flagged)) if flagged else None,
            "recall": (tp / len(fired)) if fired else None,
            "detect_s": round(secs, 1),
            "cost": rep.cost,
            "channels": {n: {"flagged": c.n_flagged, "skipped": c.skipped}
                         for n, c in rep.channels.items()},
            "gradable": not activation_warnings(fired, ids, q=Q,
                                                label=job.name),
        }
        # Refuse rather than warn, and refuse BEFORE this cell's report file is
        # written. An untraceable number in a committed results file is worse
        # than no number, because it looks usable.
        problems = check_row_provenance([row])
        if problems:
            print()
            print("REFUSING to write results: a row cannot be traced back.")
            for msg in problems:
                print(f"  {msg}")
            print("  The recordings are on disk and nothing is lost. Fix the row "
                  "construction and rerun the analysis.")
            return 4
        matrix.append(row)
        paths["report"].write_text(json.dumps(row, indent=2), encoding="utf-8")
        print(f"  {job.name:<24} activated {len(fired):>3}/{len(ids):<3} "
              f"flagged {len(flagged):>3}  {secs:.0f}s"
              f"{'' if row['gradable'] else '  NOT GRADABLE at this size'}")

    out.write_text(json.dumps({"model": MODEL, "digest": digest, "n": N, "k": K,
                               "q": Q, "rows": matrix}, indent=2),
                   encoding="utf-8")
    print(f"\nwrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
