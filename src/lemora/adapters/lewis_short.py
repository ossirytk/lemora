"""Lewis & Short adapter for local lexical lookups."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lemora.adapters.local_lexicon import LexiconEntry, load_lexicon_entries
from lemora.models import DictionarySense

if TYPE_CHECKING:
    from pathlib import Path


class LewisShortAdapter:
    """Dictionary adapter backed by Lewis & Short-style local entries."""

    source_name = "Lewis & Short"

    def __init__(self, lexicon_path: Path | None = None) -> None:
        self._entries = load_lexicon_entries(lexicon_path, _DEFAULT_LEWIS_SHORT_ENTRIES)

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
                    confidence=entry.confidence_for_query(query, lemma_bonus=0.04),
                    morphology=entry.morphology,
                ),
            )
        return results


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
