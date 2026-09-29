"""Knowledge packs, the eight tools, and cells.

Tested with a scripted chat function rather than a model, so this runs in
milliseconds and needs no GPU. What it cannot check is whether a real model drives
the loop sensibly; that is measured separately and recorded in BCH-013.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime.adapter import Invocation  # noqa: E402
from aprime.cells.cell import MODES, Cell, build_inputs  # noqa: E402
from aprime.cells.packs import DOMAINS, all_packs, build_pack  # noqa: E402
from aprime.cells.tools import NAMES, SHAPES, ToolSet  # noqa: E402


# ------------------------------------------------------------------- packs ---


def test_every_domain_builds_and_has_the_same_structure():
    packs = all_packs(n_entities=12)
    assert set(packs) == set(DOMAINS)
    shapes = [tuple(sorted(p.counts())) for p in packs.values()]
    assert len(set(shapes)) == 1, "domains must have identical structure"
    for p in packs.values():
        c = p.counts()
        assert c["entities"] == 12
        assert c["principals"] >= 4 and c["policies"] >= 4
        assert c["events"] > 0 and c["documents"] >= 6 and c["cases"] >= 4


def test_packs_are_deterministic_given_a_seed():
    a = build_pack("banking", 10, seed=3)
    b = build_pack("banking", 10, seed=3)
    c = build_pack("banking", 10, seed=4)
    assert a.entities == b.entities
    assert a.entities != c.entities


def test_an_unknown_domain_is_refused():
    with pytest.raises(ValueError, match="unknown domain"):
        build_pack("aerospace")


def test_every_entity_points_at_a_real_principal():
    """Inputs must be answerable, so referential integrity is not optional."""
    for p in all_packs(n_entities=12).values():
        key = f"{p.vocab.principal_kind}_id"
        for e in p.entities.values():
            assert e[key] in p.principals


# ------------------------------------------------------------------- tools ---


def test_the_topology_is_identical_across_domains():
    """If the detector behaves differently by domain, that must be about subject
    matter and not about one domain getting a more complicated agent."""
    sigs = {}
    for d, p in all_packs(n_entities=10).items():
        ts = ToolSet(p)
        defs = ts._defs()
        sigs[d] = tuple((t.shape, len(t.properties), t.required and len(t.required))
                        for t in defs)
    assert len(set(sigs.values())) == 1, sigs
    assert len(SHAPES) == 8


def test_tool_names_differ_per_domain_but_shapes_do_not():
    b = ToolSet(build_pack("banking", 10)).names()
    l = ToolSet(build_pack("logistics", 10)).names()
    assert set(b) & set(l) == set(), "names should be domain-specific"
    assert len(b) == len(l) == 8


def test_all_eight_tools_answer_a_well_formed_call():
    p = build_pack("banking", 12)
    ts = ToolSet(p)
    eid, pid = p.entity_ids()[0], p.principal_ids()[0]
    did, cid = p.document_ids()[0], p.case_ids()[0]
    calls = {
        "get_account": {"account_id": eid},
        "search_transactions": {"account_id": eid, "min_amount": 0},
        "get_lending_policy": {"topic": sorted(p.policies)[0]},
        "compute_debt_ratio": {"debt": 9000, "income": 30000},
        "check_eligibility": {"applicant_id": pid, "product": "personal loan"},
        "list_prior_applications": {"applicant_id": pid},
        "validate_document": {"document_id": did},
        "escalate_case": {"case_id": cid, "reason": "inconsistent paperwork"},
    }
    assert set(calls) == set(ts.names())
    for name, args in calls.items():
        out = ts.call(name, args)
        assert "error" not in out, (name, out)


def test_a_malformed_call_returns_an_error_rather_than_raising():
    """Models do supply wrong argument names. A real tool answers; it does not
    crash the agent."""
    ts = ToolSet(build_pack("banking", 10))
    assert "error" in ts.call("get_account", {"nope": "x"})
    assert "error" in ts.call("no_such_tool", {})
    assert "available" in ts.call("no_such_tool", {})
    assert "error" in ts.call("compute_debt_ratio", {"debt": 1, "income": 0})


def test_alternative_argument_spellings_are_accepted():
    """Being strict here would measure the model's naming habits, not the
    detector."""
    p = build_pack("banking", 10)
    ts = ToolSet(p)
    eid = p.entity_ids()[0]
    for args in ({"account_id": eid}, {"accountid": eid}, {"id": eid}):
        assert "error" not in ts.call("get_account", args), args


def test_disabling_a_shape_withdraws_the_tool():
    """Fault class F3: an upstream tool renamed or removed while the agent still
    expects it."""
    p = build_pack("logistics", 10)
    full, broken = ToolSet(p), ToolSet(p, disabled=frozenset({"verify"}))
    assert len(full.names()) == 8 and len(broken.names()) == 7
    gone = NAMES["verify"]["logistics"]
    assert gone in full.names() and gone not in broken.names()
    assert "error" in broken.call(gone, {"document_id": "DOC-5500"})


def test_a_stale_view_keeps_the_shape_and_changes_the_content():
    """Staleness that broke the output structure would be caught for free by the
    structural checks, which is not what F5 and F11 look like."""
    p = build_pack("banking", 12)
    eid = p.entity_ids()[0]
    fresh = ToolSet(p).call("search_transactions", {"account_id": eid})
    stale = ToolSet(p, stale=frozenset({"search"})).call(
        "search_transactions", {"account_id": eid})
    assert set(fresh) == set(stale)
    assert fresh["count"] == stale["count"]
    if len(p.events[eid]) >= 2:
        assert fresh["items"] != stale["items"]


def test_calls_are_recorded_for_activation_instrumentation():
    ts = ToolSet(build_pack("banking", 10))
    ts.call("compute_debt_ratio", {"debt": 1, "income": 2})
    assert ts.calls == [("compute_debt_ratio", {"debt": 1, "income": 2})]


# ------------------------------------------------------------------- cells ---


def _scripted(*turns):
    """A chat function that replays a fixed sequence of responses."""
    seq = list(turns)

    def chat(messages, tools):
        return seq.pop(0) if seq else {"message": {"content": "done."}}

    return chat


# These mirror what a live Ollama 0.34.4 server returns, including the "role"
# key. An earlier version omitted it, which is the third time in this project a
# hand-written fake has diverged from the real API -- see the note in
# docs/knowledge/cells.md.
def _tool_turn(name, args):
    return {"message": {"role": "assistant", "content": "",
                        "tool_calls": [{"function": {"name": name, "arguments": args}}]}}


def _text_turn(text, **kw):
    return {"message": {"role": "assistant", "content": text},
            "done_reason": "stop", **kw}


def test_a_cell_presents_as_an_ordinary_system_under_test():
    p = build_pack("banking", 10)
    c = Cell(p, "summary", _scripted(_text_turn("All fine.")), "A")
    r = c.invoke(Invocation("i0", "status?"))
    assert r.output == "All fine."
    assert r.trace.steps == 1 and r.trace.tools_called == ()
    assert c.arm == "A" and c.name == "banking-summary"


def test_a_tool_call_is_executed_and_fed_back():
    p = build_pack("banking", 10)
    eid = p.entity_ids()[0]
    c = Cell(p, "agent",
             _scripted(_tool_turn("get_account", {"account_id": eid}),
                       _text_turn("APPROVE the record is open.")), "B")
    r = c.invoke(Invocation("i0", "status?"))
    assert r.trace.tools_called == ("get_account",)
    assert r.trace.steps == 2
    assert r.output.startswith("APPROVE")
    assert c.tools.calls[0][0] == "get_account"


def test_a_tool_result_reaches_the_model_as_a_tool_message():
    p = build_pack("banking", 10)
    eid = p.entity_ids()[0]
    seen: list[list[dict]] = []

    def chat(messages, tools):
        seen.append([dict(m) for m in messages])
        if len(seen) == 1:
            return _tool_turn("get_account", {"account_id": eid})
        return _text_turn("APPROVE fine.")

    Cell(p, "agent", chat, "A").invoke(Invocation("i0", "status?"))
    roles = [m["role"] for m in seen[-1]]
    assert "tool" in roles
    payload = json.loads([m for m in seen[-1] if m["role"] == "tool"][0]["content"])
    assert payload["id"] == eid


def test_string_encoded_arguments_are_parsed():
    """Some models return arguments as a JSON string rather than an object."""
    p = build_pack("banking", 10)
    eid = p.entity_ids()[0]
    c = Cell(p, "agent",
             _scripted(_tool_turn("get_account", json.dumps({"account_id": eid})),
                       _text_turn("APPROVE.")), "A")
    c.invoke(Invocation("i0", "q"))
    assert c.tools.calls[0][1] == {"account_id": eid}


def test_running_out_of_steps_still_returns_a_flagged_output():
    """A real deployment returns something to the user, so this has to produce a
    Response rather than an exception, with the exhaustion visible."""
    p = build_pack("banking", 10)
    eid = p.entity_ids()[0]
    looping = [_tool_turn("get_account", {"account_id": eid})] * 10
    c = Cell(p, "agent", _scripted(*looping), "A", max_steps=3)
    r = c.invoke(Invocation("i0", "q"))
    assert r.trace.steps == 3
    assert r.trace.extra["exhausted_steps"] is True
    assert r.trace.extra["empty_output"] is True


def test_a_transport_failure_becomes_an_errored_response():
    def broken(messages, tools):
        raise OSError("connection reset")

    r = Cell(build_pack("banking", 10), "agent", broken, "A").invoke(
        Invocation("i0", "q"))
    assert r.output == "" and "connection reset" in r.trace.error


def test_each_mode_asks_for_a_different_output_shape():
    p = build_pack("banking", 10)
    prompts = {m: Cell(p, m, _scripted(), "A").system_prompt(Invocation("i", "q"))
               for m in MODES}
    assert "JSON object" in prompts["extraction"]
    assert "sentences of plain prose" in prompts["summary"]
    assert "APPROVE" in prompts["agent"]
    assert len(set(prompts.values())) == 3


def test_an_invalid_mode_is_refused():
    with pytest.raises(ValueError, match="mode must be"):
        Cell(build_pack("banking", 10), "chatty", _scripted(), "A")


def test_identity_awareness_puts_the_requester_in_the_instructions():
    """Fault class F8b: per-user clustering with no fault present, which is the
    control needed to recognise a sticky routing fault."""
    p = build_pack("hospitality", 10)
    plain = Cell(p, "summary", _scripted(), "A")
    aware = Cell(p, "summary", _scripted(), "A", identity_aware=True)
    inv = Invocation("i0", "q", principal="user7")
    assert "user7" not in plain.system_prompt(inv)
    assert "user7" in aware.system_prompt(inv)
    assert aware.name.endswith("-identity")
    assert plain.system_prompt(inv) != aware.system_prompt(inv)


# ------------------------------------------------------------------ inputs ---


def test_inputs_reference_records_that_exist():
    """A corpus about non-existent records would measure error handling, which is
    a different question from whether the detector notices a change."""
    p = build_pack("logistics", 16)
    invs = build_inputs(p, n=27)
    assert len(invs) == 27
    known = set(p.entity_ids()) | set(p.principal_ids()) | set(p.document_ids()) \
        | set(p.case_ids()) | set(p.policies) | set(p.vocab.products)
    for inv in invs:
        assert any(k in inv.text for k in known), inv.text


def test_inputs_are_unique_and_deterministic():
    p = build_pack("banking", 16)
    a, b = build_inputs(p, n=30), build_inputs(p, n=30)
    assert [x.input_id for x in a] == [x.input_id for x in b]
    assert [x.text for x in a] == [x.text for x in b]
    assert len({x.input_id for x in a}) == 30


def test_inputs_exercise_every_tool_shape():
    p = build_pack("banking", 16)
    kinds = {inv.input_id.split("-")[1] for inv in build_inputs(p, n=27)}
    assert set(SHAPES) <= kinds


def test_requester_identities_are_assigned_only_when_asked():
    p = build_pack("hospitality", 12)
    assert all(i.principal is None for i in build_inputs(p, n=12))
    withusers = build_inputs(p, n=12, n_principals_as_users=4)
    assert {i.principal for i in withusers} == {"user0", "user1", "user2", "user3"}
