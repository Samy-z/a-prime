"""Knowledge packs, the eight tools, and cells.

Runs in milliseconds and needs no GPU. The chat function is scripted, but the
response envelopes it replays were captured from a live server rather than
written from memory of the API, because the hand-written ones were wrong eight
times. See the note above `_tool_turn`.

What this still cannot check is whether a real model drives the loop sensibly.
That is measured separately, in BCH-014 and BCH-015.
"""

from __future__ import annotations

import copy
import functools
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime.adapter import Invocation  # noqa: E402
from aprime.cells.cell import FORMATS, Cell, build_inputs  # noqa: E402
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


# ------------------------------------------------------- captured envelopes ---
#
# These are built from response bodies a live server actually returned, stored
# in tests/fixtures/ollama_chat.json by scripts/capture_chat_fixtures.py.
#
# They used to be written from memory of the API, and did so wrongly eight
# times: an invented `sha256:` digest prefix, a check that conflated errored
# with empty, a missing `role`, no `</think>` leak, a turn that always
# terminated, a tool that always found what it was asked for, a missing
# `tool_calls[].id` and a missing `function.index`. Each cost a live run to
# find. A fake written from memory encodes what we believe the API does; a
# fixture encodes what it does, and the difference only shows up when they
# disagree, which is exactly when it matters.
#
# The envelope comes from the capture. Only the payload -- a tool name, its
# arguments, the text of an answer -- is substituted, because a test needs to
# choose those. Everything structural stays as the server sent it.

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ollama_chat.json"


def _captured():
    if not FIXTURES.exists():
        pytest.fail(
            f"{FIXTURES.name} is missing. Run scripts/capture_chat_fixtures.py "
            f"against a live server. These tests deliberately do not fall back "
            f"to hand-written doubles, because that fallback is what hid eight "
            f"divergences from the real API.")
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=1)
def _by_label():
    return {f["label"]: f for f in _captured()["fixtures"]}


def _envelope(label):
    """A deep copy of one captured response body, safe to mutate."""
    fx = _by_label()
    if label not in fx:
        pytest.fail(f"no captured fixture labelled {label!r}; have "
                    f"{sorted(fx)}")
    return copy.deepcopy(fx[label]["response"])


def _tool_turn(name, args):
    """A tool-call turn in the envelope a live server sends, including the `id`
    and `function.index` that the hand-written version omitted."""
    body = _envelope("tool_call")
    call = body["message"]["tool_calls"][0]
    call["function"]["name"] = name
    call["function"]["arguments"] = args
    return body


def _text_turn(text, **kw):
    """A plain answer in a captured envelope, with the text substituted."""
    body = _envelope("text_stop")
    body["message"]["content"] = text
    body.setdefault("done_reason", "stop")
    body.update(kw)
    return body


def test_the_captured_envelope_carries_what_the_fakes_forgot():
    """A canary on the fixtures themselves.

    Two fields were absent from every hand-written double for the life of this
    file. If a re-capture ever drops them, the doubles quietly go back to being
    wrong in the same way, and nothing else here would notice.
    """
    call = _envelope("tool_call")["message"]["tool_calls"][0]
    assert call.get("id"), "a real tool call carries an id"
    assert "index" in call["function"], "a real tool call carries function.index"
    assert _envelope("text_stop")["message"]["role"] == "assistant"
    assert _envelope("truncated").get("done_reason") == "length"


def test_a_turn_with_several_tool_calls_echoes_each_id():
    """Without the id, results are matched to calls by position alone, so any
    reordering attaches an answer to the wrong question."""
    p = build_pack("banking", 10)
    eid = p.entity_ids()[0]
    two = _envelope("tool_call")
    first = two["message"]["tool_calls"][0]
    first["function"]["name"] = "get_account"
    first["function"]["arguments"] = {"account_id": eid}
    second = copy.deepcopy(first)
    second["id"] = "SECOND_CALL_ID"
    second["function"]["index"] = 1
    second["function"]["name"] = "get_lending_policy"
    second["function"]["arguments"] = {"topic": "income verification"}
    two["message"]["tool_calls"].append(second)

    seen = []

    def chat(messages, tools):
        seen.append(list(messages))
        return two if len(seen) == 1 else _text_turn("APPROVE, fine.")

    Cell(p, "agent", chat, "A").invoke(Invocation("i0", "q"))
    tool_msgs = [m for m in seen[-1] if m.get("role") == "tool"]
    assert len(tool_msgs) == 2
    assert tool_msgs[0]["tool_call_id"] == first["id"]
    assert tool_msgs[1]["tool_call_id"] == "SECOND_CALL_ID"


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


def test_running_out_of_steps_forces_a_final_answer_without_tools():
    """Exhaustion must not cost the corpus an input.

    On the first live run a quarter of every corpus came back empty this way:
    the model hunted for a figure it could not reach and the cell yielded "".
    A real deployment answers with what it has, so the tools are withdrawn and
    one last answer is demanded. The exhaustion stays visible in the trace.
    """
    p = build_pack("banking", 10)
    eid = p.entity_ids()[0]
    seen_tools = []

    def chat(messages, tools):
        seen_tools.append(tools)
        if len(seen_tools) > 3:
            return _text_turn("ESCALATE, the figures were not available.")
        return _tool_turn("get_account", {"account_id": eid})

    c = Cell(p, "agent", chat, "A", max_steps=3)
    r = c.invoke(Invocation("i0", "q"))
    assert r.trace.steps == 4, "three tool rounds plus the forced answer"
    assert r.trace.extra["exhausted_steps"] is True
    assert "empty_output" not in r.trace.extra
    assert r.output.startswith("ESCALATE")
    assert seen_tools[-1] is None, "the final call must withhold the tools"
    assert all(t for t in seen_tools[:-1])


def test_the_forced_final_answer_may_still_come_back_empty():
    """Withdrawing the tools does not guarantee an answer, and a blank is still
    a blank. Both flags have to survive so the study can exclude these."""
    p = build_pack("banking", 10)
    eid = p.entity_ids()[0]
    looping = [_tool_turn("get_account", {"account_id": eid})] * 10
    c = Cell(p, "agent", _scripted(*looping), "A", max_steps=3)
    r = c.invoke(Invocation("i0", "q"))
    assert r.trace.extra["exhausted_steps"] is True
    assert r.trace.extra["empty_output"] is True


def test_a_transport_failure_during_the_forced_answer_is_an_errored_response():
    calls = []

    def flaky(messages, tools):
        calls.append(tools)
        if tools is None:
            raise OSError("connection reset")
        return _tool_turn("get_account", {"account_id": build_pack(
            "banking", 10).entity_ids()[0]})

    r = Cell(build_pack("banking", 10), "agent", flaky, "A",
             max_steps=2).invoke(Invocation("i0", "q"))
    assert r.output == ""
    assert "connection reset" in r.trace.error


def test_a_leaked_reasoning_block_is_stripped_and_flagged():
    """granite4.2:8b emits its working into `content` with a closing tag whose
    opener never arrives, even with `think` off. The answer is the part after
    it; keeping the working would feed the detector the model's deliberation
    as though it were output."""
    p = build_pack("banking", 10)
    leaked = ("Let me reconsider. Maybe 42." + chr(10) + "</think>"
              + chr(10) + "APPROVE, the ratio holds.")
    r = Cell(p, "agent", _scripted(_text_turn(leaked)), "A").invoke(
        Invocation("i0", "q"))
    assert r.output == "APPROVE, the ratio holds."
    assert r.trace.extra["think_leak"] is True


def test_output_without_a_leak_is_untouched():
    p = build_pack("banking", 10)
    r = Cell(p, "agent", _scripted(_text_turn("APPROVE, fine.")), "A").invoke(
        Invocation("i0", "q"))
    assert r.output == "APPROVE, fine."
    assert "think_leak" not in r.trace.extra


def test_the_agent_format_asks_for_a_decision():
    """The agent format demands a line beginning APPROVE, DECLINE or ESCALATE. A
    corpus of plain questions makes that instruction incoherent, which is how
    the format scored zero on output shape while answering every input."""
    p = build_pack("banking", 18)
    plain = build_inputs(p, n=9, seed=1)
    decide = build_inputs(p, n=9, seed=1, output_format="agent")
    assert all("decid" in i.text.lower() for i in decide)
    assert not any("decid" in i.text.lower() for i in plain)


def test_every_agent_request_names_the_records_it_needs():
    """An unanswerable request measures error handling, not detection. The
    policy template asked the model to decide on a case it never named, and the
    model replied asking which case."""
    import re as _re
    ids = _re.compile("[A-Z]{2,3}-" + chr(92) + "d+")
    for domain in ("banking", "logistics", "hospitality"):
        p = build_pack(domain, 18)
        real = set(p.entity_ids()) | set(p.principal_ids()) |             set(p.document_ids()) | set(p.case_ids())
        for inv in build_inputs(p, n=9, seed=1, output_format="agent"):
            named = set(ids.findall(inv.text))
            assert named, f"no record named in {inv.input_id}: {inv.text}"
            assert named <= real, f"{inv.input_id} names a record that does not exist"


def test_each_format_gets_a_step_budget_that_suits_it():
    """The agent format chains by design and exhausted a shared budget of six."""
    p = build_pack("banking", 10)
    budgets = {m: Cell(p, m, _scripted(), "A").max_steps for m in FORMATS}
    assert budgets["agent"] > budgets["summary"]
    assert Cell(p, "agent", _scripted(), "A", max_steps=3).max_steps == 3


def test_the_forced_answer_restates_the_format_rule():
    """By the time the tools are withdrawn the system prompt is several tool
    results back, and the model answered in prose instead of the demanded
    shape."""
    p = build_pack("banking", 10)
    eid = p.entity_ids()[0]
    seen = []

    def chat(messages, tools):
        seen.append(list(messages))
        if tools is None:
            return _text_turn("APPROVE, fine.")
        return _tool_turn("get_account", {"account_id": eid})

    Cell(p, "agent", chat, "A", max_steps=2).invoke(Invocation("i0", "q"))
    final = seen[-1][-1]
    assert final["role"] == "user"
    assert "APPROVE" in final["content"], "the format rule must be restated"


def test_format_specific_corpora_line_up_record_for_record():
    """Only the wording may move, and a record may be added but never swapped.

    The decision form of the policy request has to name the case it is deciding
    on, because "check the policy and decide whether the case can proceed" with
    no case in it is unanswerable -- the model asked which case, correctly. So
    the agent corpus may reference more records than the plain one at the same
    position, never different ones.
    """
    import re as _re
    BS = chr(92)
    p = build_pack("logistics", 18)
    plain = build_inputs(p, n=9, seed=1)
    decide = build_inputs(p, n=9, seed=1, output_format="agent")
    ids = _re.compile("[A-Z]{2,3}-" + BS + "d+")
    for a, b in zip(plain, decide):
        assert a.text != b.text
        assert set(ids.findall(a.text)) <= set(ids.findall(b.text))


def test_a_format_specific_corpus_gets_its_own_input_ids():
    """The recorder groups by input id. Two different request texts sharing one
    id would silently pair unlike requests across arms."""
    p = build_pack("banking", 18)
    plain = {i.input_id for i in build_inputs(p, n=9, seed=1)}
    decide = {i.input_id for i in build_inputs(p, n=9, seed=1, output_format="agent")}
    assert not (plain & decide)
    assert all("-agent-" in i for i in decide)


def test_a_transport_failure_becomes_an_errored_response():
    def broken(messages, tools):
        raise OSError("connection reset")

    r = Cell(build_pack("banking", 10), "agent", broken, "A").invoke(
        Invocation("i0", "q"))
    assert r.output == "" and "connection reset" in r.trace.error


def test_each_format_asks_for_a_different_output_shape():
    p = build_pack("banking", 10)
    prompts = {m: Cell(p, m, _scripted(), "A").system_prompt(Invocation("i", "q"))
               for m in FORMATS}
    assert "JSON object" in prompts["extraction"]
    assert "sentences of plain prose" in prompts["summary"]
    assert "APPROVE" in prompts["agent"]
    assert len(set(prompts.values())) == 3


def test_an_invalid_format_is_refused():
    with pytest.raises(ValueError, match="output_format must be"):
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
