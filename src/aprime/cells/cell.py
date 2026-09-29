"""A cell: one domain crossed with one output format, as a system under test.

The three formats are named `extraction`, `summary` and `agent`, and `agent`
names what the cell must OUTPUT -- a short decision line -- not a kind of
system being audited. All three call tools, so all three are agents in the
ordinary sense. This used to be called a cell's `mode`, which collided with
the semantic modes that `clustering.py` finds in an output cloud, and the
collision confused a reader who had every reason to expect one word to mean
one thing.

Nine cells make the study's grid, three domains by three output formats. A cell
implements the same `invoke(Invocation) -> Response` interface as everything else,
so the recorder, the detector and the fault harness work on it unchanged.

## All three formats use the tools

An earlier sketch gave tools only to the agent format, which would have confined
retrieval and staleness faults to three of the nine cells. Real extraction and
summarisation agents retrieve before they write, so all three formats call tools
and differ in **what they must produce**:

| output format | must output | typical steps |
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
import re
import time
from dataclasses import dataclass, field
from typing import Callable

from ..adapter import Invocation, Response, Trace, check_arm
from .packs import Pack
from .tools import ToolSet

FORMATS = ("extraction", "summary", "agent")

# Steps a format gets before the tools are withdrawn. Agent chains by design
# and exhausted a shared budget of 6 on two inputs in three of nine cells; the
# other two answer after one or two retrievals and never came close.
_MAX_STEPS = {"extraction": 6, "summary": 6, "agent": 9}

# Some servers emit a reasoning block into `content` even with `think` off,
# closing it with a tag whose opener never arrived. Observed live on
# granite4.2:8b: the answer is real, it just has the model's working in front of
# it. Everything up to the last closing tag is that working.
_THINK_LEAK = re.compile(r"^.*</think>", re.DOTALL)

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
    output_format: str
    chat: ChatFn
    arm: str
    tools: ToolSet = None  # type: ignore[assignment]
    # 0 means "whatever this format needs"; see _MAX_STEPS.
    max_steps: int = 0
    identity_aware: bool = False
    name: str = ""

    def __post_init__(self) -> None:
        check_arm(self.arm)
        if self.output_format not in FORMATS:
            raise ValueError(
                f"output_format must be one of {FORMATS}, got "
                f"{self.output_format!r}")
        if not self.max_steps:
            self.max_steps = _MAX_STEPS[self.output_format]
        if self.tools is None:
            self.tools = ToolSet(self.pack)
        if not self.name:
            ident = "-identity" if self.identity_aware else ""
            self.name = f"{self.pack.domain}-{self.output_format}{ident}"

    # ------------------------------------------------------------------ prompt

    def system_prompt(self, inv: Invocation) -> str:
        v = self.pack.vocab
        parts = [
            f"You are a {v.principal_kind} case handler working with "
            f"{v.entity_kind} records. Use the tools to look up facts rather "
            f"than guessing them.",
            _FORMAT_RULES[self.output_format],
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
                    # The real server stamps each tool call with an id, which
                    # every hand-written fake here omitted. Without echoing it
                    # back, a turn containing several tool calls has its results
                    # matched by position alone, so any reordering silently
                    # attaches an answer to the wrong question. Echoed when
                    # present; servers that do not send one are unaffected.
                    msg_out = {"role": "tool", "name": name,
                               "content": json.dumps(result)}
                    if tc.get("id"):
                        msg_out["tool_call_id"] = tc["id"]
                    messages.append(msg_out)
        except Exception as exc:  # noqa: BLE001
            return Response(
                output="",
                trace=Trace(latency_ms=(time.perf_counter() - t0) * 1000.0,
                            tools_called=tuple(called), steps=steps,
                            model_id=self.name,
                            error=f"{type(exc).__name__}: {exc}"),
            )

        # Ran out of steps while still asking for tools. Returning nothing here
        # threw away a quarter of the corpus on the first live run: the model
        # hunts for a figure, never finds it, and the cell yields "". A real
        # deployment answers with what it has, so the tools are withdrawn and
        # one final answer is demanded. Flagged either way, so the study can
        # exclude these if it chooses rather than silently scoring blanks.
        messages.append({
            "role": "user",
            "content": (
                "Stop searching and answer now, using only what you have "
                "already found. If something is missing, say so inside the "
                "required format, which is: " + _FORMAT_RULES[self.output_format]
            ),
        })
        try:
            body = self.chat(messages, None)
        except Exception as exc:  # noqa: BLE001
            return Response(
                output="",
                trace=Trace(latency_ms=(time.perf_counter() - t0) * 1000.0,
                            tools_called=tuple(called), steps=steps,
                            model_id=self.name,
                            error=f"{type(exc).__name__}: {exc}"),
            )
        steps += 1
        content = (body.get("message") or {}).get("content") or ""
        return self._done(content, called, steps, t0, "max_steps", body,
                          extra={"exhausted_steps": True})

    def _done(self, content, called, steps, t0, finish, body, extra=None) -> Response:
        ex = dict(extra or {})
        if "</think>" in content:
            content = _THINK_LEAK.sub("", content, count=1).lstrip()
            ex["think_leak"] = True
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


# The same nine requests as a decision to take rather than a question to answer.
# Asking "what is the status of AC-4000?" and then demanding a line beginning
# APPROVE, DECLINE or ESCALATE is an incoherent instruction, and on the first
# live run the model did the sensible thing and answered the question: agent
# the agent format scored 0 out of 4 on output shape in two domains of three while
# answering every input (BCH-015). The failure was in the corpus, not the model.
#
# Same record, same tool shape, same position in the list. Only the framing
# changes, because only this format's consumer sends a decision request.
_AGENT_TEMPLATES = {
    "lookup": "{entity} {eid} has come up for review. Check its status and "
              "decide what to do with it.",
    "search": "Review the {event}s on {entity} {eid} above {amount} and decide "
              "whether anything needs action.",
    "policy": "Case {cid} turns on our policy for {topic}. Check what the "
              "policy requires and decide whether the case can proceed.",
    "compute": "For {pid}, work out the ratio from their figures and decide "
               "whether it is within policy.",
    "evaluate": "Decide whether {pid} should be granted a {product}.",
    "history": "Check what we already hold for {pid} and decide whether to take "
               "their case forward.",
    "verify": "Document {did} was submitted in support of a case. Verify it and "
              "decide whether the case can proceed.",
    "act": "Case {cid} has inconsistent paperwork. Decide what to do and record "
           "the action.",
    "mixed": "For {entity} {eid}, check the status, then decide whether {pid} "
             "should be granted a {product}.",
}


def build_inputs(pack: Pack, n: int = 60, seed: int = 0,
                 n_principals_as_users: int = 0,
                 output_format: str | None = None) -> list[Invocation]:
    """Requests that reference real pack records, so the tools can succeed.

    Inputs must be answerable. A corpus of requests about entities that do not
    exist would measure how the system handles errors, which is a different
    question from whether the detector notices a change.

    `n_principals_as_users` assigns a requester identity to each input, drawn
    from that many distinct users. Needed for the sticky-routing fault, where
    the point is that the per-user rate and the per-request rate come apart.

    `output_format` phrases the request the way that format's consumer would.
    Only `agent`
    differs: a plain question is exactly what an extraction or summarisation
    consumer sends, whereas a decision line answers a decision request and
    nothing else. The records referenced, the tool shape exercised and the
    position in the list are identical across modes, so a corpus stays
    comparable; only the wording moves. Passing it also puts the format in the
    input
    id, because two different request texts must never share one id -- the
    recorder groups by input id, and a collision would silently pair
    unlike requests.
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
        if output_format == "agent":
            tmpl = _AGENT_TEMPLATES[kind]
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
        tag = f"{pack.domain}-{output_format}" if output_format else pack.domain
        out.append(Invocation(input_id=f"{tag}-{kind}-{i:03d}",
                              text=text, principal=principal))
    return out
