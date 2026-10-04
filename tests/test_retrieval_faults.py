"""Retrieval faults: faults that change what a system knows, not what it says.

Activation is the thing under test here, not the fault. A degraded view only
matters where the degradation changes an answer, and an input the fault never
bit is a true negative rather than a missed detection. Getting that wrong
understates the detector, and getting it wrong in the other direction
(marking everything as affected) makes a run look successful when it measured
nothing.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime.adapter import Invocation  # noqa: E402
from aprime.cells.cell import Cell, build_inputs  # noqa: E402
from aprime.cells.packs import build_pack  # noqa: E402
from aprime.cells.retrieval_faults import (  # noqa: E402
    RETRIEVAL_FAULTS,
    RetrievalFault,
    UsageRecorder,
    check_activation_is_usable,
    stale_view,
    tool_withdrawn,
)
from aprime.cells.tools import ToolSet  # noqa: E402
from aprime.faults import FaultSpec  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ollama_chat.json"


def _envelope(label):
    import copy
    import json

    if not FIXTURES.exists():
        pytest.fail(f"{FIXTURES.name} missing; run scripts/capture_chat_fixtures.py")
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    by = {f["label"]: f for f in data["fixtures"]}
    return copy.deepcopy(by[label]["response"])


def _tool_then_text(name, args, text="done."):
    """A chat function that calls one tool, then answers, on EVERY invocation.

    Keyed on the conversation length rather than a running counter. A counter
    that persists across invocations makes the double call a tool on the first
    input and then answer directly on every input after it, which silently turns
    a multi-input test into a one-input test.
    """

    def chat(messages, tools):
        asked_already = any(m.get("role") == "tool" for m in messages)
        if tools and not asked_already:
            body = _envelope("tool_call")
            call = body["message"]["tool_calls"][0]
            call["function"]["name"] = name
            call["function"]["arguments"] = args
            return body
        body = _envelope("text_stop")
        body["message"]["content"] = text
        return body

    return chat


def _pack():
    return build_pack("banking", n_entities=18, seed=1)


# --------------------------------------------------------------- stale views


def test_a_stale_view_that_changes_an_answer_counts_as_fired():
    p = _pack()
    # search shifts the event list, which always differs when there are two or
    # more events, so this is a case where the fault must bite.
    eid = next(e for e in p.entity_ids() if len(p.events[e]) >= 2)
    fault = stale_view(
        p, lambda tools: Cell(p, "summary",
                              _tool_then_text("search_transactions",
                                              {"account_id": eid}),
                              "B", tools=tools),
        shapes={"search"})
    fault.invoke(Invocation("i0", "q"))
    assert fault.log.fired[("i0", 0)] is True
    assert fault.log.touched == {"i0"}


def test_a_stale_view_that_changes_nothing_counts_as_a_true_negative():
    """The staleness is configured, the tool is called, and the answer is the
    same. Counting this as a missed detection would understate the detector."""
    p = _pack()
    # policy has no stale handling at all, so a call to it can never differ.
    fault = stale_view(
        p, lambda tools: Cell(p, "summary",
                              _tool_then_text("get_lending_policy",
                                              {"topic": "income verification"}),
                              "B", tools=tools),
        shapes={"search"})
    fault.invoke(Invocation("i0", "q"))
    assert fault.log.fired[("i0", 0)] is False
    assert fault.log.touched == set()


def test_activation_is_recorded_per_sample_not_per_input():
    """Per-input only would collapse the request-level and per-principal rates
    into one number, and telling those apart is the only reason blast regimes
    B2 and B3 exist."""
    p = _pack()
    eid = next(e for e in p.entity_ids() if len(p.events[e]) >= 2)
    fault = stale_view(
        p, lambda tools: Cell(p, "summary",
                              _tool_then_text("search_transactions",
                                              {"account_id": eid}),
                              "B", tools=tools),
        shapes={"search"})
    inv = Invocation("i0", "q")
    fault.invoke(inv)
    fault.invoke(inv)
    assert set(fault.log.fired) == {("i0", 0), ("i0", 1)}


def test_the_comparison_does_not_pollute_the_toolset_under_test():
    """Replaying a call to diff it must not appear in the cell's own call log,
    or the per-input activation instrumentation would corrupt the tool-use
    counts the bench also reports."""
    p = _pack()
    eid = p.entity_ids()[0]
    fault = stale_view(
        p, lambda tools: Cell(p, "summary",
                              _tool_then_text("get_account", {"account_id": eid}),
                              "B", tools=tools),
        shapes={"lookup"})
    fault.invoke(Invocation("i0", "q"))
    assert len(fault.inner.tools.calls) == 1, "one call, not three"


# ------------------------------------------------------- withdrawn tools


def test_withdrawing_a_tool_removes_it_from_the_advertised_set():
    p = _pack()
    full = ToolSet(p)
    gone = ToolSet(p, disabled=frozenset({"lookup"}))
    assert len(gone.names()) == len(full.names()) - 1
    assert gone.shape_of(full.names()[0]) is None


def test_tool_withdrawn_refuses_to_run_without_baseline_usage():
    """A withdrawn tool is never called, so there is no call to compare, and
    activation is only visible from what the baseline did. Logging false
    everywhere would report a fault that fired on nothing."""
    p = _pack()
    with pytest.raises(ValueError, match="baseline_shapes"):
        RetrievalFault(
            inner=Cell(p, "summary", _tool_then_text("get_account", {}), "B",
                       tools=ToolSet(p, disabled=frozenset({"lookup"}))),
            spec=FaultSpec(fault_class="F3", name="tool_withdrawn", severity=1.0),
            clean=ToolSet(p),
            faulty=ToolSet(p, disabled=frozenset({"lookup"})),
        )


def test_tool_withdrawn_fires_only_where_the_baseline_used_that_shape():
    p = _pack()
    baseline = {"used-it": frozenset({"lookup", "policy"}),
                "did-not": frozenset({"policy"})}
    fault = tool_withdrawn(
        p, lambda tools: Cell(p, "summary",
                              _tool_then_text("get_lending_policy",
                                              {"topic": "income verification"}),
                              "B", tools=tools),
        shapes={"lookup"}, baseline_shapes=baseline)
    fault.invoke(Invocation("used-it", "q"))
    fault.invoke(Invocation("did-not", "q"))
    assert fault.log.fired[("used-it", 0)] is True
    assert fault.log.fired[("did-not", 0)] is False


def test_usage_recorder_attributes_shapes_to_the_right_input():
    """ToolSet.calls is flat, so usage has to be captured per invocation.
    Pooling across the corpus would mark every input as affected."""
    p = _pack()
    eid = p.entity_ids()[0]
    rec = UsageRecorder(Cell(p, "summary",
                             _tool_then_text("get_account", {"account_id": eid}),
                             "A", tools=ToolSet(p)))
    rec.invoke(Invocation("i0", "q"))
    assert rec.frozen() == {"i0": frozenset({"lookup"})}
    assert rec.arm == "A"


def test_usage_recorder_output_matches_the_wrapped_cell():
    p = _pack()
    eid = p.entity_ids()[0]
    inner = Cell(p, "summary",
                 _tool_then_text("get_account", {"account_id": eid}, "the answer"),
                 "A", tools=ToolSet(p))
    out = UsageRecorder(inner).invoke(Invocation("i0", "q")).output
    assert out == "the answer", "the recorder must not alter what it observes"


# --------------------------------------------------------------- guard rails


def test_a_fault_mislabelled_against_the_frozen_taxonomy_is_refused():
    """The taxonomy is pre-registered. Relabelling a fault afterwards is how a
    per-class result stops meaning anything."""
    p = _pack()
    with pytest.raises(ValueError, match="frozen taxonomy"):
        RetrievalFault(
            inner=Cell(p, "summary", _tool_then_text("get_account", {}), "B",
                       tools=ToolSet(p)),
            spec=FaultSpec(fault_class="F7", name="stale_view", severity=1.0),
            clean=ToolSet(p), faulty=ToolSet(p))


def test_every_retrieval_fault_names_a_taxonomy_class():
    assert set(RETRIEVAL_FAULTS) == {"stale_view", "tool_withdrawn", "degraded_retrieval"}
    assert RETRIEVAL_FAULTS["degraded_retrieval"] == "F11"
    assert all(v.startswith("F") for v in RETRIEVAL_FAULTS.values())


def test_a_shape_that_does_not_exist_is_refused():
    p = _pack()
    with pytest.raises(ValueError, match="not tool shapes"):
        stale_view(p, lambda tools: Cell(p, "summary", _tool_then_text("x", {}),
                                         "B", tools=tools),
                   shapes={"teleport"})


def test_a_fault_over_no_shapes_is_refused():
    p = _pack()
    with pytest.raises(ValueError, match="not a fault"):
        stale_view(p, lambda tools: Cell(p, "summary", _tool_then_text("x", {}),
                                         "B", tools=tools), shapes=set())


# -------------------------------------------------- is the run gradable at all


def test_a_fault_below_the_discovery_floor_is_flagged_before_the_gpu_is_spent():
    """The estimator cannot report fewer than 1/q findings (MTH-024), so a fault
    firing on fewer inputs than that cannot be detected however good the
    detector is. The first two end-to-end runs were spent learning this."""
    p = _pack()
    eid = next(e for e in p.entity_ids() if len(p.events[e]) >= 2)
    fault = stale_view(
        p, lambda tools: Cell(p, "summary",
                              _tool_then_text("search_transactions",
                                              {"account_id": eid}),
                              "B", tools=tools),
        shapes={"search"})
    ids = [f"i{n}" for n in range(30)]
    for iid in ids[:3]:
        fault.invoke(Invocation(iid, "q"))
    warns = check_activation_is_usable(fault.log, ids, q=0.10)
    assert len(warns) == 1
    assert "MTH-024" in warns[0]
    assert "fired on 3 of 30" in warns[0]
    assert "100 inputs" in warns[0], "should say how large the corpus must be"


def test_enough_activation_raises_no_warning():
    p = _pack()
    eid = next(e for e in p.entity_ids() if len(p.events[e]) >= 2)
    fault = stale_view(
        p, lambda tools: Cell(p, "summary",
                              _tool_then_text("search_transactions",
                                              {"account_id": eid}),
                              "B", tools=tools),
        shapes={"search"})
    ids = [f"i{n}" for n in range(20)]
    for iid in ids[:12]:
        fault.invoke(Invocation(iid, "q"))
    assert check_activation_is_usable(fault.log, ids, q=0.10) == []


def test_a_fault_that_never_fires_says_no_corpus_size_helps():
    p = _pack()
    fault = stale_view(
        p, lambda tools: Cell(p, "summary",
                              _tool_then_text("get_lending_policy",
                                              {"topic": "income verification"}),
                              "B", tools=tools),
        shapes={"search"})
    ids = [f"i{n}" for n in range(30)]
    for iid in ids[:5]:
        fault.invoke(Invocation(iid, "q"))
    warns = check_activation_is_usable(fault.log, ids, q=0.10)
    assert "no corpus size helps" in warns[0]


def test_a_retrieval_fault_presents_as_an_ordinary_system_under_test():
    """The recorder must be able to drive it with no special handling."""
    p = _pack()
    inputs = build_inputs(p, n=2, seed=1, output_format="summary")
    eid = p.entity_ids()[0]
    fault = stale_view(
        p, lambda tools: Cell(p, "summary",
                              _tool_then_text("get_account", {"account_id": eid}),
                              "B", tools=tools),
        shapes={"lookup"})
    assert fault.arm == "B"
    assert "stale_view" in fault.name
    for inv in inputs:
        resp = fault.invoke(inv)
        assert resp.trace.model_id
