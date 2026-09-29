"""Can the model pool actually pick the right tool out of eight?

The model survey measured tool chaining at 12 out of 12, but with a two-tool
set. Choosing correctly among eight is a harder task and we have no number for
it. Nine domain cells are about to be built on the assumption that it works, so
it is worth two minutes of GPU to find out first.

Measures three things at once:

1. **Selection accuracy.** Given a request that unambiguously needs one specific
   tool, does the model call that tool?
2. **Chaining.** Given a request needing one tool's output as another's input,
   does it get through both steps?
3. **Prompt token cost of eight schemas.** This answers the other half of the
   context-budget question: tool definitions are paid on every single call, so
   they set the floor under the context cap.

Every call passes `keep_alive: 0`, so each model unloads as soon as its turn
ends instead of holding VRAM.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

HOST = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:11434"
MODELS = ["granite4.2:8b", "ministral-3:8b", "qwen3.5:9b", "ministral-3:3b"]

SYSTEM = (
    "You are a claims assessor for a retail bank. Use the available tools to "
    "answer. Call exactly one tool at a time and wait for its result."
)


def tool(name, desc, props, required):
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {"type": "object", "properties": props, "required": required},
        },
    }


S = {"type": "string"}
N = {"type": "number"}

TOOLS = [
    tool("get_account", "Retrieve one account record by its account id.",
         {"account_id": S}, ["account_id"]),
    tool("search_transactions",
         "Search transactions for an account, optionally filtered by amount.",
         {"account_id": S, "min_amount": N, "max_amount": N}, ["account_id"]),
    tool("get_lending_policy",
         "Retrieve the written lending policy for a named topic.",
         {"topic": S}, ["topic"]),
    tool("compute_ratio",
         "Compute a debt-to-income ratio from two figures.",
         {"debt": N, "income": N}, ["debt", "income"]),
    tool("check_eligibility",
         "Evaluate whether an applicant meets lending criteria for a product.",
         {"applicant_id": S, "product": S}, ["applicant_id", "product"]),
    tool("list_prior_applications",
         "List an applicant's previous loan applications.",
         {"applicant_id": S}, ["applicant_id"]),
    tool("validate_document",
         "Check whether a submitted document is valid and unexpired.",
         {"document_id": S}, ["document_id"]),
    tool("escalate_case",
         "Escalate a case to a human underwriter with a stated reason.",
         {"case_id": S, "reason": S}, ["case_id", "reason"]),
]

# Two phrasings per tool, so a miss is less likely to be one unlucky wording.
SINGLE = [
    ("get_account", "Pull up account AC-4471 for me."),
    ("get_account", "What does the record for account AC-9930 say?"),
    ("search_transactions", "Show transactions over 5000 on account AC-4471."),
    ("search_transactions", "Find any payments under 50 on account AC-1200."),
    ("get_lending_policy", "What is our written policy on self-employed borrowers?"),
    ("get_lending_policy", "Look up the lending policy covering buy-to-let."),
    ("compute_ratio", "Work out the debt to income ratio for debt 18000 and income 54000."),
    ("compute_ratio", "If someone owes 9000 and earns 30000, what is their ratio?"),
    ("check_eligibility", "Is applicant AP-771 eligible for the fixed-rate mortgage?"),
    ("check_eligibility", "Does AP-302 meet the criteria for a personal loan?"),
    ("list_prior_applications", "Has applicant AP-771 applied to us before?"),
    ("list_prior_applications", "Show me AP-118's earlier applications."),
    ("validate_document", "Is document DOC-5512 still valid?"),
    ("validate_document", "Check whether DOC-8890 has expired."),
    ("escalate_case", "Send case CS-220 to an underwriter, the income is unverifiable."),
    ("escalate_case", "Escalate CS-47 please, the documents look inconsistent."),
]

# Step one returns an id that step two needs.
CHAINED = [
    (("get_account", "search_transactions"),
     "For account AC-4471, find the transactions above 5000."),
    (("list_prior_applications", "check_eligibility"),
     "Check AP-771's application history, then tell me if they qualify for a personal loan."),
    (("compute_ratio", "check_eligibility"),
     "Applicant AP-302 owes 18000 and earns 54000. Work out their ratio, then "
     "check whether they qualify for a personal loan."),
    (("validate_document", "escalate_case"),
     "Check document DOC-5512, and if it is not valid escalate case CS-220."),
]

FAKE_RESULTS = {
    "get_account": '{"account_id": "AC-4471", "holder_id": "AP-771", "status": "open"}',
    "search_transactions": '{"count": 3, "total": 21400}',
    "get_lending_policy": '{"topic": "self-employed", "min_years_trading": 2}',
    "compute_ratio": '{"ratio": 0.333}',
    "check_eligibility": '{"eligible": true}',
    "list_prior_applications": '{"applications": [{"id": "AP-771-1", "outcome": "declined"}]}',
    "validate_document": '{"document_id": "DOC-5512", "valid": false}',
    "escalate_case": '{"case_id": "CS-220", "queued": true}',
}


def chat(model, messages, use_tools=True, num_predict=160):
    payload = {
        "model": model, "messages": messages, "stream": False,
        "keep_alive": 0, "think": False,
        "options": {"num_ctx": 8192, "temperature": 0.0, "top_p": 1.0,
                    "top_k": 1, "num_predict": num_predict},
    }
    if use_tools:
        payload["tools"] = TOOLS
    req = urllib.request.Request(
        f"{HOST}/api/chat", data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())


def called(body):
    calls = (body.get("message") or {}).get("tool_calls") or []
    return [c.get("function", {}).get("name") for c in calls]


def main() -> int:
    t_all = time.perf_counter()
    rows = []
    print(f"host {HOST}\n8 tools, temperature 0, num_ctx 8192\n")

    for model in MODELS:
        t0 = time.perf_counter()
        print(f"=== {model} ===")

        # Token cost of the schemas: same message, with and without tools.
        with_t = chat(model, [{"role": "system", "content": SYSTEM},
                              {"role": "user", "content": "hello"}], True, 8)
        without = chat(model, [{"role": "system", "content": SYSTEM},
                               {"role": "user", "content": "hello"}], False, 8)
        pt_with = with_t.get("prompt_eval_count", 0)
        pt_without = without.get("prompt_eval_count", 0)
        print(f"  prompt tokens: {pt_without} without tools, {pt_with} with 8 tools "
              f"-> schemas cost {pt_with - pt_without}")

        hits = 0
        wrong = []
        for want, prompt in SINGLE:
            body = chat(model, [{"role": "system", "content": SYSTEM},
                                {"role": "user", "content": prompt}])
            got = called(body)
            if got and got[0] == want:
                hits += 1
            else:
                wrong.append((want, got[0] if got else "NO CALL"))
        sel = hits / len(SINGLE)
        print(f"  selection  {hits}/{len(SINGLE)} = {sel:.0%}")
        for w, g in wrong[:4]:
            print(f"      wanted {w}, got {g}")

        chain_ok = 0
        for (first, second), prompt in CHAINED:
            msgs = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt}]
            b1 = chat(model, msgs)
            c1 = called(b1)
            if not c1:
                continue
            msgs.append(b1["message"])
            msgs.append({"role": "tool",
                         "content": FAKE_RESULTS.get(c1[0], "{}")})
            b2 = chat(model, msgs)
            c2 = called(b2)
            if c1[0] == first and c2 and c2[0] == second:
                chain_ok += 1
        print(f"  chaining   {chain_ok}/{len(CHAINED)}")
        print(f"  ({time.perf_counter() - t0:.0f}s)\n")

        rows.append({"model": model, "selection": sel, "hits": hits,
                     "n_single": len(SINGLE), "chain_ok": chain_ok,
                     "n_chain": len(CHAINED), "schema_tokens": pt_with - pt_without,
                     "prompt_with_tools": pt_with, "wrong": wrong})

    out = Path(__file__).resolve().parents[1] / "results" / "tool_selection.json"
    out.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    print(f"total {time.perf_counter() - t_all:.0f}s GPU")
    print(f"wrote {out.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
