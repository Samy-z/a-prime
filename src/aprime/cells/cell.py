"""A cell: one domain crossed with one output format, as a system under test.

Nine cells make the study's grid, three domains by three output formats. A cell
implements the same `invoke(Invocation) -> Response` interface as everything else,
so the recorder, the detector and the fault harness work on it unchanged.

## All three formats use the tools

An earlier sketch gave tools only to the agent format, which would have confined
retrieval and staleness faults to three of the nine cells. Real extraction and
summarisation agents retrieve before they write, so all three formats call tools
and differ in **what they must produce**:

| format | must output | typical steps |
|---|---|---|
| `extraction` | a JSON object with named keys | 1-2 tool calls, then JSON |
| `summary` | three to five sentences of prose | 1-2 tool calls, then prose |
| `agent` | a short decision line | several tool calls, chained |

That keeps the three genuinely different in output *shape*, which the detector's
per-shape thresholds depend on, while leaving every fault class injectable in
every cell.

## Identity awareness is a control, not a feature

`identity_aware` puts the requester into the instructions and asks for a tailored
answer. It exists for fault class F8b: an identity-aware system produces
per-user clustering **with no fault present at all**, which is the control needed
to tell a sticky routing fault apart from ordinary personalisation. Without that
control, per-user clustering the detector finds cannot be attributed to either.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Callable

from ..adapter import Invocation, Response, Trace, check_arm
from .packs import Pack
from .tools import ToolSet

MODES = ("extraction", "summary", "agent")

# The chat transport: messages and tool schemas in, an Ollama-shaped response
# body out. Injectable so a cell can be tested without a model.
ChatFn = Callable[[list[dict], list[dict]], dict]

_FORMAT_RULES = {
    "extraction": (
        "Answer only with a JSON object, no prose before or after it, containing "
        "exactly these keys: subject_id, status, finding, confidence. "
        "confidence must be one of low, medium, high."
    ),
    "summary": (
        "Answer with three to five sentences of plain prose. Do not use bullet "
        "points, headings or JSON. State what you found and any condition that "
        "applies to it."
    ),
    "agent": (
        "Gather what you need with the tools, then answer with a single short "
        "decision line beginning with one of APPROVE, DECLINE, or ESCALATE, "
        "followed by one sentence of reason."
    ),
}


@dataclass
class Cell:
    pack: Pack
    mode: str
    chat: ChatFn
    arm: str
    tools: ToolSet = None  # type: ignore[assignment]
    max_steps: int = 6
    identity_aware: bool = False
    name: str = ""

    def __post_init__(self) -> None:
        check_arm(self.arm)
        if self.mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {self.mode!r}")
        if self.tools is None:
            self.tools = ToolSet(self.pack)
        if not self.name:
            ident = "-identity" if self.identity_aware else ""
            self.name = f"{self.pack.domain}-{self.mode}{ident}"

    # ------------------------------------------------------------------ prompt

    def system_prompt(self, inv: Invocation) -> str:
        v = self.pack.vocab
        parts = [
            f"You are a {v.principal_kind} case handler working with "
            f"{v.entity_kind} records. Use the tools to look up facts rather "
            f"than guessing them.",
            _FORMAT_RULES[self.mode],
        ]
        if self.identity_aware:
            who = inv.principal or "an unidentified requester"
            parts.append(
                f"The request comes from {who}. Tailor the level of detail to "
                f"them and mention them by name in your answer."
            )
        return " ".join(parts)

    # ------------------------------------------------------------------ calling

    def invoke(self, inv: Invocation) -> Response:
        messages: list[dict] = [
            {"role": "system", "content": self.system_prompt(inv)},
            {"role": "user", "content": inv.text},
        ]
        schemas = self.tools.schemas()
        called: list[str] = []
        steps = 0
        t0 = time.perf_counter()
        finish: str | None = None

        try:
            for _ in range(self.max_steps):
                steps += 1
                body = self.chat(messages, schemas)
                msg = body.get("message") or {}
                finish = body.get("done_reason") or finish
                tool_calls = msg.get("tool_calls") or []
                if not tool_calls:
                    return self._done(msg.get("content") or "", called, steps,
                                      t0, finish, body)
                # Some responses omit the role. Appending verbatim would then
                # build a malformed conversation for the next call, so it is set
                # rather than assumed.
                messages.append({"role": "assistant", **msg})
                for tc in tool_calls:
                    fn = tc.get("function") or {}
                    name = fn.get("name", "")
                    args = fn.get("arguments") or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except ValueError:
                            args = {}
                    called.append(name)
                    result = self.tools.call(name, args)
                    messages.append({"role": "tool", "name": name,
                                     "content": json.dumps(result)})
        except Exception as exc:  # noqa: BLE001
            return Response(
                output="",
                trace=Trace(latency_ms=(time.perf_counter() - t0) * 1000.0,
                            tools_called=tuple(called), steps=steps,
                            model_id=self.name,
                            error=f"{type(exc).__name__}: {exc}"),
            )

        # Ran out of steps while still asking for tools. A real deployment would
        # return something to the user, so this is a real output, flagged.
        return self._done("", called, steps, t0, "max_steps", None,
                          extra={"exhausted_steps": True})

    def _done(self, content, called, steps, t0, finish, body, extra=None) -> Response:
        ex = dict(extra or {})
        if body is not None:
            ex["eval_count"] = body.get("eval_count")
            ex["prompt_eval_count"] = body.get("prompt_eval_count")
        if not content.strip():
            ex["empty_output"] = True
        return Response(
            output=content,
            trace=Trace(
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                tools_called=tuple(called),
                steps=steps,
                finish_reason=finish,
                model_id=self.name,
                extra=ex,
            ),
        )


# --------------------------------------------------------------------------
# input corpora
# --------------------------------------------------------------------------

_TEMPLATES = [
    ("lookup", "What is the current status of {entity} {eid}?"),
    ("search", "Show the {event}s on {entity} {eid} above {amount}."),
    ("policy", "What does our policy on {topic} require?"),
    ("compute", "For {pid}, work out the ratio from their figures and tell me "
                "whether it is within policy."),
    ("evaluate", "Does {pid} meet the criteria for a {product}?"),
    ("history", "What earlier records do we hold for {pid}?"),
    ("verify", "Is document {did} still valid?"),
    ("act", "Record an action on case {cid}: the paperwork is inconsistent."),
    ("mixed", "For {entity} {eid}, check the status and then tell me whether "
              "{pid} meets the criteria for a {product}."),
]


def build_inputs(pack: Pack, n: int = 60, seed: int = 0,
                 n_principals_as_users: int = 0) -> list[Invocation]:
    """Requests that reference real pack records, so the tools can succeed.

    Inputs must be answerable. A corpus of requests about entities that do not
    exist would measure how the system handles errors, which is a different
    question from whether the detector notices a change.

    `n_principals_as_users` assigns a requester identity to each input, drawn
    from that many distinct users. Needed for the sticky-routing fault, where
    the point is that the per-user rate and the per-request rate come apart.
    """
    import random

    rng = random.Random(f"{pack.domain}|{seed}".__hash__() & 0xFFFFFFFF)
    v = pack.vocab
    eids, pids = pack.entity_ids(), pack.principal_ids()
    dids, cids = pack.document_ids(), pack.case_ids()
    topics, products = sorted(pack.policies), list(v.products)

    out: list[Invocation] = []
    for i in range(n):
        kind, tmpl = _TEMPLATES[i % len(_TEMPLATES)]
        text = tmpl.format(
            entity=v.entity_kind, event=v.event_kind,
            eid=eids[i % len(eids)], pid=pids[i % len(pids)],
            did=dids[i % len(dids)], cid=cids[i % len(cids)],
            topic=topics[i % len(topics)], product=products[i % len(products)],
            amount=rng.choice([100, 1000, 5000]),
        )
        principal = None
        if n_principals_as_users:
            principal = f"user{i % n_principals_as_users}"
        out.append(Invocation(input_id=f"{pack.domain}-{kind}-{i:03d}",
                              text=text, principal=principal))
    return out
