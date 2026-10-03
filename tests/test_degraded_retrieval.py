"""Retrieval degradation, fault class F11: the wrong rows, not older ones.

A stale index is behind; a degraded one is confused. The hook must return rows
that are well-formed and belong to another record, reproducibly for the same
call, so the clean-versus-degraded replay that decides activation sees what
the cell saw. At the published floor of 10% noise many calls come back
unchanged, and those are true negatives rather than misses. No GPU.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime.adapter import Invocation  # noqa: E402
from aprime.cells.cell import Cell  # noqa: E402
from aprime.cells.packs import build_pack  # noqa: E402
from aprime.cells.retrieval_faults import (  # noqa: E402
    F11_LADDER,
    RETRIEVAL_FAULTS,
    degraded_retrieval,
)
from aprime.cells.tools import NAMES, SHAPES, ToolSet  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ollama_chat.json"
READS = ("lookup", "search", "policy", "evaluate", "history", "verify")


def _pack(n=18):
    return build_pack("banking", n_entities=n, seed=1)


def _envelope(label):
    if not FIXTURES.exists():
        pytest.fail(f"{FIXTURES.name} missing; run scripts/capture_chat_fixtures.py")
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    by = {f["label"]: f for f in data["fixtures"]}
    return copy.deepcopy(by[label]["response"])


def _tool_then_text(name, args, text="done."):
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


def _calls(p):
    """One representative call per readable shape, with real ids."""
    eid, pid = p.entity_ids()[0], p.principal_ids()[0]
    did, topic = p.document_ids()[0], sorted(p.policies)[0]
    return {
        "lookup": (NAMES["lookup"]["banking"], {"account_id": eid}),
        "search": (NAMES["search"]["banking"], {"account_id": eid}),
        "policy": (NAMES["policy"]["banking"], {"topic": topic}),
        "evaluate": (NAMES["evaluate"]["banking"],
                     {"applicant_id": pid, "product": "personal loan"}),
        "history": (NAMES["history"]["banking"], {"applicant_id": pid}),
        "verify": (NAMES["verify"]["banking"], {"document_id": did}),
    }


# ------------------------------------------------------------------ the hook


def test_the_ladder_is_the_published_one():
    assert F11_LADDER == (0.10, 0.20, 0.30)
    assert RETRIEVAL_FAULTS["degraded_retrieval"] == "F11"


def test_degraded_without_noise_is_refused_and_so_is_noise_outside_the_unit_interval():
    p = _pack()
    with pytest.raises(ValueError, match="no fault"):
        ToolSet(p, degraded=frozenset({"lookup"}))
    with pytest.raises(ValueError, match="fraction"):
        ToolSet(p, noise=1.5)


@pytest.mark.parametrize("shape", READS)
def test_at_full_noise_every_read_returns_a_well_formed_wrong_row(shape):
    """Same keys, different content, for every readable shape."""
    p = _pack()
    name, args = _calls(p)[shape]
    clean = ToolSet(p).call(name, args)
    bad = ToolSet(p, degraded=frozenset({shape}), noise=1.0).call(name, args)
    assert "error" not in clean and "error" not in bad
    assert set(clean) == set(bad), shape
    assert clean != bad, shape


def test_a_wrong_lookup_row_belongs_to_another_real_entity():
    p = _pack()
    name, args = _calls(p)["lookup"]
    bad = ToolSet(p, degraded=frozenset({"lookup"}), noise=1.0).call(name, args)
    assert bad["id"] != args["account_id"]
    assert bad == p.entities[bad["id"]]


def test_search_keeps_count_and_total_consistent_with_its_items():
    p = _pack()
    name, args = _calls(p)["search"]
    bad = ToolSet(p, degraded=frozenset({"search"}), noise=1.0).call(name, args)
    assert bad["count"] == len(bad["items"])
    assert bad["total"] == sum(e["amount"] for e in bad["items"])
    own = {e["id"] for e in p.events[args["account_id"]]}
    assert all(e["id"] not in own for e in bad["items"])


def test_degradation_is_reproducible_per_call_and_moves_with_the_seed():
    p = _pack()
    name, args = _calls(p)["search"]
    a = ToolSet(p, degraded=frozenset({"search"}), noise=0.5, seed=4)
    b = ToolSet(p, degraded=frozenset({"search"}), noise=0.5, seed=4)
    assert a.call(name, args) == b.call(name, args) == a.call(name, args)
    seeds = {json.dumps(ToolSet(p, degraded=frozenset({"search"}), noise=0.5,
                                seed=s).call(name, args), sort_keys=True)
             for s in range(6)}
    assert len(seeds) > 1


def test_at_the_published_floor_many_calls_come_back_unchanged():
    """10% noise: the controlled study measured no downstream change. Here
    that shows as a majority of true negatives, not as a bug."""
    p = _pack(n=36)
    clean, bad = ToolSet(p), ToolSet(p, degraded=frozenset({"lookup"}), noise=0.10)
    name = NAMES["lookup"]["banking"]
    same = sum(clean.call(name, {"account_id": e}) == bad.call(name, {"account_id": e})
               for e in p.entity_ids())
    assert same >= len(p.entity_ids()) * 0.6


def test_a_shape_that_does_not_read_is_untouched():
    p = _pack()
    name = NAMES["compute"]["banking"]
    args = {"debt": 9000, "income": 54000}
    assert (ToolSet(p).call(name, args)
            == ToolSet(p, degraded=frozenset(SHAPES), noise=1.0).call(name, args))


def test_stale_and_degraded_are_different_faults():
    """Stale shifts to older rows of the right record; degraded picks a wrong
    record. On the same call they disagree with each other and with clean."""
    p = _pack()
    name, args = _calls(p)["history"]
    clean = ToolSet(p).call(name, args)["records"]
    stale = ToolSet(p, stale=frozenset({"history"})).call(name, args)["records"]
    bad = ToolSet(p, degraded=frozenset({"history"}), noise=1.0).call(name, args)["records"]
    pid = args["applicant_id"]
    own = {e["id"] for e in p.entities.values() if e["applicant_id"] == pid}
    assert all(r["id"] in own for r in stale)       # older, but still theirs
    assert all(r["id"] not in own for r in bad)     # somebody else's
    assert len(clean) == len(stale) == len(bad)


# ------------------------------------------------------------ the fault


def _fault(p, noise, shapes=("lookup",), chat_args=None, seed=0):
    eid = p.entity_ids()[0]
    chat = _tool_then_text(NAMES["lookup"]["banking"], chat_args or {"account_id": eid})
    return degraded_retrieval(
        p, lambda tools: Cell(p, "summary", chat, "B", tools=tools),
        shapes, noise=noise, seed=seed)


def test_the_fault_names_f11_and_carries_noise_as_severity():
    f = _fault(_pack(), noise=0.2)
    assert f.spec.fault_class == "F11" and f.spec.severity == 0.2
    assert f.name.endswith("+F11:degraded_retrieval@0.2/B0")


def test_noise_outside_the_interval_is_refused_by_the_factory():
    with pytest.raises(ValueError, match="noise must be"):
        _fault(_pack(), noise=0.0)


def test_activation_fires_where_the_wrong_row_differs_and_not_where_it_does_not():
    p = _pack(n=36)
    fired = {}
    for i, eid in enumerate(p.entity_ids()):
        f = _fault(p, noise=0.5, chat_args={"account_id": eid}, seed=2)
        f.invoke(Invocation(input_id=f"in{i}", text="t"))
        fired[eid] = f.log.fired[(f"in{i}", 0)]
    # At 50% noise both outcomes occur across a corpus of 36 reads.
    assert any(fired.values()) and not all(fired.values())
    # And each outcome matches whether the degraded toolset changed that read.
    name = NAMES["lookup"]["banking"]
    for eid, hit in fired.items():
        changed = (ToolSet(p).call(name, {"account_id": eid})
                   != ToolSet(p, degraded=frozenset({"lookup"}), noise=0.5, seed=2)
                   .call(name, {"account_id": eid}))
        assert hit == changed, eid


def test_the_candidate_reads_the_wrong_row_and_the_clean_toolset_does_not():
    p = _pack()
    eid = p.entity_ids()[0]
    f = _fault(p, noise=1.0, chat_args={"account_id": eid})
    f.invoke(Invocation(input_id="in0", text="t"))
    name = NAMES["lookup"]["banking"]
    seen = f.inner.tools.call(name, {"account_id": eid})
    assert seen["id"] != eid
    assert f.clean.call(name, {"account_id": eid})["id"] == eid
    assert f.log.fired[("in0", 0)] is True
