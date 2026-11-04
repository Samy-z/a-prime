"""French-capability spot check for the pair nomination (CMP seat).

The pace pass records lengths, not text, so it cannot answer the one gate
in the frozen pair rule ("two fastest FRENCH-CAPABLE"). This instrument
captures the actual outputs of named candidates on three representative
tasks — an English inbound, a German inbound, a French outbound brief —
for a human read. It judges nothing itself: the verdict is the reader's,
recorded in the CMP ledger next to this file's output.

    python compare/spotcheck_french.py llama3.2:3b phi4-mini:latest
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures" / "messages.json"
RESULTS = HERE / "results" / "french-spotcheck-2026-11.json"
OLLAMA = "http://127.0.0.1:11434"

SPOT_INBOUND = ["msg-01", "msg-02"]   # en -> fr, de -> fr
SPOT_OUTBOUND = ["out-01"]            # French draft from a French brief

# Same prompts as the pace pass, deliberately: the gate judges what the
# campaign would actually ship, not a flattering variant.
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


def generate(tag: str, prompt: str) -> dict:
    req = urllib.request.Request(
        OLLAMA + "/api/generate",
        data=json.dumps({
            "model": tag, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.2, "num_predict": 400,
                        "num_gpu": 0},
            "keep_alive": "2m"}).encode("utf-8"),
        headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as r:
        body = json.loads(r.read().decode())
    return {"wall_s": round(time.perf_counter() - t0, 2),
            "text": body.get("response", "")}


def main() -> int:
    tags = sys.argv[1:]
    if not tags:
        print("usage: spotcheck_french.py <ollama-tag> [...]")
        return 2
    msgs = json.loads(FIXTURES.read_text(encoding="utf-8"))
    inbound = {m["id"]: m for m in msgs["inbound"]}
    outbound = {o["id"]: o for o in msgs["outbound"]}

    out = {"purpose": "French-capability gate for the CMP pair rule",
           "tasks": SPOT_INBOUND + SPOT_OUTBOUND, "models": {}}
    for tag in tags:
        rows = []
        for mid in SPOT_INBOUND:
            m = inbound[mid]
            r = generate(tag, PROMPT_TRADUIRE.format(texte=m["text"]))
            rows.append({"task": mid, "lang_in": m["lang"], **r})
            print(f"{tag} {mid} ({m['lang']}): {r['wall_s']}s")
        for oid in SPOT_OUTBOUND:
            o = outbound[oid]
            r = generate(tag, PROMPT_REDIGER.format(consigne=o["brief"]))
            rows.append({"task": oid, "lang_in": "fr", **r})
            print(f"{tag} {oid} (fr brief): {r['wall_s']}s")
        out["models"][tag] = rows
    RESULTS.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    print(f"saved -> {RESULTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
