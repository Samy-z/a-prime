"""Blind judging queue for the assistante-ventes pairwise campaign.

Measurement plan item 3 (docs/compare/campaign-assistante.md): the detector
does not rank quality, it names the inputs where the two models certifiably
differ, and a human judges only those, blind to which model wrote which
side. This emitter reads the primary pairing's selection from the pairwise
report, draws two samples per model per flagged input (one from each
recording arm, seeded), shuffles which model is side X case by case,
shuffles case order, and writes:

    compare/results/judging-queue.md             the judge reads and fills this
    compare/results/judging-key-DO-NOT-OPEN.json the unblinding map, sealed

The judge fills one `verdict:` line per case with X, Y, egal or aucun
(legend at the top of the queue). `--score` parses the filled queue,
unblinds it against the key, prints the tally and writes it to
compare/results/judging-verdict.json.

Blindness caveat, recorded here because it is structural: the campaign's
ledger reports aggregate tendencies, so an owner-judge may recognise a
side from its style. Sides are still shuffled per case, the queue itself
carries no scores, no channel names and no stability markers, and a judge
who has read nothing (the real user) stays fully blind.
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "messages.json"
RESULTS = HERE / "results"
STORE = RESULTS / "pairwise-ventes.jsonl"
REPORT = RESULTS / "pairwise-ventes.report.json"
QUEUE = RESULTS / "judging-queue.md"
KEY = RESULTS / "judging-key-DO-NOT-OPEN.json"
VERDICT = RESULTS / "judging-verdict.json"

SEED = 20261106  # the run date; recorded in the key, never re-rolled silently

# One sample from each of the model's two recording arms, so both replicate
# arms are represented and neither arm's quirks are over-drawn.
ARMS = {"llama3.2:3b": ["m1a", "m1b"], "phi4-mini:latest": ["m2a", "m2b"]}

# Nothing model-identifying may reach the judge. Checked over the emitted
# queue; word boundaries keep French words like "graphique" out of it.
FORBIDDEN = re.compile(
    r"(?i)\b(ollama|llama|llama3|phi|phi4|m1a|m1b|m2a|m2b|mistral|microsoft|meta)\b")

HEADER = """\
# File d'arbitrage — campagne assistante-ventes (à l'aveugle)

{n} cas. Chaque cas montre la tâche, puis deux réponses du côté X et deux
du côté Y. X et Y ne désignent pas toujours le même système : le camp est
retiré au sort à chaque cas, et la correspondance est scellée dans un
fichier à part. Ne pas l'ouvrir avant d'avoir tout jugé.

Pour chaque cas, remplir la ligne `verdict:` avec un seul mot :

- `X` : le côté X fait mieux le travail
- `Y` : le côté Y fait mieux le travail
- `egal` : aussi bons (ou aussi moyens) l'un que l'autre
- `aucun` : aucun des deux n'est utilisable

La ligne `remarque:` est libre et optionnelle. Juger le travail, pas le
style pour le style : fidélité (dates, montants, références de commande),
registre professionnel, français correct, concision.
"""

TASK_INBOUND = "**Tâche : traduire en français le message client ({lang}).**"
TASK_OUTBOUND = "**Tâche : rédiger l'e-mail selon la consigne.**"


def _load_cases() -> list[str]:
    rep = json.loads(REPORT.read_text(encoding="utf-8"))
    return [f["input_id"] for f in rep["pairings"]["primary"]["findings"]]


def _store_index() -> dict[tuple[str, str, int], str]:
    idx = {}
    for line in STORE.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("error") is None and r.get("output"):
            idx[(r["input_id"], r["arm"], r["sample_idx"])] = r["output"]
    return idx


def _fixture_blocks() -> dict[str, tuple[str, str]]:
    """input_id -> (task line, quoted source text)."""
    fx = json.loads(FIXTURES.read_text(encoding="utf-8"))
    out = {}
    for m in fx["inbound"]:
        out[m["id"]] = (TASK_INBOUND.format(lang=m["lang"]), m["text"])
    for o in fx["outbound"]:
        out[o["id"]] = (TASK_OUTBOUND, o["brief"])
    return out


def _quote(text: str) -> str:
    return "\n".join("> " + ln for ln in text.splitlines())


def emit(queue_path: Path = QUEUE, key_path: Path = KEY,
         force: bool = False) -> int:
    if queue_path.exists() and not force:
        filled = [ln for ln in queue_path.read_text(encoding="utf-8").splitlines()
                  if ln.startswith("verdict:") and ln[len("verdict:"):].strip()]
        if filled:
            print(f"REFUSED: {queue_path} carries {len(filled)} filled verdict(s); "
                  "judging work is runtime state. --force discards it.")
            return 2

    cases = _load_cases()
    idx = _store_index()
    fixtures = _fixture_blocks()
    rep = json.loads(REPORT.read_text(encoding="utf-8"))

    rng = random.Random(SEED)
    order = list(cases)
    rng.shuffle(order)

    models = sorted(ARMS)  # fixed iteration order, so the rng stream is stable
    md = [HEADER.format(n=len(order))]
    key_cases = []
    for pos, iid in enumerate(order, start=1):
        draws = {}
        for model in models:
            draws[model] = [(arm, rng.randrange(20)) for arm in ARMS[model]]
        x_model = models[rng.randrange(2)]
        y_model = next(m for m in models if m != x_model)

        task_line, source = fixtures[iid]
        md.append(f"\n## Cas {pos} (id: {iid})\n")
        md.append(task_line + "\n")
        md.append(_quote(source) + "\n")
        for side, model in (("X", x_model), ("Y", y_model)):
            for j, (arm, sidx) in enumerate(draws[model], start=1):
                md.append(f"**{side}{j} :**\n")
                md.append("```\n" + idx[(iid, arm, sidx)].strip() + "\n```\n")
        md.append("verdict:\nremarque:\n")

        key_cases.append({
            "position": pos, "input_id": iid,
            "X": x_model, "Y": y_model,
            "draws": {"X": draws[x_model], "Y": draws[y_model]},
        })

    body = "\n".join(md)
    hit = FORBIDDEN.search(body)
    if hit:
        print(f"REFUSED: blindness check failed, {hit.group(0)!r} appears in "
              "the queue. Inspect the drawn outputs before emitting.")
        return 3

    queue_path.write_text(body, encoding="utf-8")
    key_path.write_text(json.dumps({
        "created_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "seed": SEED,
        "source_report": {"run_id": rep["run_id"],
                          "config_hash": rep["config_hash"]},
        "cases": key_cases,
    }, indent=2), encoding="utf-8")
    print(f"wrote {queue_path} ({len(order)} cases) and {key_path}")
    return 0


def score(queue_path: Path = QUEUE, key_path: Path = KEY,
          out_path: Path = VERDICT) -> int:
    key = json.loads(key_path.read_text(encoding="utf-8"))
    by_id = {c["input_id"]: c for c in key["cases"]}
    text = queue_path.read_text(encoding="utf-8")

    rows, current = [], None
    for ln in text.splitlines():
        m = re.match(r"^## Cas (\d+) \(id: ([a-z0-9-]+)\)", ln)
        if m:
            current = m.group(2)
            continue
        m = re.match(r"^verdict:\s*(.*)$", ln)
        if m and current is not None:
            rows.append((current, m.group(1).strip().lower()))
            current = None

    if len(rows) != len(key["cases"]):
        print(f"REFUSED: parsed {len(rows)} verdict lines for "
              f"{len(key['cases'])} cases; the queue looks edited beyond "
              "its verdict lines.")
        return 2

    tally: dict[str, int] = {}
    cases_out = []
    for iid, raw in rows:
        kc = by_id[iid]
        verdict = {"égal": "egal"}.get(raw, raw)
        model = kc[verdict.upper()] if verdict in ("x", "y") else None
        label = model if model else (verdict if verdict else "blank")
        tally[label] = tally.get(label, 0) + 1
        cases_out.append({"input_id": iid, "verdict": verdict or "blank",
                          "side_X": kc["X"], "side_Y": kc["Y"],
                          "judged_model": model})

    print(f"{len(rows)} cases:")
    for label in sorted(tally, key=tally.get, reverse=True):
        print(f"  {label:20} {tally[label]:2} / {len(rows)}")
    out_path.write_text(json.dumps({
        "scored_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "source_report": key["source_report"],
        "totals": tally, "cases": cases_out,
    }, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--score", action="store_true",
                    help="parse the filled queue and unblind the tally")
    ap.add_argument("--force", action="store_true",
                    help="re-emit even over filled verdicts")
    args = ap.parse_args(argv)
    if args.score:
        return score()
    return emit(force=args.force)


if __name__ == "__main__":
    sys.exit(main())
