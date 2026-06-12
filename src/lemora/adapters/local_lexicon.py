"""Utilities for file-backed and built-in local lexicon entries."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(slots=True, frozen=True)
class LexiconEntry:
    """Single normalized lexicon record."""

    lemma: str
    gloss: str
    forms: tuple[str, ...] = ()
    confidence: float = 0.5
    morphology: str | None = None

    def matches(self, query: str) -> bool:
        """Return whether the query matches the lemma or any known form."""
        normalized_query = _normalize(query)
        return normalized_query == _normalize(self.lemma) or normalized_query in {
            _normalize(form) for form in self.forms
        }

    def confidence_for_query(self, query: str, *, lemma_bonus: float = 0.0) -> float:
        """Return confidence for a query with optional exact-lemma bonus."""
        normalized_query = _normalize(query)
        base_confidence = self.confidence
        if normalized_query == _normalize(self.lemma):
            base_confidence += lemma_bonus
        return _clamp_confidence(base_confidence)


def load_lexicon_entries(
    asset_path: Path | None, fallback_entries: tuple[LexiconEntry, ...]
) -> tuple[LexiconEntry, ...]:
    """Load lexicon entries from JSON, or fallback to built-ins when not configured."""
    if asset_path is None:
        return fallback_entries
    raw_payload = json.loads(asset_path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, list):
        msg = f"Expected list payload in lexicon JSON at {asset_path}"
        raise TypeError(msg)
    return tuple(_parse_entry(item) for item in raw_payload)


def _parse_entry(item: object) -> LexiconEntry:
    if not isinstance(item, dict):
        msg = "Each lexicon entry must be an object."
        raise TypeError(msg)

    lemma = item.get("lemma")
    gloss = item.get("gloss")
    if not isinstance(lemma, str) or lemma.strip() == "":
        msg = "Lexicon entry requires a non-empty 'lemma' string."
        raise ValueError(msg)
    if not isinstance(gloss, str) or gloss.strip() == "":
        msg = "Lexicon entry requires a non-empty 'gloss' string."
        raise ValueError(msg)

    forms_raw = item.get("forms", [])
    if not isinstance(forms_raw, list) or any(not isinstance(form, str) for form in forms_raw):
        msg = "Lexicon entry 'forms' must be a list of strings."
        raise ValueError(msg)

    confidence = item.get("confidence", 0.5)
    if not isinstance(confidence, int | float):
        msg = "Lexicon entry 'confidence' must be numeric."
        raise TypeError(msg)

    morphology = item.get("morphology")
    if morphology is not None and not isinstance(morphology, str):
        msg = "Lexicon entry 'morphology' must be a string when present."
        raise ValueError(msg)

    return LexiconEntry(
        lemma=lemma.strip(),
        gloss=gloss.strip(),
        forms=tuple(form.strip() for form in forms_raw if form.strip()),
        confidence=_clamp_confidence(float(confidence)),
        morphology=morphology.strip() if isinstance(morphology, str) and morphology.strip() else None,
    )


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip().lower()


def _clamp_confidence(confidence: float) -> float:
    return max(0.0, min(1.0, confidence))
