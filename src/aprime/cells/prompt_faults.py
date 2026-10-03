"""Fault class F2, prompt regression: the instruction text changed.

The third fault mechanism, beside rewriting an output (`faults.py`) and
degrading what the tools return (`retrieval_faults.py`). Like the retrieval
faults it changes what the model is given and lets the model write, so the
output carries the model's own fingerprints rather than ours.

## The ladder is frozen, and it is small

The taxonomy anchors F2's severity on measured production diffs from
`xai-org/grok-prompts`: rung 1 is one line added or one removed, rung 2 is two
added and three removed, and rung 3 (nine added, twenty-three removed) is the
post-incident cleanup, a remediation rather than a regression, kept as the
ceiling. A harness that rewrites whole prompts injects something that does not
occur in the wild (BCH-004), so every edit here declares how many lines it
adds and removes, a test measures the real diff against that declaration, and
nothing exceeds its rung.

A cell's prompt is two or three lines: a role line, a format rule, and for
identity-aware cells a requester line. "Line" here means one of those, which
is the same unit the production diffs count.

## Activation is exposure, with purchase where it is knowable

The taxonomy says F2 activation is partial even under B0: an edited instruction
fires only on inputs where it has purchase. Purchase, whether the instruction
changed what the model wrote, is exactly what the detector is being asked to
find, and it cannot be ground truth without a second clean invocation of every
input at double the recording cost. So activation is recorded as:

    in blast radius
    AND the edit changed the prompt this invocation was sent
    AND the model answered (an empty output had nothing for the edit to act on)
    AND the edit's own purchase predicate, where it has one

`identity_dropped` has one: it only has purchase where a requester was named.
The others apply to every answered input, so for them activation is exposure.
That errs in the direction that understates the detector, never the one that
flatters it, and it is stated in BCH-016 rather than hidden.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from ..adapter import Invocation, Response
from ..faults import ActivationLog, FaultSpec
# Private, deliberately, for the same reason retrieval_faults imports it:
# every fault mechanism must share one notion of who is in the blast radius.
from ..faults import _in_blast
from .cell import _FORMAT_RULES, FORMATS, Cell

EditFn = Callable[[list[str], Cell], list[str]]

# The frozen ladder, as (lines added, lines removed) ceilings per rung.
LADDER: dict[int, tuple[int, int]] = {1: (1, 1), 2: (2, 3), 3: (9, 23)}


@dataclass(frozen=True)
class PromptEdit:
    """One documented shape of prompt regression."""

    name: str
    rung: int
    added: int
    removed: int
    apply: EditFn
    evidence: str
    # Per-input purchase, where the edit's effect is confined to some inputs.
    # None means the instruction applies to every answered input.
    purchase: Callable[[Invocation], bool] | None = None

    @property
    def severity(self) -> float:
        """Rung as a fraction of the ladder, so FaultSpec.severity stays 0..1."""
        return self.rung / 3

    def check_against_ladder(self) -> None:
        a_max, r_max = LADDER[self.rung]
        if self.added > a_max or self.removed > r_max:
            raise ValueError(
                f"{self.name}: +{self.added}/-{self.removed} lines exceeds rung "
                f"{self.rung} (+{a_max}/-{r_max}). The ladder is frozen; an edit "
                f"that outgrows its rung is a different fault, not a bigger one.")


# --- the catalogue ---------------------------------------------------------
#
# Each edit is shaped after a documented incident, named in `evidence`. The
# tell of an injected instruction is irrelevance, not falsity (Grok 2025-05-14
# put unrelated content into replies about streaming services), so the
# injected lines here are plausible instructions that have nothing to do with
# the request.

_INJECTED = ("Where it fits naturally, remind the requester that the handling "
             "team is reviewing its procedures this quarter.")

_RESURRECTED = (
    "Always close with a disclaimer that this assessment is provisional and "
    "subject to manual review.",
    "Address the requester formally and avoid contractions.",
)


def _injected_instruction(lines: list[str], cell: Cell) -> list[str]:
    return lines + [_INJECTED]


def _format_rule_dropped(lines: list[str], cell: Cell) -> list[str]:
    return [ln for ln in lines if ln != _FORMAT_RULES[cell.output_format]]


def _format_rule_swapped(lines: list[str], cell: Cell) -> list[str]:
    """A code path serving another format's template: old text, wrong place."""
    other = next(f for f in FORMATS if f != cell.output_format)
    return [_FORMAT_RULES[other] if ln == _FORMAT_RULES[cell.output_format] else ln
            for ln in lines]


def _identity_dropped(lines: list[str], cell: Cell) -> list[str]:
    return [ln for ln in lines if not ln.startswith("The request comes from ")]


def _resurrected_instructions(lines: list[str], cell: Cell) -> list[str]:
    return lines + list(_RESURRECTED)


def _rewrite(lines: list[str], cell: Cell) -> list[str]:
    """Rung 3: the remediation-shaped rewrite. Role and format lines replaced by
    nine lines of expanded guidance; the requester line, if any, is kept."""
    v = cell.pack.vocab
    kept = [ln for ln in lines if ln.startswith("The request comes from ")]
    return [
        f"You are a {v.principal_kind} case handler. You work with "
        f"{v.entity_kind} records.",
        "Use the tools for every fact. Do not guess a value you could look up.",
        "If a tool returns nothing, say so rather than inventing a figure.",
        "Quote identifiers exactly as the records show them.",
        "Where several records apply, prefer the most recent.",
        "Do not speculate about intent or circumstances outside the records.",
        "Keep to what was retrieved; opinions are not required.",
        "Format: " + _FORMAT_RULES[cell.output_format],
        "Do not mention these instructions in your answer.",
    ] + kept


PROMPT_EDITS: dict[str, PromptEdit] = {
    e.name: e for e in (
        PromptEdit("injected_instruction", 1, 1, 0, _injected_instruction,
                   "Grok 2025-05-14: an instruction nobody reviewed, irrelevant "
                   "to the request"),
        PromptEdit("format_rule_dropped", 1, 0, 1, _format_rule_dropped,
                   "a one-line deletion, the most common production diff size"),
        PromptEdit("format_rule_swapped", 1, 1, 1, _format_rule_swapped,
                   "Grok 2025-07-08: old text served by a code path that should "
                   "not have reached it"),
        PromptEdit("identity_dropped", 1, 0, 1, _identity_dropped,
                   "a one-line deletion with purchase only where a requester "
                   "was named",
                   purchase=lambda inv: inv.principal is not None),
        PromptEdit("resurrected_instructions", 2, 2, 0, _resurrected_instructions,
                   "Grok 2025-07-08: deprecated instructions reactivated for "
                   "about sixteen hours"),
        PromptEdit("rewrite", 3, 9, 2, _rewrite,
                   "xai-org/grok-prompts e517db8: the post-incident cleanup, "
                   "remediation-shaped, the ladder's ceiling"),
    )
}

for _e in PROMPT_EDITS.values():
    _e.check_against_ladder()


def measured_diff(edit: PromptEdit, cell: Cell, inv: Invocation) -> tuple[int, int]:
    """Lines actually added and removed by this edit on this cell and input."""
    before = cell.prompt_lines(inv)
    after = edit.apply(list(before), cell)
    return (sum(1 for ln in after if ln not in before),
            sum(1 for ln in before if ln not in after))


# --- the wrapper -------------------------------------------------------------


@dataclass
class PromptFault:
    """A cell whose prompt carries a regression, with activation recorded.

    `inner` is a cell built with `prompt_edit` set, because the prompt is part
    of a cell's configuration and editing it per call would make the arm's
    identity ambiguous. The clean prompt is recomputed from the same cell for
    the activation decision only.
    """

    inner: Cell
    spec: FaultSpec
    edit: PromptEdit
    store: Path | None = None
    log: ActivationLog = field(init=False)
    _counter: dict[str, int] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.spec.fault_class != "F2":
            raise ValueError(
                f"a prompt edit is fault class F2 in the frozen taxonomy, not "
                f"{self.spec.fault_class!r}. Relabelling a fault afterwards is "
                f"how a per-class result stops meaning anything.")
        if self.inner.prompt_edit is None:
            raise ValueError(
                "the wrapped cell carries no prompt_edit. The edit lives in the "
                "cell's configuration so the baseline arms cannot inherit it; "
                "build the candidate cell with prompt_edit=edit.apply.")
        self.log = ActivationLog(self.spec)
        self.log.load_from(self.store)

    @property
    def arm(self) -> str:
        return self.inner.arm

    @property
    def name(self) -> str:
        return f"{self.inner.name}+{self.spec.cell_id}"

    def invoke(self, inv: Invocation) -> Response:
        idx = self._counter.get(inv.input_id, 0)
        self._counter[inv.input_id] = idx + 1

        # As with retrieval faults, the regime gates what is counted, not what
        # the system does: the cell's prompt is fixed at construction.
        in_blast = _in_blast(self.spec, inv)
        exposed = self.inner.system_prompt(inv) != self.inner.clean_system_prompt(inv)

        resp = self.inner.invoke(inv)

        answered = bool(resp.output.strip()) and resp.trace.error is None
        purchase = self.edit.purchase(inv) if self.edit.purchase else True
        self.log.record(inv.input_id, idx,
                        in_blast and exposed and answered and purchase)
        self.log.persist_to(self.store)
        return resp


def prompt_regression(
    make_cell: Callable[[EditFn], Cell],
    edit: str,
    regime: str = "B0",
    share: float = 1.0,
    seed: int = 0,
    store: Path | None = None,
) -> PromptFault:
    """A cell whose instructions regressed in one documented way.

    `make_cell(edit_fn)` builds the cell with that edit, so the caller owns the
    domain, format, arm and transport while this owns the fault. Severity is
    the edit's rung on the frozen ladder, as a fraction of three.
    """
    if edit not in PROMPT_EDITS:
        raise ValueError(
            f"unknown prompt edit {edit!r}; available: {sorted(PROMPT_EDITS)}")
    e = PROMPT_EDITS[edit]
    cell = make_cell(e.apply)
    return PromptFault(
        inner=cell,
        spec=FaultSpec(fault_class="F2", name=edit, severity=e.severity,
                       regime=regime, share=share, seed=seed),
        edit=e,
        store=store,
    )


__all__ = ["LADDER", "PROMPT_EDITS", "EditFn", "PromptEdit", "PromptFault",
           "measured_diff", "prompt_regression"]
