"""Translation orchestration for lemora."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from lemora.grammar_reference import load_national_archives_grammar
from lemora.adapters.national_archives_reference import load_reference_form_index
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
            expected_pos = _expected_pos_for_variant(lookup_query, token_analysis)
            for adapter in self.dictionaries:
                collected.extend(
                    type(sense)(
                        lemma=sense.lemma,
                        gloss=sense.gloss,
                        source=sense.source,
                        confidence=_clamp_confidence(
                            sense.confidence + confidence_adjustment + _sense_pos_adjustment(sense, expected_pos),
                        ),
                        morphology=sense.morphology,
                    )
                    for sense in adapter.lookup(lookup_query)
                )
        merged = _merge_senses(collected)
        ranked = _rank_senses(merged)
        exact_phrase = _exact_phrase_senses(ranked, normalized_query)
        if exact_phrase:
            return exact_phrase
        return _cover_tokens(ranked, normalized_query, token_analysis)


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
    for token in tokens:
        reference_lemma = _reference_lemma_variant(token)
        if reference_lemma is not None:
            variants.append(reference_lemma)

    # Whitaker/L&S forms often appear without enclitic -que.
    variants.extend(
        token[: -len(enclitic)] for token in tokens if token.endswith(enclitic) and len(token) > len(enclitic)
    )
    for token in tokens:
        if token.endswith(enclitic) and len(token) > len(enclitic):
            variants.extend(_surface_stem_variants(token[: -len(enclitic)]))
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


def _cover_tokens(
    senses: list[DictionarySense],
    normalized_query: str,
    token_analysis: tuple[TokenAnalysis, ...],
) -> list[DictionarySense]:
    tokens = _token_profiles(normalized_query, token_analysis)
    if len(tokens) <= 1:
        return senses

    selected: list[DictionarySense] = []
    selected_keys: set[tuple[str, str]] = set()

    for variants in tokens:
        match = next(
            (
                sense
                for sense in senses
                if _normalize_query(sense.lemma) in variants
                and (_normalize_query(sense.lemma), _normalize_query(sense.gloss)) not in selected_keys
            ),
            None,
        )
        if match is None:
            match = next(
                (
                    sense
                    for sense in senses
                    if (_normalize_query(sense.lemma), _normalize_query(sense.gloss)) not in selected_keys
                ),
                None,
            )
        if match is None:
            continue
        key = (_normalize_query(match.lemma), _normalize_query(match.gloss))
        selected.append(match)
        selected_keys.add(key)

    if not selected:
        return senses[: len(tokens)]

    return selected


def _exact_phrase_senses(senses: list[DictionarySense], normalized_query: str) -> list[DictionarySense]:
    if " " not in normalized_query:
        return []
    exact_matches = [sense for sense in senses if _normalize_query(sense.lemma) == normalized_query]
    if not exact_matches:
        return []
    return exact_matches


def _token_profiles(normalized_query: str, token_analysis: tuple[TokenAnalysis, ...]) -> list[set[str]]:
    enclitic = "que"
    grammar = load_national_archives_grammar()

    source_tokens = (
        [token.token for token in token_analysis]
        if token_analysis
        else [token for token in normalized_query.split() if token != ""]
    )
    source_lemma_candidates = (
        [token.lemma_candidates for token in token_analysis]
        if token_analysis
        else [tuple() for _ in source_tokens]
    )

    profiles: list[set[str]] = []
    ref_index = load_reference_form_index()
    for token, lemma_candidates in zip(source_tokens, source_lemma_candidates, strict=False):
        variants = {_normalize_query(token)}
        variants.update(_normalize_query(candidate) for candidate in lemma_candidates)

        if token.endswith(enclitic) and len(token) > len(enclitic):
            token = token[: -len(enclitic)]
            variants.add(_normalize_query(token))
            variants.update(_surface_stem_variants(token))

        pronoun_mapped = grammar.pronoun_lemma_by_form.get(token)
        if pronoun_mapped is not None:
            variants.add(_normalize_query(pronoun_mapped))
        verb_mapped = grammar.verb_lemma_by_form.get(token)
        if verb_mapped is not None:
            variants.add(_normalize_query(verb_mapped))

        # Enrich variants with the lemma that the reference lexicon associates with
        # any surface form in this token's variant set (handles declined nouns,
        # conjugated verbs, etc., e.g. ``meridiem`` → ``meridies``).
        for v in list(variants):
            ref_lemma = ref_index.get(v)
            if ref_lemma is not None:
                variants.add(ref_lemma)

        profiles.append({variant for variant in variants if variant != ""})

    return profiles


def _surface_stem_variants(token: str) -> set[str]:
    lowered = _normalize_query(token)
    if lowered == "":
        return set()

    variants = {lowered}
    for suffix in ("orum", "arum", "ibus", "ium", "um", "am", "em", "as", "os", "es", "is", "ae", "i", "o", "u"):
        if lowered.endswith(suffix) and len(lowered) > len(suffix) + 1:
            variants.add(lowered[: -len(suffix)])
    return variants


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


def _reference_lemma_variant(token: str) -> str | None:
    grammar = load_national_archives_grammar()
    return grammar.pronoun_lemma_by_form.get(token) or grammar.verb_lemma_by_form.get(token)


def _expected_pos_for_variant(lookup_query: str, token_analysis: tuple[TokenAnalysis, ...]) -> set[str]:
    expected: set[str] = set()
    enclitic = "que"
    grammar = load_national_archives_grammar()
    for token in token_analysis:
        normalized_pos = _normalize_pos(token.pos)
        if normalized_pos is None:
            continue
        token_variants = set(token.lemma_candidates)
        token_variants.add(token.token)
        if token.token.endswith(enclitic) and len(token.token) > len(enclitic):
            token_variants.add(token.token[: -len(enclitic)])
        pronoun_mapped = grammar.pronoun_lemma_by_form.get(token.token)
        if pronoun_mapped is not None:
            token_variants.add(pronoun_mapped)
        verb_mapped = grammar.verb_lemma_by_form.get(token.token)
        is_reference_verb_query = False
        if verb_mapped is not None:
            token_variants.add(verb_mapped)
            if lookup_query == verb_mapped:
                is_reference_verb_query = True
                expected.add("verb")
        if lookup_query in token_variants and not is_reference_verb_query:
            expected.add(normalized_pos)
    return expected


def _sense_pos_adjustment(sense: DictionarySense, expected_pos: set[str]) -> float:
    if not expected_pos:
        return 0.0
    sense_pos = _infer_sense_pos(sense)
    if sense_pos is None:
        return 0.0
    return 0.04 if sense_pos in expected_pos else -0.08


def _infer_sense_pos(sense: DictionarySense) -> str | None:
    morphology = (sense.morphology or "").lower()
    if morphology == "":
        return None

    if "v." in morphology or "verb" in morphology:
        return "verb"
    if "adj" in morphology:
        return "adjective"
    if "adv" in morphology:
        return "adverb"
    if "prep" in morphology:
        return "preposition"
    if "pron" in morphology:
        return "pronoun"
    if "conj" in morphology:
        return "conjunction"
    if "noun" in morphology or "n." in morphology:
        return "noun"
    return None


def _normalize_pos(pos: str | None) -> str | None:
    if pos is None:
        return None
    mapping = {
        "verb": "verb",
        "aux": "verb",
        "noun": "noun",
        "propn": "noun",
        "adj": "adjective",
        "adv": "adverb",
        "adp": "preposition",
        "pron": "pronoun",
        "det": "pronoun",
        "cconj": "conjunction",
        "sconj": "conjunction",
        "conj": "conjunction",
    }
    return mapping.get(pos.lower())
