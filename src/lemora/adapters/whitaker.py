"""Whitaker adapter for local lexical lookups."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lemora.adapters.local_lexicon import LexiconEntry, load_lexicon_entries
from lemora.models import DictionarySense

if TYPE_CHECKING:
    from pathlib import Path


class WhitakerAdapter:
    """Dictionary adapter backed by Whitaker-style local entries."""

    source_name = "Whitaker"

    def __init__(self, lexicon_path: Path | None = None) -> None:
        self._entries = load_lexicon_entries(lexicon_path, _DEFAULT_WHITAKER_ENTRIES)

    def lookup(self, query: str) -> list[DictionarySense]:
        """Return dictionary senses for query."""
        results: list[DictionarySense] = []
        for entry in self._entries:
            if not entry.matches(query):
                continue
            results.append(
                DictionarySense(
                    lemma=entry.lemma,
                    gloss=entry.gloss,
                    source=self.source_name,
                    confidence=entry.confidence_for_query(query, lemma_bonus=0.05),
                    morphology=entry.morphology,
                ),
            )
        return results


_DEFAULT_WHITAKER_ENTRIES: tuple[LexiconEntry, ...] = (
    LexiconEntry(
        lemma="amo",
        forms=("amas", "amat", "amare", "amavi", "amatum"),
        gloss="love; like",
        confidence=0.63,
        morphology="verb",
    ),
    LexiconEntry(
        lemma="vir",
        forms=("viri", "virum", "viro", "viros"),
        gloss="man; husband",
        confidence=0.61,
        morphology="noun masculine",
    ),
    LexiconEntry(
        lemma="arma",
        forms=("armorum", "armis"),
        gloss="arms; weapons",
        confidence=0.58,
        morphology="noun neuter plural",
    ),
)
