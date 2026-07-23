"""Bundled National Archives stage Latin reference lexicon."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import TYPE_CHECKING

from lemora.adapters.local_lexicon import LexiconEntry
from lemora.models import DictionarySense

if TYPE_CHECKING:
    from pathlib import Path


class NationalArchivesReferenceAdapter:
    """Dictionary adapter backed by bundled stage Latin reference entries."""

    source_name = "National Archives"

    def __init__(self, lexicon_path: Path | None = None) -> None:
        self._entries = _load_entries(lexicon_path)
        self._index = _build_query_index(self._entries)

    def lookup(self, query: str) -> list[DictionarySense]:
        normalized_query = _normalize_lookup_key(query)
        return [
            DictionarySense(
                lemma=entry.lemma,
                gloss=entry.gloss,
                source=self.source_name,
                confidence=entry.confidence_for_query(query, lemma_bonus=0.03),
                morphology=entry.morphology,
            )
            for entry in self._index.get(normalized_query, [])
        ]


def _load_entries(lexicon_path: Path | None) -> tuple[LexiconEntry, ...]:
    if lexicon_path is None:
        resource_path = files("lemora.resources").joinpath("national_archives_reference_lexicon.json")
        payload = json.loads(resource_path.read_text(encoding="utf-8"))
    else:
        payload = json.loads(lexicon_path.read_text(encoding="utf-8"))
    return tuple(_parse_entry(item) for item in payload)


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
        confidence=max(0.0, min(1.0, float(confidence))),
        morphology=morphology.strip() if isinstance(morphology, str) and morphology.strip() else None,
    )


def _build_query_index(entries: tuple[LexiconEntry, ...]) -> dict[str, list[LexiconEntry]]:
    index: dict[str, list[LexiconEntry]] = {}
    for entry in entries:
        for lookup_key in {_normalize_lookup_key(entry.lemma), *(_normalize_lookup_key(form) for form in entry.forms)}:
            index.setdefault(lookup_key, []).append(entry)
    return index


def _normalize_lookup_key(text: str) -> str:
    return " ".join(text.split()).strip().lower().replace("j", "i")

