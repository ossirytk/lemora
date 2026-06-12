"""llama-cpp-python synthesis scaffold."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from lemora.models import DictionarySense


class LlamaSynthesizer:
    """Optional synthesis backend placeholder."""

    def __init__(self, model_path: Path | None) -> None:
        self._model_path = model_path

    def synthesize(self, query: str, senses: list[DictionarySense]) -> str | None:
        """Return concise, dictionary-grounded synthesis if model path is configured."""
        if self._model_path is None:
            return None
        if not senses:
            return f"No grounded synthesis available for: {query}"

        selected = _pick_phrase_senses(query, senses)
        phrase = "; ".join(f"{sense.lemma}: {_concise_gloss(sense.gloss)}" for sense in selected)
        sources = ", ".join(sorted({sense.source for sense in selected}))
        return f"{query} -> {phrase} (grounded in {sources})"


def _pick_phrase_senses(query: str, senses: list[DictionarySense]) -> list[DictionarySense]:
    token_order = [_normalize(token) for token in query.split() if token.strip() != ""]
    grouped = _group_by_lemma(senses)
    selected: list[DictionarySense] = []
    used_lemmas: set[str] = set()

    for token in token_order:
        if token not in grouped or token in used_lemmas:
            continue
        selected.append(_best_readable_sense(grouped[token]))
        used_lemmas.add(token)

    for lemma, lemma_senses in grouped.items():
        if lemma in used_lemmas:
            continue
        selected.append(_best_readable_sense(lemma_senses))

    max_terms = 4
    return selected[:max_terms]


def _group_by_lemma(senses: list[DictionarySense]) -> dict[str, list[DictionarySense]]:
    grouped: dict[str, list[DictionarySense]] = {}
    for sense in senses:
        grouped.setdefault(_normalize(sense.lemma), []).append(sense)
    return grouped


def _best_readable_sense(senses: list[DictionarySense]) -> DictionarySense:
    return max(senses, key=lambda sense: (_readability_score(sense.gloss), sense.confidence))


def _readability_score(gloss: str) -> float:
    cleaned = _normalize_space(gloss).lower()
    score = 0.0

    if re.search(r"\b(to|a|an|the|of|for|with|from)\b", cleaned):
        score += 2.0

    penalties = (
        (r"\b(ap|ib|cf|inscr|naev|plaut|cic|verg|lucil)\.", 0.8),
        (r"\d", 0.2),
    )
    for pattern, weight in penalties:
        score -= len(re.findall(pattern, cleaned)) * weight

    max_readable_len = 140
    if len(cleaned) > max_readable_len:
        score -= 1.0

    return score


def _concise_gloss(gloss: str) -> str:
    cleaned = _normalize_space(gloss)
    cleaned = cleaned.replace(" .", ".")
    split_pattern = r";|\s[—-]\s|(?<=\w)\.\s+(?=[A-Z])"
    fragments = [part.strip(" .,:;-") for part in re.split(split_pattern, cleaned) if part.strip() != ""]
    if not fragments:
        return cleaned

    best = max(fragments, key=_readability_score)
    best = re.sub(r"\s+", " ", best).strip(" .,:;-")
    max_gloss_length = 120
    return best[:max_gloss_length] if len(best) > max_gloss_length else best


def _normalize(text: str) -> str:
    return _normalize_space(text).lower()


def _normalize_space(text: str) -> str:
    return " ".join(text.split()).strip()
