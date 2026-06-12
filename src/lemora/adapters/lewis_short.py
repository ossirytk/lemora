"""Lewis & Short adapter for local lexical lookups."""

from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING

from lemora.adapters.local_lexicon import LexiconEntry, load_lexicon_entries
from lemora.models import DictionarySense

if TYPE_CHECKING:
    from pathlib import Path


class LewisShortAdapter:
    """Dictionary adapter backed by Lewis & Short-style local entries."""

    source_name = "Lewis & Short"

    def __init__(self, lexicon_path: Path | None = None) -> None:
        self._entries = _load_entries(lexicon_path)
        self._index = _build_query_index(self._entries)

    def lookup(self, query: str) -> list[DictionarySense]:
        """Return dictionary senses for query."""
        normalized_query = _normalize(query)
        results: list[DictionarySense] = []
        for entry in self._index.get(normalized_query, []):
            if not entry.matches(normalized_query):
                continue
            results.append(
                DictionarySense(
                    lemma=entry.lemma,
                    gloss=entry.gloss,
                    source=self.source_name,
                    confidence=entry.confidence_for_query(query, lemma_bonus=0.04),
                    morphology=entry.morphology,
                ),
            )
        return results


def _load_entries(lexicon_path: Path | None) -> tuple[LexiconEntry, ...]:
    if lexicon_path is None:
        return _DEFAULT_LEWIS_SHORT_ENTRIES
    if lexicon_path.suffix.lower() == ".xml":
        return _load_perseus_xml_entries(lexicon_path)
    return load_lexicon_entries(lexicon_path, _DEFAULT_LEWIS_SHORT_ENTRIES)


def _load_perseus_xml_entries(lexicon_path: Path) -> tuple[LexiconEntry, ...]:
    entries: list[LexiconEntry] = []
    content = lexicon_path.read_text(encoding="utf-8")
    for match in _ENTRY_PATTERN.finditer(content):
        key = match.group("key").strip()
        lemma = _normalize_entry_key(key)
        body = match.group("body")
        if lemma == "":
            continue

        sense_text = _first_tag_text(body, "sense")
        fallback_text = _strip_markup(body)
        gloss = _truncate_gloss(sense_text if sense_text != "" else fallback_text)
        if gloss == "":
            continue

        morphology = _first_tag_text(body, "pos") or None
        entries.append(
            LexiconEntry(
                lemma=lemma,
                forms=(key,),
                gloss=gloss,
                confidence=0.79,
                morphology=morphology,
            ),
        )
    return tuple(entries)


def _first_tag_text(body: str, tag_name: str) -> str:
    tag_pattern = re.compile(rf"<{tag_name}\b[^>]*>(?P<content>.*?)</{tag_name}>", flags=re.DOTALL)
    match = tag_pattern.search(body)
    if match is not None:
        return _strip_markup(match.group("content"))
    return ""


def _build_query_index(entries: tuple[LexiconEntry, ...]) -> dict[str, list[LexiconEntry]]:
    index: dict[str, list[LexiconEntry]] = {}
    for entry in entries:
        for lookup_key in {_normalize(entry.lemma), *(_normalize(form) for form in entry.forms)}:
            index.setdefault(lookup_key, []).append(entry)
    return index


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip().lower()


def _clean_text(text: str) -> str:
    return " ".join(text.split()).strip()


def _normalize_entry_key(key: str) -> str:
    return re.sub(r"\d+$", "", key).strip()


def _strip_markup(text: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", text)
    return _clean_text(html.unescape(without_tags))


def _truncate_gloss(text: str) -> str:
    cleaned = _clean_text(text)
    max_gloss_length = 220
    if len(cleaned) <= max_gloss_length:
        return cleaned
    return f"{cleaned[:max_gloss_length].rstrip()}..."


_ENTRY_PATTERN = re.compile(
    r"<entryFree\b[^>]*\bkey=\"(?P<key>[^\"]+)\"[^>]*>(?P<body>.*?)</entryFree>",
    flags=re.DOTALL,
)


_DEFAULT_LEWIS_SHORT_ENTRIES: tuple[LexiconEntry, ...] = (
    LexiconEntry(
        lemma="amo",
        forms=("amare", "amavi", "amatum"),
        gloss="to love, be fond of",
        confidence=0.78,
        morphology="verb",
    ),
    LexiconEntry(
        lemma="vir",
        forms=("viri", "virum"),
        gloss="a man; husband",
        confidence=0.75,
        morphology="noun masculine",
    ),
    LexiconEntry(
        lemma="bellum",
        forms=("belli", "bello", "bella"),
        gloss="war",
        confidence=0.77,
        morphology="noun neuter",
    ),
)
