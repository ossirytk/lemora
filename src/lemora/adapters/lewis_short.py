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
        normalized_query = _normalize_lookup_key(query)
        return [
            DictionarySense(
                lemma=entry.lemma,
                gloss=entry.gloss,
                source=self.source_name,
                confidence=entry.confidence_for_query(query, lemma_bonus=0.04),
                morphology=entry.morphology,
            )
            for entry in self._index.get(normalized_query, [])
        ]


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
        morphology = _first_tag_text(body, "pos") or None
        gloss_source = sense_text if sense_text != "" else fallback_text
        gloss = _truncate_gloss(_prioritize_definition(gloss_source, lemma=lemma, morphology=morphology))
        if gloss == "":
            continue

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
        for lookup_key in {_normalize_lookup_key(entry.lemma), *(_normalize_lookup_key(form) for form in entry.forms)}:
            index.setdefault(lookup_key, []).append(entry)
    return index


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip().lower()


def _normalize_lookup_key(text: str) -> str:
    normalized = _normalize(text)
    return normalized.replace("j", "i")


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


def _prioritize_definition(text: str, *, lemma: str, morphology: str | None) -> str:
    cleaned = _clean_text(text)
    if cleaned == "":
        return ""

    anchor_positions: list[int] = []
    if _is_probably_verb(lemma=lemma, morphology=morphology):
        anchor_positions.extend(
            match.start()
            for match in re.finditer(r"\bto\s+(?!the\b|a\b|an\b)[a-z][a-z'-]+", cleaned, flags=re.IGNORECASE)
        )

    semantic_noun_pattern = r"\b(chance|luck|fate|fortune|memory|death|life|day|time)\b"
    anchor_positions.extend(
        match.start() for match in re.finditer(semantic_noun_pattern, cleaned, flags=re.IGNORECASE)
    )

    if not anchor_positions:
        return cleaned

    start = min(anchor_positions)
    prioritized = cleaned[start:].strip(" ,.;:-")
    return prioritized if prioritized != "" else cleaned


def _is_probably_verb(*, lemma: str, morphology: str | None) -> bool:
    if morphology is not None and re.search(r"\bv\.", morphology.lower()):
        return True
    normalized_lemma = _normalize_lookup_key(lemma)
    return normalized_lemma.endswith(("o", "or", "ri"))


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
