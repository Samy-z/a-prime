"""Input deduplication.

Near-duplicate inputs corrupt two things at once. They inflate the apparent
number of independent observations, so the target-decoy FDR estimate is computed
over a corpus with far fewer effective units than it thinks it has. And they
create dense regions in embedding space that a hotspot search will happily
report as a finding.

Production corpora are full of them — the same question asked by a hundred
users, retried requests, templated traffic. Dedup happens before any counting,
testing or clustering, without exception.

**Known gap.** This module does exact and normalised matching only. Semantic
near-duplicates — the same question in different words — need an embedding pass
and are not handled. That gap is real and must be stated wherever a number
derived from this is reported, because the residual duplication is not zero.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Sequence

from .adapter import Invocation

_WS = re.compile(r"\s+")
_PUNCT_EDGE = re.compile(r"^[^\w]+|[^\w]+$")


def normalise(text: str) -> str:
    """Casefold, strip accents, collapse whitespace, trim edge punctuation.

    Deliberately conservative: it collapses formatting differences and nothing
    else. Anything more aggressive starts merging inputs that a system could
    legitimately answer differently, which would hide real behaviour rather than
    deduplicate noise.
    """
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c))
    t = t.casefold()
    t = _WS.sub(" ", t).strip()
    return _PUNCT_EDGE.sub("", t)


@dataclass
class DedupResult:
    kept: list[Invocation]
    groups: dict[str, list[str]]  # representative input_id -> all input_ids in group

    @property
    def n_removed(self) -> int:
        return sum(len(v) - 1 for v in self.groups.values())

    @property
    def duplication_rate(self) -> float:
        total = sum(len(v) for v in self.groups.values())
        return self.n_removed / total if total else 0.0


def dedup(invocations: Sequence[Invocation]) -> DedupResult:
    """Keep one invocation per normalised text, preserving first-seen order.

    The representative keeps its own input_id, and the group records everything
    it stands for — so a later report can say "this finding covers 47 requests",
    which is usually what the reader wants to know.
    """
    seen: dict[str, str] = {}
    groups: dict[str, list[str]] = {}
    kept: list[Invocation] = []
    for inv in invocations:
        key = normalise(inv.text)
        if key in seen:
            groups[seen[key]].append(inv.input_id)
            continue
        seen[key] = inv.input_id
        groups[inv.input_id] = [inv.input_id]
        kept.append(inv)
    return DedupResult(kept=kept, groups=groups)
