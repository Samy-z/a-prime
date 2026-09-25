"""Output normalisation.

Presentation differences are the largest avoidable source of false alarms in
the whole design. Rendering the same content as bullets instead of prose tripped
the NLI contradiction channel on 18.8% of meaning-preserving probe pairs and the
directional channel on 19% — and reformatting is among the most common side
effects of swapping a model, so those false alarms would land exactly when the
tool is most needed.

Normalisation runs before any scoring. It is the first stage of mode clustering
rather than a separate step, because the two want the same thing: strip what
carries no meaning, keep everything that does.

The line to hold: **remove presentation, never content.** Every transform here
must be one where a reader would say the two texts say the same thing. Anything
more aggressive starts erasing the differences the detector exists to find, and
that failure is invisible — it shows up as a clean report, not as an error.
"""

from __future__ import annotations

import json
import re
import unicodedata

_BULLET = re.compile(r"^\s*(?:[-*+•–—]|\d+[.)])\s+", re.MULTILINE)
_HEADING = re.compile(r"^\s*#{1,6}\s+", re.MULTILINE)
_EMPHASIS = re.compile(r"(\*\*|__|\*|_|`)")
_WS = re.compile(r"[ \t]+")
_BLANKLINES = re.compile(r"\n{2,}")
_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Straight/curly quote and dash equivalences. A model swap frequently changes
# these and nothing else.
_PUNCT_MAP = str.maketrans(
    {
        "‘": "'", "’": "'", "‚": "'", "‛": "'",
        "“": '"', "”": '"', "„": '"', "‟": '"',
        "–": "-", "—": "-", "−": "-",
        " ": " ", "…": "...",
    }
)


def normalise_text(text: str) -> str:
    """Canonical form of a free-text output.

    Strips markdown structure, list markers and emphasis; unifies quotes, dashes
    and whitespace; joins the result into single-spaced lines. Word content and
    word order are untouched.
    """
    t = unicodedata.normalize("NFKC", text)
    t = t.translate(_PUNCT_MAP)
    t = _HEADING.sub("", t)
    t = _BULLET.sub("", t)
    t = _EMPHASIS.sub("", t)
    t = _WS.sub(" ", t)
    t = _BLANKLINES.sub("\n", t)
    lines = [ln.strip() for ln in t.split("\n")]
    return "\n".join(ln for ln in lines if ln).strip()


def normalise_json(text: str) -> str | None:
    """Canonical form of a JSON output, or None if it does not parse.

    Keys are sorted and whitespace is fixed, so key ordering and indentation
    stop registering as changes. Returning None on a parse failure is
    deliberate: an output that stopped being valid JSON is a real regression
    (fault class F3), and silently falling back to text normalisation would hide
    it.
    """
    try:
        obj = json.loads(text)
    except (ValueError, TypeError):
        return None
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def normalise(text: str) -> str:
    """Normalise an output of unknown shape.

    JSON is detected and canonicalised structurally; anything else goes through
    text normalisation. A string that looks like JSON but does not parse falls
    through to text — the parse failure itself is caught by structural
    conformance, which is a different channel, not by silently repairing it here.
    """
    stripped = text.strip()
    if stripped[:1] in "{[":
        js = normalise_json(stripped)
        if js is not None:
            return js
    return normalise_text(text)


def as_sentences(text: str) -> list[str]:
    """Split normalised text into sentences.

    Used by clustering to compare content at a finer grain than the whole
    output, and by the omission channel, where the unit that goes missing is
    usually a sentence.
    """
    return [s.strip() for s in _SENT_SPLIT.split(normalise_text(text)) if s.strip()]


def is_probably_json(text: str) -> bool:
    return normalise_json(text.strip()) is not None
