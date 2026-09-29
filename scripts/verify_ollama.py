"""Verify the Ollama adapter against a live server.

Everything in `tests/test_ollama.py` runs against a fake transport. That proves
the adapter enforces its own rules; it proves nothing about whether a real server
behaves as the fake does. This is the check that closes that gap, and it is the
only thing in the repo that needs the GPU.

Two per-model traps are the reason this is a four-model pass rather than one:

- **Ministral 3's template injects the current date.** Verified by comparing
  `prompt_eval_count` with an explicit system message against a raw call with
  none. A large gap means the template is supplying its own prompt (BCH-009).
- **Qwen3.5 defaults thinking on** and can spend a whole budget reasoning,
  returning empty content — indistinguishable from injected F12 truncation.

Every call passes `keep_alive: 0`, so each model unloads the moment its checks
finish rather than parking 6 GB of VRAM for Ollama's default five-minute idle.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.adapter import Invocation  # noqa: E402
from aprime.systems.ollama import (  # noqa: E402
    HttpTransport,
    OllamaConfig,
    OllamaSystem,
    PinMismatch,
)

HOST = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:11434"
MODELS = ["granite4.2:8b", "ministral-3:8b", "qwen3.5:9b", "ministral-3:3b"]
SYSTEM = "You are a claims assessor. Reply with exactly one short sentence."
PROMPT = "Was the term loan application for Maria Okonkwo approved?"

ok: list[str] = []
bad: list[str] = []


def check(label: str, passed: bool, detail: str = "") -> None:
    (ok if passed else bad).append(label)
    print(f"  [{'PASS' if passed else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))


def raw_chat(model: str, messages: list[dict], **opts) -> dict:
    """Bypass the adapter, to measure what the server does on its own."""
    payload = {
        "model": model, "messages": messages, "stream": False,
        "keep_alive": 0, "options": {"num_predict": 8, **opts},
    }
    req = urllib.request.Request(
        f"{HOST}/api/chat", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())


def cfg(model: str, **kw) -> OllamaConfig:
    base = dict(
        model=model, system=SYSTEM, num_ctx=4096, temperature=0.2,
        top_p=0.9, top_k=40, seed=11, num_predict=80,
        keep_alive=0, host=HOST,
    )
    base.update(kw)
    return OllamaConfig(**base)


def main() -> int:
    t_start = time.perf_counter()
    print(f"host {HOST}\n")

    try:
        ver = json.loads(urllib.request.urlopen(f"{HOST}/api/version", timeout=10).read())
        tags = json.loads(urllib.request.urlopen(f"{HOST}/api/tags", timeout=10).read())
    except (urllib.error.URLError, OSError) as exc:
        print(f"server unreachable at {HOST}: {exc}")
        return 2
    present = {m["name"] for m in tags.get("models", [])}
    print(f"server version {ver.get('version')}")
    print(f"models present: {len(present)}")
    missing = [m for m in MODELS if m not in present]
    if missing:
        print(f"  MISSING: {missing} -- the data directory may be redirected")
        return 2
    print()

    for model in MODELS:
        print(f"=== {model} ===")
        t0 = time.perf_counter()
        sysm = OllamaSystem(cfg(model), "A", HttpTransport())

        # 1. pinning against the real server
        try:
            p = sysm.pin()
            # Digests come back as bare hex on a live 0.34.4 server. The fake
            # transport invented a "sha256:" prefix and this assertion copied it.
            check("pin captures version and digest",
                  bool(p["server_version"]) and len(p["model_digest"] or "") >= 12,
                  f"digest {p['model_digest'][:19]}")
            sysm.verify_pin()
            sysm.verify_pin()
            check("verify_pin is quiet on an unchanged stack", True)
        except PinMismatch as exc:
            check("pinning", False, str(exc)[:120])

        # 2. a real generation comes back
        r = sysm.invoke(Invocation("v1", PROMPT))
        check("returns non-empty content", bool(r.output.strip()),
              f"{len(r.output.split())} words, {r.trace.latency_ms:.0f}ms, "
              f"finish={r.trace.finish_reason}")
        if r.trace.error:
            check("no transport error", False, r.trace.error[:120])
            print()
            continue

        # 3. BCH-009: does the template inject its own system prompt?
        with_sys = raw_chat(model, [{"role": "system", "content": SYSTEM},
                                    {"role": "user", "content": "hi"}])
        without = raw_chat(model, [{"role": "user", "content": "hi"}])
        a, b = with_sys.get("prompt_eval_count", 0), without.get("prompt_eval_count", 0)
        injected = b > a + 50
        print(f"  prompt tokens: with system={a}  without={b}  "
              f"{'TEMPLATE INJECTS ~' + str(b - a) if injected else 'no injection'}")
        check("explicit system message suppresses template injection",
              a <= b + 50, f"{a} vs {b}")

        # 4. seed reproducibility -- proves options actually take effect
        o1 = sysm.invoke(Invocation("v2", PROMPT)).output
        o2 = OllamaSystem(cfg(model), "A", HttpTransport()).invoke(
            Invocation("v2", PROMPT)).output
        check("same seed reproduces the same output", o1 == o2,
              "identical" if o1 == o2 else f"{o1[:40]!r} vs {o2[:40]!r}")

        # 5. the thinking trap
        thinking = OllamaSystem(cfg(model, think=True, num_predict=12), "A",
                                HttpTransport()).invoke(Invocation("v3", PROMPT))
        ex = thinking.trace.extra
        print(f"  think=True, budget 12: content={len(thinking.output.strip())} chars, "
              f"empty_output={ex.get('empty_output', False)}, "
              f"with_tokens={ex.get('empty_with_tokens', False)}, "
              f"thinking={ex.get('thinking_chars', 0)} chars")
        # An empty output is accounted for either way: flagged as empty, or
        # carrying an error. Ministral 3 rejects `think` with HTTP 400 rather
        # than returning an empty message, and an error is not an empty success.
        accounted = (
            bool(thinking.output.strip())
            or ex.get("empty_output") is True
            or bool(thinking.trace.error)
        )
        check("an empty output is accounted for (flagged or errored)", accounted,
              f"error={(thinking.trace.error or 'none')[:40]}")
        if thinking.trace.error and "400" in str(thinking.trace.error):
            print("        note: this model rejects `think` outright (HTTP 400)")
        check("think=False default returns content", bool(r.output.strip()))

        print(f"  ({time.perf_counter() - t0:.0f}s)\n")

    # error path needs no GPU
    print("=== error handling ===")
    dead = OllamaSystem(cfg("granite4.2:8b", host="http://127.0.0.1:59999"), "A",
                        HttpTransport())
    er = dead.invoke(Invocation("v9", PROMPT))
    check("unreachable server becomes an errored sample, not an exception",
          er.output == "" and bool(er.trace.error), (er.trace.error or "")[:60])

    print(f"\n{len(ok)} passed, {len(bad)} failed, "
          f"{time.perf_counter() - t_start:.0f}s total GPU time")
    if bad:
        print("failures:")
        for b_ in bad:
            print(f"  - {b_}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
