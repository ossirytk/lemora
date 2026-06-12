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
        for lookup_query in _lookup_variants(normalized_query):
            for adapter in self.dictionaries:
                collected.extend(adapter.lookup(lookup_query))
        merged = _merge_senses(collected)
        return _rank_senses(merged)


def _normalize_query(query: str) -> str:
    return " ".join(query.split()).strip().lower()


def _lookup_variants(normalized_query: str) -> tuple[str, ...]:
    variants: list[str] = []
    variants.extend(_token_variants(normalized_query))

    # Preserve order while removing duplicates.
    seen: set[str] = set()
    ordered: list[str] = []
    for variant in variants:
        if variant in seen:
            continue
        seen.add(variant)
        ordered.append(variant)
    return tuple(ordered)


def _token_variants(normalized_query: str) -> list[str]:
    enclitic = "que"
    variants = [normalized_query]
    tokens = normalized_query.split()
    variants.extend(tokens)

    # Whitaker/L&S forms often appear without enclitic -que.
    variants.extend(
        token[: -len(enclitic)] for token in tokens if token.endswith(enclitic) and len(token) > len(enclitic)
    )
    return variants


def _merge_senses(senses: list[DictionarySense]) -> list[DictionarySense]:
    grouped: dict[tuple[str, str], list[DictionarySense]] = {}
    for sense in senses:
        key = (_normalize_query(sense.lemma), _normalize_query(sense.gloss))
        grouped.setdefault(key, []).append(sense)

    merged: list[DictionarySense] = []
    for group in grouped.values():
        first = group[0]
        sources = sorted(
            {sense.source for sense in group},
            key=_source_priority_key,
        )
        max_confidence = max(sense.confidence for sense in group)
        merged_confidence = min(1.0, max_confidence + (0.05 * (len(sources) - 1)))
        morphology = next((sense.morphology for sense in group if sense.morphology is not None), None)
        merged.append(
            type(first)(
                lemma=first.lemma,
                gloss=first.gloss,
                source=", ".join(sources),
                confidence=merged_confidence,
                morphology=morphology,
            ),
        )
    return merged


def _rank_senses(senses: list[DictionarySense]) -> list[DictionarySense]:
    return sorted(
        senses,
        key=lambda sense: (-_score_sense(sense), _normalize_query(sense.lemma), _normalize_query(sense.gloss)),
    )


def _score_sense(sense: DictionarySense) -> float:
    source_bonus = max((_source_bonus(source) for source in sense.source.split(", ")), default=0.0)
    morphology_bonus = 0.02 if sense.morphology is not None else 0.0
    return sense.confidence + source_bonus + morphology_bonus


def _source_priority_key(source: str) -> tuple[int, str]:
    return (_source_priority(source), source)


def _source_priority(source: str) -> int:
    priorities = {"Lewis & Short": 0, "Whitaker": 1}
    return priorities.get(source, 99)


def _source_bonus(source: str) -> float:
    bonuses = {"Lewis & Short": 0.06, "Whitaker": 0.03}
    return bonuses.get(source, 0.0)
