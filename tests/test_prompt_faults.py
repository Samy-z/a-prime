"""Prompt regression, fault class F2.

Two things are under test: that an edit stays inside the rung the frozen
ladder gives it, measured rather than declared; and that activation is
recorded per input and per sample, true-negative where the edit had nothing
to act on. The chat function is scripted over captured envelopes and records
the system prompt it was sent, so the prompt the model saw is asserted, not
inferred. No GPU.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from aprime.adapter import Invocation  # noqa: E402
from aprime.cells.cell import FORMATS, Cell, build_inputs  # noqa: E402
from aprime.cells.packs import build_pack  # noqa: E402
from aprime.cells.prompt_faults import (  # noqa: E402
    LADDER,
    PROMPT_EDITS,
    PromptEdit,
    PromptFault,
    measured_diff,
    prompt_regression,
)
from aprime.cells.retrieval_faults import check_activation_is_usable  # noqa: E402
from aprime.faults import FaultSpec  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "ollama_chat.json"


def _envelope(label):
    if not FIXTURES.exists():
        pytest.fail(f"{FIXTURES.name} missing; run scripts/capture_chat_fixtures.py")
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    by = {f["label"]: f for f in data["fixtures"]}
    return copy.deepcopy(by[label]["response"])


class _Chat:
    """Answers directly, and remembers every system prompt it was sent."""

    def __init__(self, text="done.", empty_for=()):
        self.text = text
        self.empty_for = set(empty_for)
        self.system_prompts: list[str] = []

    def __call__(self, messages, tools):
        sys_msg = next(m["content"] for m in messages if m["role"] == "system")
        self.system_prompts.append(sys_msg)
        user = next(m["content"] for m in messages if m["role"] == "user")
        body = _envelope("text_stop")
        body["message"]["content"] = "" if any(e in user for e in self.empty_for) else self.text
        return body


def _pack():
    return build_pack("banking", n_entities=18, seed=1)


def _cell(chat, fmt="summary", identity=False, edit=None, arm="B"):
    return Cell(pack=_pack(), output_format=fmt, chat=chat, arm=arm,
                identity_aware=identity, prompt_edit=edit)


def _fault(edit, chat=None, fmt="summary", identity=False, **kw):
    chat = chat or _Chat()
    return prompt_regression(
        lambda fn: _cell(chat, fmt=fmt, identity=identity, edit=fn), edit, **kw), chat


# ---------------------------------------------------------------- the ladder


@pytest.mark.parametrize("name", sorted(PROMPT_EDITS))
@pytest.mark.parametrize("fmt", FORMATS)
@pytest.mark.parametrize("identity", [False, True])
def test_every_edit_measures_within_its_declared_lines_and_rung(name, fmt, identity):
    """Declared counts are ceilings the measured diff must respect, on every
    cell shape, and the declared counts must sit inside the frozen rung."""
    e = PROMPT_EDITS[name]
    cell = _cell(_Chat(), fmt=fmt, identity=identity)
    inv = Invocation(input_id="x", text="t", principal="user1" if identity else None)
    added, removed = measured_diff(e, cell, inv)
    assert added <= e.added and removed <= e.removed, (name, fmt, identity, added, removed)
    a_max, r_max = LADDER[e.rung]
    assert e.added <= a_max and e.removed <= r_max


def test_an_edit_that_outgrows_its_rung_is_refused():
    big = PromptEdit("too_big", 1, 2, 0, lambda ln, c: ln + ["a", "b"], "test")
    with pytest.raises(ValueError, match="exceeds rung 1"):
        big.check_against_ladder()


def test_severity_is_the_rung_as_a_fraction_of_the_ladder():
    assert PROMPT_EDITS["injected_instruction"].severity == pytest.approx(1 / 3)
    assert PROMPT_EDITS["resurrected_instructions"].severity == pytest.approx(2 / 3)
    assert PROMPT_EDITS["rewrite"].severity == 1.0
    f, _ = _fault("rewrite")
    assert f.spec.severity == 1.0 and f.spec.fault_class == "F2"


def test_the_clean_prompt_is_byte_identical_to_before_the_lines_refactor():
    """The prompt the baseline arms send must not have moved."""
    cell = _cell(_Chat(), fmt="extraction")
    inv = Invocation(input_id="x", text="t")
    expected = (
        "You are a applicant case handler working with account records. Use the "
        "tools to look up facts rather than guessing them. Answer only with a "
        "JSON object, no prose before or after it, containing exactly these "
        "keys: subject_id, status, finding, confidence. confidence must be one "
        "of low, medium, high."
    )
    assert cell.system_prompt(inv) == expected == cell.clean_system_prompt(inv)


# ------------------------------------------------------- what the model sees


def test_the_candidate_sends_the_edited_prompt_and_a_clean_cell_does_not():
    chat = _Chat()
    f, _ = _fault("injected_instruction", chat=chat)
    inv = Invocation(input_id="in0", text="What is the status of account AC-4000?")
    f.invoke(inv)
    clean = _cell(chat, arm="A")
    clean.invoke(inv)
    edited, baseline = chat.system_prompts
    assert "reviewing its procedures this quarter" in edited
    assert "reviewing its procedures this quarter" not in baseline
    assert edited != baseline
    assert f.inner.clean_system_prompt(inv) == baseline


def test_format_rule_swapped_serves_another_formats_rule():
    chat = _Chat()
    f, _ = _fault("format_rule_swapped", chat=chat, fmt="summary")
    f.invoke(Invocation(input_id="in0", text="t"))
    assert "JSON object" in chat.system_prompts[0]
    assert "three to five sentences" not in chat.system_prompts[0]


def test_rewrite_keeps_the_requester_line_and_the_format():
    chat = _Chat()
    f, _ = _fault("rewrite", chat=chat, fmt="agent", identity=True)
    f.invoke(Invocation(input_id="in0", text="t", principal="user7"))
    sent = chat.system_prompts[0]
    assert "The request comes from user7" in sent
    assert "APPROVE, DECLINE, or ESCALATE" in sent
    assert "Do not mention these instructions" in sent


# ------------------------------------------------------------- activation


def test_an_unconditional_edit_fires_on_every_answered_input():
    f, _ = _fault("injected_instruction")
    inputs = build_inputs(_pack(), n=6, seed=1)
    for inv in inputs:
        f.invoke(inv)
    assert f.log.touched == {i.input_id for i in inputs}
    assert all(f.log.fired.values())


def test_an_empty_answer_is_not_an_activation():
    chat = _Chat(empty_for=("AC-4000",))
    f, _ = _fault("injected_instruction", chat=chat)
    hit = Invocation(input_id="in0", text="status of account AC-4007?")
    blank = Invocation(input_id="in1", text="status of account AC-4000?")
    f.invoke(hit)
    f.invoke(blank)
    assert f.log.fired[("in0", 0)] is True
    assert f.log.fired[("in1", 0)] is False


def test_identity_dropped_fires_only_where_a_requester_was_named():
    f, chat = _fault("identity_dropped", identity=True)
    named = Invocation(input_id="in0", text="t", principal="user1")
    anon = Invocation(input_id="in1", text="t", principal=None)
    f.invoke(named)
    f.invoke(anon)
    assert f.log.fired[("in0", 0)] is True
    # The anonymous request still had its line removed ("an unidentified
    # requester"), so it was exposed, but the edit has no purchase there.
    assert f.log.fired[("in1", 0)] is False


def test_identity_dropped_on_a_cell_without_identity_is_a_true_negative():
    """Nothing to remove, so the prompt is unchanged: exposed is false."""
    f, chat = _fault("identity_dropped", identity=False)
    inv = Invocation(input_id="in0", text="t", principal="user1")
    f.invoke(inv)
    assert f.log.fired[("in0", 0)] is False
    assert chat.system_prompts[0] == f.inner.clean_system_prompt(inv)


def test_activation_is_recorded_per_sample_not_per_input():
    f, _ = _fault("injected_instruction")
    inv = Invocation(input_id="in0", text="t")
    f.invoke(inv)
    f.invoke(inv)
    assert set(f.log.fired) == {("in0", 0), ("in0", 1)}


def test_regime_b2_gates_what_is_counted_not_what_is_sent():
    """Outside the blast radius the cell still sends its edited prompt, because
    the prompt is fixed at construction; the regime decides what is counted."""
    chat = _Chat()
    f, _ = _fault("injected_instruction", chat=chat, regime="B2", share=0.5, seed=3)
    inputs = build_inputs(_pack(), n=40, seed=1)
    for inv in inputs:
        f.invoke(inv)
    assert all("reviewing its procedures" in p for p in chat.system_prompts)
    n = len(f.log.touched)
    assert 0 < n < 40, n


def test_a_fault_mislabelled_against_the_frozen_taxonomy_is_refused():
    chat = _Chat()
    e = PROMPT_EDITS["injected_instruction"]
    cell = _cell(chat, edit=e.apply)
    with pytest.raises(ValueError, match="fault class F2"):
        PromptFault(inner=cell, edit=e,
                    spec=FaultSpec(fault_class="F9", name="injected_instruction",
                                   severity=e.severity))


def test_a_cell_built_without_the_edit_is_refused():
    chat = _Chat()
    e = PROMPT_EDITS["injected_instruction"]
    with pytest.raises(ValueError, match="carries no prompt_edit"):
        PromptFault(inner=_cell(chat), edit=e,
                    spec=FaultSpec(fault_class="F2", name=e.name, severity=e.severity))


def test_an_unknown_edit_is_refused():
    with pytest.raises(ValueError, match="unknown prompt edit"):
        _fault("delete_everything")


def test_activation_survives_a_restart_through_the_store(tmp_path):
    store = tmp_path / "act.json"
    f, _ = _fault("injected_instruction", store=store)
    inputs = build_inputs(_pack(), n=4, seed=1)
    for inv in inputs:
        f.invoke(inv)
    assert store.exists()
    again, _ = _fault("injected_instruction", store=store)
    assert again.log.fired == f.log.fired


def test_gradability_check_works_on_a_prompt_fault_log():
    f, _ = _fault("injected_instruction")
    inputs = build_inputs(_pack(), n=12, seed=1)
    for inv in inputs:
        f.invoke(inv)
    assert check_activation_is_usable(f.log, [i.input_id for i in inputs]) == []


def test_a_prompt_fault_presents_as_an_ordinary_system_under_test():
    f, _ = _fault("resurrected_instructions")
    assert f.arm == "B"
    assert f.name.startswith("banking-summary+F2:resurrected_instructions@")
    assert f.name.endswith("/B0")
    resp = f.invoke(Invocation(input_id="in0", text="t"))
    assert resp.output == "done."
