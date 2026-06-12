"""Translation orchestration for lemora."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from lemora.models import TranslationResult

if TYPE_CHECKING:
    from lemora.adapters.base import DictionaryAdapter, SentenceAnalyzer, Synthesizer
    from lemora.models import DictionarySense


@dataclass(slots=True)
class LemoraService:
    """Application service for dictionary-first translation."""

    dictionaries: list[DictionaryAdapter]
    analyzer: SentenceAnalyzer | None = None
    synthesizer: Synthesizer | None = None

    def translate(self, query: str, *, synthesize: bool = False) -> TranslationResult:
        """Translate a query using dictionary adapters and optional synthesis."""
        normalized_query = _normalize_query(query)
        token_analysis = tuple(self.analyzer.analyze(normalized_query)) if self.analyzer is not None else ()
        senses = tuple(self._lookup(normalized_query))
        synthesis = None
        if synthesize and self.synthesizer is not None:
            synthesis = self.synthesizer.synthesize(normalized_query, list(senses))
        return TranslationResult(
            query=query,
            normalized_query=normalized_query,
            senses=senses,
            token_analysis=token_analysis,
            synthesis=synthesis,
        )

    def _lookup(self, normalized_query: str) -> list[DictionarySense]:
        collected: list[DictionarySense] = []
        for adapter in self.dictionaries:
            collected.extend(adapter.lookup(normalized_query))
        collected.sort(key=lambda sense: sense.confidence, reverse=True)
        return collected


def _normalize_query(query: str) -> str:
    return " ".join(query.split()).strip().lower()
