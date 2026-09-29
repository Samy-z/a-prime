"""Run every cell against a live model, and measure what it actually costs.

Two questions at once.

**Do the cells work?** Everything so far has been tested with a scripted chat
function. That proves the loop is wired correctly and says nothing about whether
a real model drives it sensibly: whether it calls the tools, whether it produces
the output shape each mode asks for, whether the agent mode terminates.

**What is the peak context demand per cell?** D11 settled that the context cap
follows from what the cells need rather than being chosen first. The tool
schemas cost 461-751 tokens (BCH-013) and that is the floor; this measures the
conversation on top of it, which is what actually sets the cap.

Keeps the model resident during the run and unloads once at the end.
Unloading per call would mean a multi-gigabyte reload before every call.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aprime.cells.cell import MODES, Cell, build_inputs  # noqa: E402
from aprime.cells.chat import OllamaChat  # noqa: E402
from aprime.cells.packs import DOMAINS, build_pack  # noqa: E402
from aprime.cells.tools import ToolSet  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:11434"
MODEL = sys.argv[2] if len(sys.argv) > 2 else "granite4.2:8b"
N_INPUTS = 4


def shape_ok(mode: str, text: str) -> bool:
    """Did the model produce the output shape this mode asked for?"""
    s = text.strip()
    if not s:
        return False
    if mode == "extraction":
        try:
            obj = json.loads(s[s.index("{"): s.rindex("}") + 1])
        except (ValueError, TypeError):
            return False
        return isinstance(obj, dict) and len(obj) >= 2
    if mode == "agent":
        return s.upper().startswith(("APPROVE", "DECLINE", "ESCALATE"))
    return len(s.split()) >= 15 and "{" not in s[:20]


def main() -> int:
    t_all = time.perf_counter()
    print(f"host {HOST}\nmodel {MODEL}\n{N_INPUTS} inputs per cell, "
          f"num_ctx 8192, num_predict 512\n")
    rows = []
    hdr = f"{'cell':<28} {'ok':>6} {'shape':>7} {'tools':>6} {'steps':>6} {'peak tok':>9} {'s':>6}"
    print(hdr)
    print("-" * len(hdr))

    for domain in DOMAINS:
        pack = build_pack(domain, n_entities=18, seed=1)
        for mode in MODES:
            inputs = build_inputs(pack, n=N_INPUTS, seed=1, mode=mode)
            t0 = time.perf_counter()
            chat = OllamaChat(model=MODEL, host=HOST, keep_alive="2m",
                              num_ctx=8192, temperature=0.2, seed=7,
                              num_predict=512)
            cell = Cell(pack, mode, chat, "A", tools=ToolSet(pack))
            ok = shaped = tool_uses = steps = 0
            truncated = leaked = exhausted = 0
            errors = []
            # The outputs themselves, not just the counts. Shape *compliance*
            # and shape *distinctness* are different questions -- a mode whose
            # outputs are indistinguishable from another mode's costs the grid
            # an axis whether or not it obeys its format rule -- and the second
            # question cannot be asked of a row of integers. Saving them also
            # means later analysis needs no further GPU time.
            outputs = []
            for inv in inputs:
                r = cell.invoke(inv)
                if r.trace.error:
                    errors.append(r.trace.error[:60])
                    continue
                if r.output.strip():
                    ok += 1
                shaped += shape_ok(mode, r.output)
                tool_uses += len(r.trace.tools_called)
                steps += r.trace.steps
                outputs.append({"input_id": inv.input_id, "text": inv.text,
                                "output": r.output,
                                "tools": list(r.trace.tools_called),
                                "finish": r.trace.finish_reason,
                                "flags": {k: v for k, v in r.trace.extra.items()
                                          if k in ("exhausted_steps", "think_leak",
                                                   "empty_output")}})
                truncated += r.trace.finish_reason == "length"
                leaked += bool(r.trace.extra.get("think_leak"))
                exhausted += bool(r.trace.extra.get("exhausted_steps"))
            n = len(inputs)
            row = {
                "cell": cell.name, "domain": domain, "mode": mode,
                "non_empty": ok, "correct_shape": shaped, "n": n,
                "tool_calls": tool_uses, "mean_steps": round(steps / n, 2),
                "peak_prompt_tokens": chat.peak_prompt_tokens,
                "truncated": truncated, "think_leaks": leaked,
                "exhausted": exhausted, "model_calls": chat.calls,
                "seconds": round(time.perf_counter() - t0, 1),
                "errors": errors, "outputs": outputs,
            }
            rows.append(row)
            print(f"{cell.name:<28} {ok:>3}/{n:<2} {shaped:>4}/{n:<2} "
                  f"{tool_uses:>6} {row['mean_steps']:>6} "
                  f"{chat.peak_prompt_tokens:>9} {row['seconds']:>6.0f}")
            flags = [f"{k}={v}" for k, v in
                     (("truncated", truncated), ("leaked", leaked),
                      ("exhausted", exhausted)) if v]
            if flags:
                print(f"{'':<28} {' '.join(flags)}")
            if errors:
                print(f"{'':<28} errors: {errors[0]}")

    OllamaChat(model=MODEL, host=HOST).release()
    peak = max(r["peak_prompt_tokens"] for r in rows)
    print(f"\npeak prompt tokens across all nine cells: {peak}")
    print(f"headroom at num_ctx 8192: {8192 - peak} tokens")
    print(f"total {time.perf_counter() - t_all:.0f}s")

    out = ROOT / "results" / "cells_smoke.json"
    out.write_text(json.dumps({"model": MODEL, "rows": rows, "peak": peak},
                              indent=2), encoding="utf-8")
    print(f"wrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
