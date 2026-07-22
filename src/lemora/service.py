"""Translation orchestration for lemora."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from lemora.models import TranslationResult

if TYPE_CHECKING:
    from lemora.adapters.base import DictionaryAdapter, SentenceAnalyzer, Synthesizer
    from lemora.models import DictionarySense, TokenAnalysis


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
        senses = tuple(self._lookup(normalized_query, token_analysis))
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

    def _lookup(self, normalized_query: str, token_analysis: tuple[TokenAnalysis, ...]) -> list[DictionarySense]:
        collected: list[DictionarySense] = []
        for lookup_query, confidence_adjustment in _lookup_variants(normalized_query, token_analysis):
            for adapter in self.dictionaries:
                collected.extend(
                    type(sense)(
                        lemma=sense.lemma,
                        gloss=sense.gloss,
                        source=sense.source,
                        confidence=_clamp_confidence(sense.confidence + confidence_adjustment),
                        morphology=sense.morphology,
                    )
                    for sense in adapter.lookup(lookup_query)
                )
        merged = _merge_senses(collected)
        return _rank_senses(merged)


def _normalize_query(query: str) -> str:
    normalized_tokens = [_normalize_token(token) for token in query.split()]
    return " ".join(token for token in normalized_tokens if token != "")


def _lookup_variants(
    normalized_query: str, token_analysis: tuple[TokenAnalysis, ...]
) -> tuple[tuple[str, float], ...]:
    variants: list[tuple[str, float]] = []
    variants.extend((variant, 0.0) for variant in _token_variants(normalized_query))
    variants.extend((variant, -0.08) for variant in _lemma_variants(token_analysis))

    # Preserve order while removing duplicates.
    seen: set[str] = set()
    ordered: list[tuple[str, float]] = []
    for variant, confidence_adjustment in variants:
        if variant in seen:
            continue
        seen.add(variant)
        ordered.append((variant, confidence_adjustment))
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


def _lemma_variants(token_analysis: tuple[TokenAnalysis, ...]) -> list[str]:
    variants: list[str] = []
    for token in token_analysis:
        variants.extend(token.lemma_candidates)
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


def _normalize_token(token: str) -> str:
    lowered = token.strip().lower()
    # Keep inner apostrophes/hyphens but drop leading/trailing punctuation and quotes.
    return re.sub(r"^[^\w]+|[^\w]+$", "", lowered)


def _clamp_confidence(confidence: float) -> float:
    return max(0.0, min(1.0, confidence))
