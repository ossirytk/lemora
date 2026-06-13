"""llama-cpp-python synthesis scaffold."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lemora.gloss import concise_gloss, normalize_space, readability_score

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
        phrase = "; ".join(_component_line(index, sense) for index, sense in enumerate(selected))
        sources = ", ".join(sorted({sense.source for sense in selected}))
        return f"{query} -> components: {phrase} (grounded in {sources})"


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
    return max(senses, key=lambda sense: (readability_score(sense.gloss), sense.confidence))


def _component_line(index: int, sense: DictionarySense) -> str:
    gloss = concise_gloss(sense.gloss, max_length=120)
    role = _infer_role(index, gloss)
    return f"{role}: {sense.lemma} = {gloss}"


def _infer_role(index: int, gloss: str) -> str:
    normalized = normalize_space(gloss).lower()
    if normalized.startswith("dative/ablative of "):
        return "addressee"
    if normalized.startswith(("dative/", "ablative/", "genitive/", "nominative/", "accusative/", "vocative/")):
        return "case form"
    if normalized.startswith(("to ", "imperative of ", "infinitive")):
        return "verb"
    if "accusative of " in normalized:
        return "direct object"
    return "term" if index > 0 else "head term"


def _normalize(text: str) -> str:
    return normalize_space(text).lower()
