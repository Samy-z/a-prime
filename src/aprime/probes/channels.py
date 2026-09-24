"""Scoring channels under test.

A channel maps a pair of texts to a scalar where HIGHER MEANS MORE CHANGED.
That orientation is fixed across channels so the analysis never has to know
which direction a particular instrument points.

Model identity is resolved to a commit SHA at load time and reported back, not
assumed. The pinning rail in docs/methods/METHODS.md requires that a result
name the exact weights that produced it; a bare model name is not a pin,
because the hub contents behind a name can change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import numpy as np


@dataclass
class ModelSpec:
    """A model to probe. `prefix` covers families that require an instruction
    prefix to perform at their documented level (E5 in particular degrades
    noticeably without one)."""

    key: str
    hub_id: str
    kind: str  # "embedding" | "nli"
    prefix: str = ""
    revision: str | None = None  # resolved at load time


EMBEDDING_MODELS: list[ModelSpec] = [
    ModelSpec("minilm", "sentence-transformers/all-MiniLM-L6-v2", "embedding"),
    ModelSpec("bge_base", "BAAI/bge-base-en-v1.5", "embedding"),
    ModelSpec("e5_base", "intfloat/e5-base-v2", "embedding", prefix="query: "),
]

NLI_MODELS: list[ModelSpec] = [
    ModelSpec("deberta_mnli", "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli", "nli"),
    # Second checkpoint, different family (RoBERTa, not DeBERTa). The embedding
    # finding replicates across three families and is therefore a statement
    # about embeddings; the NLI finding rested on one checkpoint and was
    # therefore only a statement about that checkpoint. This closes the gap.
    ModelSpec("roberta_mnli", "FacebookAI/roberta-large-mnli", "nli"),
]


def _resolve_revision(hub_id: str) -> str | None:
    """Best-effort resolution of the cached commit SHA, for the pin record."""
    try:
        from huggingface_hub import HfApi

        return HfApi().model_info(hub_id).sha
    except Exception:
        return None


@dataclass
class ChannelResult:
    channel: str
    model_key: str
    hub_id: str
    revision: str | None
    scores: np.ndarray
    meta: dict = field(default_factory=dict)


class EmbeddingChannel:
    """1 - cosine similarity between the two arms.

    This is the instrument the design leans on for triage. The probe suite
    exists largely to find out where it is blind; see docs/engine/METHODS.md.
    """

    def __init__(self, spec: ModelSpec, device: str | None = None):
        from sentence_transformers import SentenceTransformer

        self.spec = spec
        self.model = SentenceTransformer(spec.hub_id, device=device)
        self.revision = _resolve_revision(spec.hub_id)

    def score(self, texts_a: Sequence[str], texts_b: Sequence[str]) -> np.ndarray:
        p = self.spec.prefix
        a = self.model.encode(
            [p + t for t in texts_a],
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
        b = self.model.encode(
            [p + t for t in texts_b],
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
        cos = np.sum(np.asarray(a) * np.asarray(b), axis=1)
        return 1.0 - cos


class NLIChannel:
    """Bidirectional contradiction probability.

    Run in both directions and take the maximum: entailment is asymmetric, and
    a dropped caveat contradicts in one direction only. Taking the max is the
    conservative choice for a detector whose job is to notice.
    """

    def __init__(self, spec: ModelSpec, device: str | None = None):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.spec = spec
        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.tok = AutoTokenizer.from_pretrained(spec.hub_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(spec.hub_id)
        self.model.to(self.device).eval()
        self.revision = _resolve_revision(spec.hub_id)

        # Never hardcode the label order. Several MNLI checkpoints in common use
        # disagree on it, and a silent off-by-one here would look exactly like
        # the channel being uninformative.
        id2label = {int(k): v.lower() for k, v in self.model.config.id2label.items()}
        self.contra_idx = self._one(id2label, "contradiction", spec.hub_id)
        self.entail_idx = self._one(id2label, "entail", spec.hub_id)

    @staticmethod
    def _one(id2label: dict[int, str], needle: str, hub_id: str) -> int:
        matches = [i for i, lab in id2label.items() if needle in lab]
        if len(matches) != 1:
            raise RuntimeError(
                f"cannot identify '{needle}' label in {id2label} for {hub_id}"
            )
        return matches[0]

    def _probs(self, prem: Sequence[str], hyp: Sequence[str]) -> np.ndarray:
        """Full 3-class probabilities, shape (n, 3)."""
        out = []
        bs = 16
        for i in range(0, len(prem), bs):
            enc = self.tok(
                list(prem[i : i + bs]),
                list(hyp[i : i + bs]),
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True,
            ).to(self.device)
            with self.torch.no_grad():
                logits = self.model(**enc).logits
            probs = self.torch.softmax(logits, dim=-1)
            out.append(probs.cpu().numpy())
        return np.concatenate(out)

    def score_both(
        self, texts_a: Sequence[str], texts_b: Sequence[str]
    ) -> dict[str, np.ndarray]:
        """Both channels from a single pair of forward passes.

        `contradiction` — max over directions. Symmetric by construction, which
        is why it cannot speak to direction of change (MTH-001).

        `directional` — how much more A entails B than B entails A. This is
        **asymmetric**, and it is the signal for information *loss*: a text with
        a condition removed is entailed by the original while the original is
        not entailed by it. That is precisely the omission case that
        contradiction is blind to by definition (MTH-014).

        Note what it does and does not give. It detects that information moved
        in a direction, not whether that is better or worse — dropping a caveat
        and dropping waffle look identical here. But it is the first
        meaning-sensitive asymmetric feature the design has had, so it is a
        candidate against MTH-001's reopen clause rather than a resolution of it.
        """
        fwd = self._probs(texts_a, texts_b)
        rev = self._probs(texts_b, texts_a)
        return {
            "contradiction": np.maximum(fwd[:, self.contra_idx], rev[:, self.contra_idx]),
            "directional": fwd[:, self.entail_idx] - rev[:, self.entail_idx],
            "directional_abs": np.abs(fwd[:, self.entail_idx] - rev[:, self.entail_idx]),
        }

    def score(self, texts_a: Sequence[str], texts_b: Sequence[str]) -> np.ndarray:
        return self.score_both(texts_a, texts_b)["contradiction"]
