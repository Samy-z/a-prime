"""Capture real server responses as test fixtures, and measure the seed regimes.

## Why fixtures at all

Six times now a hand-written test double has been more cooperative than the
real API: an invented `sha256:` digest prefix, a check that conflated errored
with empty, a missing `"role"`, no `</think>` leak, a scripted turn that always
terminated, and a tool that always found what it was asked for. Every one was
caught by running against reality, and none by the tests.

A fake written from memory of an API encodes what we believe the API does. A
fixture captured from the API encodes what it does. The difference is only
visible when they disagree, which is exactly when it matters.

## Why the seed regimes are measured in the same pass

A-prime is the second baseline run and it IS the null distribution that
target-decoy FDR calibrates against. How wide that null is depends entirely on
the seed policy, and the seed policy of the arms has to mirror the seed policy
of the deployment being audited rather than being chosen for our convenience.
Three regimes, three different nulls, measured rather than assumed.

Writes `tests/fixtures/ollama_chat.json`. Needs a live server.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.cells.chat import OllamaChat  # noqa: E402
from aprime.cells.packs import build_pack  # noqa: E402
from aprime.cells.tools import ToolSet  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:11434"
MODEL = sys.argv[2] if len(sys.argv) > 2 else "granite4.2:8b"
OUT = ROOT / "tests" / "fixtures" / "ollama_chat.json"

PACK = build_pack("banking", n_entities=18, seed=1)
TOOLS = ToolSet(PACK)
EID = PACK.entity_ids()[0]

SYS = ("You are a applicant case handler working with account records. Use the "
       "tools to look up facts rather than guessing them.")


def cap(label: str, why: str, messages, tools, **over) -> dict:
    chat = OllamaChat(model=MODEL, host=HOST, keep_alive="2m", num_ctx=8192,
                      temperature=0.2, seed=7, **over)
    body = chat(messages, tools)
    print(f"  {label:<22} keys={sorted(body.get('message', {}))} "
          f"done={body.get('done_reason')}")
    return {"label": label, "why": why, "captured_from": MODEL,
            "request": {"messages": messages, "tools_offered": bool(tools),
                        "overrides": over},
            "response": body}


def main() -> int:
    print(f"host {HOST}\nmodel {MODEL}\n")
    schemas = TOOLS.schemas()
    fx = []

    print("capturing response shapes")
    fx.append(cap(
        "text_stop", "A plain answer with no tool call. The baseline shape.",
        [{"role": "system", "content": SYS},
         {"role": "user", "content": "Reply with exactly the word: ready."}],
        None))

    fx.append(cap(
        "tool_call", "A turn that asks for a tool. Note whether 'role' is "
                     "present and what 'content' holds alongside tool_calls.",
        [{"role": "system", "content": SYS},
         {"role": "user", "content": f"What is the status of account {EID}?"}],
        schemas))

    fx.append(cap(
        "truncated", "done_reason 'length'. A cut-off output is a confound the "
                     "detector would read as the system changing.",
        [{"role": "system", "content": SYS},
         {"role": "user", "content": "Explain, at length, what a debt to "
                                     "income ratio is and why lenders use it."}],
        None, num_predict=24))

    fx.append(cap(
        "after_tool_result", "The turn after a tool result is fed back. This "
                             "is where the reasoning leak was first seen.",
        [{"role": "system", "content": SYS},
         {"role": "user", "content": f"Show the transactions on account {EID} "
                                     f"above 1000."},
         {"role": "assistant", "content": "",
          "tool_calls": [{"function": {"name": "search_transactions",
                                       "arguments": {"account_id": EID,
                                                     "min_amount": 1000}}}]},
         {"role": "tool", "name": "search_transactions",
          "content": json.dumps(TOOLS.call("search_transactions",
                                           {"account_id": EID,
                                            "min_amount": 1000}))}],
        schemas))

    fx.append(cap(
        "tools_withheld", "The forced final answer: same conversation, tools "
                          "withdrawn. Exercises the exhaustion path.",
        [{"role": "system", "content": SYS},
         {"role": "user", "content": f"What is the status of account {EID}?"},
         {"role": "assistant", "content": "",
          "tool_calls": [{"function": {"name": "get_account",
                                       "arguments": {"account_id": EID}}}]},
         {"role": "tool", "name": "get_account",
          "content": json.dumps(TOOLS.call("get_account", {"account_id": EID}))},
         {"role": "user", "content": "Stop searching and answer now."}],
        None))

    fx.append(cap(
        "bad_tool_name", "A tool the set does not have. Models do this, and "
                         "the error has to be readable enough to recover from.",
        [{"role": "system", "content": SYS},
         {"role": "user", "content": "Call the tool named get_nonexistent."}],
        schemas))

    # ---------------------------------------------------------------- seeds
    print("\nseed regimes: how wide is the null the decoy arm measures?")
    probe = [{"role": "system", "content": SYS},
             {"role": "user", "content": "In two sentences, say what a debt to "
                                         "income ratio tells a lender."}]
    regimes = {}
    for name, seeds in (("pinned, shared", (7, 7)),
                        ("pinned, differing", (7, 8)),
                        ("unset", (None, None))):
        outs = []
        for sd in seeds:
            c = OllamaChat(model=MODEL, host=HOST, keep_alive="2m",
                           num_ctx=8192, temperature=0.2, seed=sd,
                           num_predict=160)
            outs.append((c(probe, None).get("message") or {}).get("content", ""))
        same = outs[0].strip() == outs[1].strip()
        regimes[name] = {"seeds": seeds, "identical": same,
                         "a": outs[0].strip(), "a_prime": outs[1].strip()}
        print(f"  {name:<20} identical={same}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"captured": MODEL, "host_note": "local Ollama, see BCH-012 for version",
         "fixtures": fx, "seed_regimes": regimes}, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)} ({len(fx)} fixtures)")
    OllamaChat(model=MODEL, host=HOST).release()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
