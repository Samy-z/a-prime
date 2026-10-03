"""Faults that change what a system retrieves, rather than what it returns.

`faults.py` breaks a system by rewriting its output after the fact. That is the
right mechanism for a fault with no cause inside the system, such as a truncating
proxy, and it works on any system under test including ones we did not build.

It cannot express the faults that matter most for an agent. A stale knowledge
base, a withdrawn tool, a retriever returning the wrong rows: none of these
rewrite an answer. They change what the system knows, and the model then writes a
different answer **by itself**. That difference is not cosmetic. An output we
rewrote carries our fingerprints, in vocabulary and sentence shape we chose; an
output the model wrote from degraded inputs carries only its own, which is what a
real regression looks like.

Cells already expose the hooks: `ToolSet(disabled=...)` withdraws a tool and
`ToolSet(stale=...)` serves a shifted view. What was missing is the part that
makes a fault usable as ground truth.

## Activation is the whole point

A degraded view only matters where the degradation changes an answer. Asking a
stale tool about a record whose value already matches the stale one returns the
truth, and the fault has not fired. That input is a **true negative, not a missed
detection**, and grading the detector as though the fault applied everywhere it
was configured would understate it badly.

So every tool call is replayed against both a clean and a faulty toolset, and the
comparison decides activation. This reuses `ActivationLog` from `faults.py`
rather than keeping a second notion of activation. Both mechanisms record per
`(input_id, sample_idx)`, which is what lets the request-level rate and the
per-principal rate come apart, and that separation is the only reason blast
regimes B2 and B3 exist. A per-input-only log destroys it silently, which is what
a first version of this did.

## Not every fault can be graded from inside the candidate arm

`stale_view` can: the tool is called, and the clean and faulty answers can be
compared on the spot.

`tool_withdrawn` cannot. A withdrawn tool is absent from the advertised schemas,
so the model never asks for it and there is no call to compare. What changed is
what the system *would* have done, which is only visible from the baseline arm.
So `tool_withdrawn` requires the caller to supply the baseline's tool usage,
collected by wrapping the clean arm in `UsageRecorder`, and **refuses to run
without it** rather than logging activation as false everywhere and reporting a
fault that fired on nothing.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from ..adapter import Invocation, Response
from ..faults import ActivationLog, FaultSpec
# Private, deliberately. `_in_blast` is the one piece of the injector that a
# second fault mechanism must share exactly rather than reimplement: it decides
# which requests or principals a fault applies to, and two implementations of
# that would diverge and make the blast-regime results incomparable.
from ..faults import _in_blast
from .cell import Cell
from .tools import SHAPES, ToolSet

# Each retrieval fault and the frozen-taxonomy class it belongs to. Written out
# rather than inferred, so that adding a shape to tools.py cannot quietly widen a
# pre-registered fault.
RETRIEVAL_FAULTS: dict[str, str] = {
    "stale_view": "F5",       # knowledge-base staleness
    "tool_withdrawn": "F3",   # upstream tool renamed or removed
}

CellFactory = Callable[[ToolSet], Cell]


@dataclass
class RetrievalFault:
    """A cell reading through a degraded tool layer, with activation recorded.

    `inner` is a cell already built with the faulty toolset, because a cell's
    tools are part of its configuration and swapping them mid-run would make the
    arm's identity ambiguous. `clean` and `faulty` are separate toolsets used only
    to decide activation, so that replaying a call in order to diff it does not
    pollute the call log of the ones under test.

    `baseline_shapes` maps an input id to the tool shapes the clean system used
    for it. Only `tool_withdrawn` needs it, and it is required there.
    """

    inner: Cell
    spec: FaultSpec
    clean: ToolSet
    faulty: ToolSet
    baseline_shapes: Mapping[str, frozenset[str]] | None = None
    # Where to persist the labels. A resumed run never re-invokes the triples it
    # skips, so activation learned in an earlier session is lost unless it is
    # written down, and the loss is silent: the fault simply appears to have
    # fired on less of the corpus than it did. Written after every invocation,
    # because the alternative is losing it to whatever stops the run.
    store: Path | None = None
    log: ActivationLog = field(init=False)
    calls_seen: int = 0
    _counter: dict[str, int] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        if self.spec.name not in RETRIEVAL_FAULTS:
            raise ValueError(
                f"unknown retrieval fault {self.spec.name!r}; available: "
                f"{sorted(RETRIEVAL_FAULTS)}")
        expected = RETRIEVAL_FAULTS[self.spec.name]
        if self.spec.fault_class != expected:
            raise ValueError(
                f"{self.spec.name!r} is fault class {expected} in the frozen "
                f"taxonomy, not {self.spec.fault_class!r}. The taxonomy is "
                f"pre-registered, and relabelling a fault afterwards is how a "
                f"per-class result stops meaning anything.")
        if self.spec.name == "tool_withdrawn" and self.baseline_shapes is None:
            raise ValueError(
                "tool_withdrawn needs baseline_shapes. A withdrawn tool is not "
                "in the advertised schemas, so the model never calls it and "
                "there is no call to compare: activation is only visible from "
                "what the baseline arm did. Without it every input would be "
                "logged as unaffected and the fault would appear to have fired "
                "on nothing, which is worse than refusing.")
        self.log = ActivationLog(self.spec)
        self.log.load_from(self.store)

    @property
    def arm(self) -> str:
        return self.inner.arm

    def _persist(self) -> None:
        self.log.persist_to(self.store)

    @property
    def name(self) -> str:
        return f"{self.inner.name}+{self.spec.cell_id}"

    def _withdrawn_shapes(self) -> frozenset[str]:
        return frozenset(self.faulty.disabled)

    def invoke(self, inv: Invocation) -> Response:
        idx = self._counter.get(inv.input_id, 0)
        self._counter[inv.input_id] = idx + 1

        # The cell's tools are fixed at construction, so a request outside the
        # blast radius still runs against them. The regime therefore gates what
        # we *count*, not what the system does, and saying otherwise would be a
        # lie whenever the fault still bit.
        in_blast = _in_blast(self.spec, inv)

        log = self.inner.tools.calls
        before = len(log)
        resp = self.inner.invoke(inv)
        used = log[before:]

        if self.spec.name == "tool_withdrawn":
            wanted = (self.baseline_shapes or {}).get(inv.input_id, frozenset())
            activated = bool(wanted & self._withdrawn_shapes())
            self.calls_seen += len(used)
        else:
            activated = False
            for tool_name, args in used:
                self.calls_seen += 1
                if self.clean.call(tool_name, dict(args)) != self.faulty.call(
                        tool_name, dict(args)):
                    activated = True

        self.log.record(inv.input_id, idx, activated and in_blast)
        self._persist()
        return resp


def _validate(shapes: Iterable[str]) -> frozenset[str]:
    unknown = set(shapes) - set(SHAPES)
    if unknown:
        raise ValueError(
            f"not tool shapes: {sorted(unknown)}; available: {sorted(SHAPES)}")
    if not shapes:
        raise ValueError("a fault over no shapes is not a fault")
    return frozenset(shapes)


def stale_view(
    pack,
    make_cell: CellFactory,
    shapes: Iterable[str],
    severity: float = 1.0,
    regime: str = "B0",
    share: float = 1.0,
    seed: int = 0,
) -> RetrievalFault:
    """A cell whose reads come from a knowledge base that has fallen behind.

    **A knowledge base that has fallen behind is behind for every read from it**,
    so staling one shape and calling it a stale knowledge base overstates how
    localised the fault is. It also depresses activation sharply: staling one
    shape fired on 2 of 12 inputs, where staling the four readable shapes fired
    on 15 of 30 (BCH-014, ENG-007).

    `make_cell(tools)` builds the cell, so the caller owns the domain, output
    format and arm while this owns the tools.
    """
    picked = _validate(shapes)
    faulty = ToolSet(pack, stale=picked)
    return RetrievalFault(
        inner=make_cell(faulty),
        spec=FaultSpec(fault_class="F5", name="stale_view", severity=severity,
                       regime=regime, share=share, seed=seed),
        clean=ToolSet(pack),
        faulty=ToolSet(pack, stale=picked),
    )


def tool_withdrawn(
    pack,
    make_cell: CellFactory,
    shapes: Iterable[str],
    baseline_shapes: Mapping[str, frozenset[str]],
    severity: float = 1.0,
    regime: str = "B0",
    share: float = 1.0,
    seed: int = 0,
) -> RetrievalFault:
    """A cell that has lost a tool it was built expecting.

    `baseline_shapes` maps input id to the shapes the clean system used, which
    comes from a baseline run. It is required: see the module docstring.
    """
    picked = _validate(shapes)
    faulty = ToolSet(pack, disabled=picked)
    return RetrievalFault(
        inner=make_cell(faulty),
        spec=FaultSpec(fault_class="F3", name="tool_withdrawn",
                       severity=severity, regime=regime, share=share, seed=seed),
        clean=ToolSet(pack),
        faulty=ToolSet(pack, disabled=picked),
        baseline_shapes=baseline_shapes,
    )


@dataclass
class UsageRecorder:
    """A baseline cell, plus which tool shapes it used for each input.

    Wraps the clean arm so `tool_withdrawn` can be graded. `ToolSet.calls` is a
    flat log with no input id on each entry, so usage cannot be attributed after
    the fact; pooling shapes across the corpus would mark every input as affected
    and inflate the apparent activation rate to 1.0. Recording it per invocation
    is the only honest option, and it costs nothing.

    Shapes rather than tool names, because a tool is withdrawn by shape and the
    names differ per domain.
    """

    inner: Cell
    shapes_by_input: dict[str, set[str]] = field(default_factory=dict)

    @property
    def arm(self) -> str:
        return self.inner.arm

    @property
    def name(self) -> str:
        return self.inner.name

    def invoke(self, inv: Invocation) -> Response:
        log = self.inner.tools.calls
        before = len(log)
        resp = self.inner.invoke(inv)
        seen = self.shapes_by_input.setdefault(inv.input_id, set())
        for tool_name, _ in log[before:]:
            shape = self.inner.tools.shape_of(tool_name)
            if shape is not None:
                seen.add(shape)
        return resp

    def frozen(self) -> dict[str, frozenset[str]]:
        """What `tool_withdrawn` wants, in the shape it wants it."""
        return {k: frozenset(v) for k, v in self.shapes_by_input.items()}


def activation_warnings(
    touched: Iterable[str],
    input_ids: Iterable[str],
    q: float = 0.10,
    label: str = "fault",
) -> list[str]:
    """The gradability check, over a plain set of input ids.

    Separate from `check_activation_is_usable` so that labels reloaded from disk
    can be checked without rebuilding an `ActivationLog` around them, which an
    earlier version of the study runner did by constructing a fake one.
    """
    ids = set(input_ids)
    if not ids:
        return []
    floor = int(round(1 / q))
    hit = len(set(touched) & ids)
    if hit >= floor:
        return []
    rate = hit / len(ids)
    advice = (f"Raise the corpus to about {int(floor / rate)} inputs at this "
              f"activation rate" if rate > 0 else
              "The fault never fired, so no corpus size helps")
    return [f"{label}: fired on {hit} of {len(ids)} inputs, below the {floor} "
            f"findings the estimator can report at q={q} (MTH-024). Nothing can "
            f"be flagged at this size whatever the detector does, so an empty "
            f"report will carry no information. {advice}, or choose a fault with "
            f"a higher activation rate."]


def check_activation_is_usable(
    log: ActivationLog,
    input_ids: Iterable[str],
    q: float = 0.10,
) -> list[str]:
    """Whether a fault fired on enough inputs to be gradable at all.

    The FDR estimator cannot report fewer than `1/q` findings (MTH-024), so a
    fault that fired on fewer inputs than that cannot be detected however good
    the detector is, and a run in that state measures nothing. Saying so before
    the GPU time is spent is much cheaper than saying so after, which is how the
    first two end-to-end runs were spent.
    """
    return activation_warnings(log.touched, input_ids, q=q,
                               label=log.spec.cell_id)


__all__ = ["RETRIEVAL_FAULTS", "CellFactory", "RetrievalFault",
           "UsageRecorder", "activation_warnings",
           "check_activation_is_usable", "stale_view", "tool_withdrawn"]
