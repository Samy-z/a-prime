"""The eight tools a cell exposes, as deterministic lookups over a pack.

## Why eight, and why the same eight everywhere

Real agents are integrated: they retrieve data, process it through tools, then
emit a decision or a templated answer. A two-tool agent is not a smaller version
of that, it is a different thing, and lighter agents are the ones most likely to
be obsolete by the time this work is read. Eight tools also give a fault
injection far more room: breaking one tool out of eight touches only the inputs
that needed it, which is the per-input activation case the harness was built for
and could not previously exercise.

**The topology is identical across domains, only the vocabulary changes.** Eight
shapes, same parameter structure, same return structure. If the detector performs
differently on banking than on logistics, that difference has to be about the
subject matter, and not about one domain having been given a more complicated
agent to drive.

Measured before committing to this: all three 8B models in the pool selected the
right tool 16 times out of 16 among these eight, and the schemas cost 461 to 751
prompt tokens rather than the 1,200 to 2,000 the design had assumed (BCH-013).

## Fault hooks

`disabled` removes a tool from the advertised set, which is fault class F3: an
upstream tool renamed or withdrawn while the agent still expects it. `stale`
makes a tool answer from a shifted view of the pack, which is F5 and F11:
knowledge-base staleness and retrieval degradation. Both were listed as not
implemented, because they need a system that actually retrieves.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .packs import Pack

# shape -> per-domain name. The shape is what the study reasons about; the name
# is what the model sees.
NAMES: dict[str, dict[str, str]] = {
    "lookup":   {"banking": "get_account", "logistics": "get_shipment",
                 "hospitality": "get_booking"},
    "search":   {"banking": "search_transactions", "logistics": "search_movements",
                 "hospitality": "search_stays"},
    "policy":   {"banking": "get_lending_policy", "logistics": "get_customs_rule",
                 "hospitality": "get_rate_policy"},
    "compute":  {"banking": "compute_debt_ratio", "logistics": "compute_load_factor",
                 "hospitality": "compute_occupancy"},
    "evaluate": {"banking": "check_eligibility", "logistics": "check_clearance",
                 "hospitality": "check_restrictions"},
    "history":  {"banking": "list_prior_applications",
                 "logistics": "list_prior_movements",
                 "hospitality": "list_prior_stays"},
    "verify":   {"banking": "validate_document", "logistics": "validate_manifest",
                 "hospitality": "validate_id"},
    "act":      {"banking": "escalate_case", "logistics": "flag_hold",
                 "hospitality": "create_request"},
}

SHAPES = tuple(NAMES)

_COMPUTE_ARGS: dict[str, tuple[str, str]] = {
    "banking": ("debt", "income"),
    "logistics": ("loaded", "capacity"),
    "hospitality": ("booked", "available"),
}

_S = {"type": "string"}
_N = {"type": "number"}


@dataclass(frozen=True)
class ToolDef:
    shape: str
    name: str
    description: str
    properties: dict
    required: tuple[str, ...]

    def as_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.properties,
                    "required": list(self.required),
                },
            },
        }


@dataclass
class ToolSet:
    pack: Pack
    disabled: frozenset[str] = frozenset()   # shapes withdrawn: fault class F3
    stale: frozenset[str] = frozenset()      # shapes answering from a shifted view
    calls: list[tuple[str, dict]] = field(default_factory=list)

    # -------------------------------------------------------------- definitions

    def _defs(self) -> list[ToolDef]:
        d, v = self.pack.domain, self.pack.vocab
        ent, pri = v.entity_kind, v.principal_kind
        a, b = _COMPUTE_ARGS[d]
        out = [
            ToolDef("lookup", NAMES["lookup"][d],
                    f"Retrieve one {ent} record by its id.",
                    {f"{ent}_id": _S}, (f"{ent}_id",)),
            ToolDef("search", NAMES["search"][d],
                    f"Search the {v.event_kind} history of one {ent}, "
                    f"optionally filtered by amount.",
                    {f"{ent}_id": _S, "min_amount": _N, "max_amount": _N},
                    (f"{ent}_id",)),
            ToolDef("policy", NAMES["policy"][d],
                    "Retrieve the written policy for a named topic.",
                    {"topic": _S}, ("topic",)),
            ToolDef("compute", NAMES["compute"][d],
                    f"Compute the ratio of {a} to {b}.",
                    {a: _N, b: _N}, (a, b)),
            ToolDef("evaluate", NAMES["evaluate"][d],
                    f"Evaluate whether a {pri} meets the criteria for a product.",
                    {f"{pri}_id": _S, "product": _S}, (f"{pri}_id", "product")),
            ToolDef("history", NAMES["history"][d],
                    f"List a {pri}'s previous records.",
                    {f"{pri}_id": _S}, (f"{pri}_id",)),
            ToolDef("verify", NAMES["verify"][d],
                    "Check whether a submitted document is valid and unexpired.",
                    {"document_id": _S}, ("document_id",)),
            ToolDef("act", NAMES["act"][d],
                    "Record an action on a case, with a stated reason.",
                    {"case_id": _S, "reason": _S}, ("case_id", "reason")),
        ]
        return [t for t in out if t.shape not in self.disabled]

    def schemas(self) -> list[dict]:
        return [t.as_schema() for t in self._defs()]

    def names(self) -> list[str]:
        return [t.name for t in self._defs()]

    def shape_of(self, name: str) -> str | None:
        for t in self._defs():
            if t.name == name:
                return t.shape
        return None

    # ------------------------------------------------------------------ calling

    def call(self, name: str, args: dict) -> dict:
        """Execute a tool. Never raises.

        A real tool returns an error rather than crashing the agent, and the
        models do sometimes supply wrong argument names, so a malformed call has
        to produce something the model can read and recover from.
        """
        self.calls.append((name, dict(args or {})))
        shape = self.shape_of(name)
        if shape is None:
            return {"error": f"no such tool: {name}",
                    "available": self.names()}
        try:
            return _HANDLERS[shape](self, args or {})
        except Exception as exc:  # noqa: BLE001
            return {"error": f"{type(exc).__name__}: {exc}"}

    # --------------------------------------------------------------- internals

    def _arg(self, args: dict, *candidates: str) -> Any:
        """Accept any of several argument spellings.

        Models are inconsistent about whether the id field is `account_id`,
        `accountId` or just `id`. Being strict here would measure the model's
        naming habits rather than the detector.
        """
        for c in candidates:
            for key in (c, c.replace("_", ""), c.split("_")[0], "id"):
                if key in args:
                    return args[key]
        return None

    def _shift(self, seq: list, on: bool) -> list:
        """A stale view: drop the most recent item and repeat the oldest.

        Same length, same shape, older content. That is what staleness looks
        like from the outside, and it keeps the output structurally valid so the
        structural checks do not catch it for free.
        """
        if not on or len(seq) < 2:
            return seq
        return [seq[0]] + seq[:-1]


def _h_lookup(ts: ToolSet, args: dict) -> dict:
    eid = ts._arg(args, f"{ts.pack.vocab.entity_kind}_id", "entity_id")
    rec = ts.pack.entities.get(str(eid))
    if rec is None:
        return {"error": f"no such {ts.pack.vocab.entity_kind}: {eid}"}
    if "lookup" in ts.stale:
        rec = {**rec, "status": ts.pack.vocab.statuses[0]}
    return rec


def _h_search(ts: ToolSet, args: dict) -> dict:
    eid = str(ts._arg(args, f"{ts.pack.vocab.entity_kind}_id", "entity_id"))
    events = ts.pack.events.get(eid)
    if events is None:
        return {"error": f"no such {ts.pack.vocab.entity_kind}: {eid}"}
    lo = args.get("min_amount")
    hi = args.get("max_amount")
    hits = [e for e in ts._shift(events, "search" in ts.stale)
            if (lo is None or e["amount"] >= lo) and (hi is None or e["amount"] <= hi)]
    return {"count": len(hits), "total": sum(e["amount"] for e in hits),
            "items": hits}


def _h_policy(ts: ToolSet, args: dict) -> dict:
    topic = str(args.get("topic", "")).strip().lower()
    for name, pol in ts.pack.policies.items():
        if topic and (topic in name.lower() or name.lower() in topic):
            text = pol["text"].format(min_years=pol["min_years_on_record"],
                                      max_ratio=pol["max_ratio"],
                                      doc=pol["requires_document"])
            return {**{k: v for k, v in pol.items() if k != "text"}, "text": text}
    return {"error": f"no policy for topic: {args.get('topic')}",
            "available_topics": sorted(ts.pack.policies)}


def _h_compute(ts: ToolSet, args: dict) -> dict:
    a, b = _COMPUTE_ARGS[ts.pack.domain]
    num, den = args.get(a), args.get(b)
    if num is None or den is None:
        return {"error": f"need both {a} and {b}", "got": sorted(args)}
    if float(den) == 0:
        return {"error": f"{b} is zero"}
    return {"ratio": round(float(num) / float(den), 4), "numerator": num,
            "denominator": den}


def _h_evaluate(ts: ToolSet, args: dict) -> dict:
    pri = ts.pack.vocab.principal_kind
    pid = str(ts._arg(args, f"{pri}_id", "principal_id"))
    who = ts.pack.principals.get(pid)
    if who is None:
        return {"error": f"no such {pri}: {pid}"}
    product = str(args.get("product", ""))
    pol = next(iter(ts.pack.policies.values()))
    income = who["annual_income"] or 1
    ratio = round(who["existing_debt"] / income, 4)
    ok = (who["years_on_record"] >= pol["min_years_on_record"]
          and ratio <= pol["max_ratio"])
    return {"id": pid, "product": product, "meets_criteria": ok,
            "ratio": ratio, "threshold": pol["max_ratio"],
            "years_on_record": who["years_on_record"]}


def _h_history(ts: ToolSet, args: dict) -> dict:
    pri = ts.pack.vocab.principal_kind
    pid = str(ts._arg(args, f"{pri}_id", "principal_id"))
    if pid not in ts.pack.principals:
        return {"error": f"no such {pri}: {pid}"}
    owned = [e for e in ts.pack.entities.values() if e.get(f"{pri}_id") == pid]
    owned = ts._shift(owned, "history" in ts.stale)
    return {"count": len(owned),
            "records": [{"id": e["id"], "status": e["status"],
                         "product": e["product"], "opened": e["opened"]}
                        for e in owned]}


def _h_verify(ts: ToolSet, args: dict) -> dict:
    did = str(ts._arg(args, "document_id", "doc_id"))
    doc = ts.pack.documents.get(did)
    if doc is None:
        return {"error": f"no such document: {did}"}
    if "verify" in ts.stale:
        doc = {**doc, "valid": True}
    return doc


def _h_act(ts: ToolSet, args: dict) -> dict:
    cid = str(ts._arg(args, "case_id"))
    case = ts.pack.cases.get(cid)
    if case is None:
        return {"error": f"no such case: {cid}",
                "available_cases": ts.pack.case_ids()[:5]}
    return {"case_id": cid, "recorded": True,
            "reason": str(args.get("reason", ""))[:120]}


_HANDLERS: dict[str, Callable[[ToolSet, dict], dict]] = {
    "lookup": _h_lookup, "search": _h_search, "policy": _h_policy,
    "compute": _h_compute, "evaluate": _h_evaluate, "history": _h_history,
    "verify": _h_verify, "act": _h_act,
}
