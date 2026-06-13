"""CLTK-based sentence analysis with graceful local fallback."""

from __future__ import annotations

import logging
from dataclasses import asdict
from importlib import import_module
from importlib.util import find_spec
from typing import TYPE_CHECKING

from lemora.models import TokenAnalysis

if TYPE_CHECKING:
    from cltk import NLP


class CltkAnalyzer:
    """Sentence analyzer using CLTK when available, with safe fallback behavior."""

    def __init__(self) -> None:
        self._pipeline: NLP | None = None
        self._pipeline_unavailable = False
        _configure_nlp_logging()

    def analyze(self, text: str) -> list[TokenAnalysis]:
        """Return token analyses with lemma candidates and optional CLTK metadata."""
        fallback_tokens = [token for token in text.split() if token != ""]
        pipeline = self._get_pipeline()
        if pipeline is None:
            return [_fallback_token_analysis(token) for token in fallback_tokens]

        try:
            doc = pipeline.analyze(text=text)
        except RuntimeError:
            self._pipeline_unavailable = True
            return [_fallback_token_analysis(token) for token in fallback_tokens]

        analyses: list[TokenAnalysis] = []
        for word in doc.words:
            token = _clean_token(getattr(word, "string", ""))
            if token == "":
                continue
            lemma = _clean_token(getattr(word, "lemma", ""))
            lemma_candidates = _dedupe_candidates((token, lemma, *_fallback_lemma_candidates(token)))
            pos = _clean_token(getattr(word, "upos", "")) or None
            features = _coerce_features(getattr(word, "features", None))
            analyses.append(
                TokenAnalysis(
                    token=token,
                    lemma_candidates=lemma_candidates,
                    pos=pos,
                    features=features,
                ),
            )

        return analyses or [_fallback_token_analysis(token) for token in fallback_tokens]

    def _get_pipeline(self) -> NLP | None:
        if self._pipeline_unavailable:
            return None
        if self._pipeline is not None:
            return self._pipeline

        nlp_class = _resolve_nlp_class()
        if nlp_class is None or not _has_stanza():
            self._pipeline_unavailable = True
            return None

        try:
            self._pipeline = nlp_class(language_code="lat", suppress_banner=True)
        except (ImportError, RuntimeError, ValueError):
            self._pipeline_unavailable = True
            return None
        return self._pipeline


def _fallback_token_analysis(token: str) -> TokenAnalysis:
    return TokenAnalysis(token=token, lemma_candidates=_dedupe_candidates((token, *_fallback_lemma_candidates(token))))


def _fallback_lemma_candidates(token: str) -> tuple[str, ...]:
    enclitic = "que"
    candidates = [token]
    if token.endswith(enclitic) and len(token) > len(enclitic):
        candidates.append(token[: -len(enclitic)])
    return tuple(candidates)


def _dedupe_candidates(candidates: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for candidate in candidates:
        normalized = _clean_token(candidate)
        if normalized == "" or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return tuple(ordered)


def _clean_token(token: object) -> str:
    if token is None:
        return ""

    if isinstance(token, str):
        raw = token
    else:
        tag_value = getattr(token, "tag", None)
        raw = tag_value if isinstance(tag_value, str) else str(token)

    return " ".join(raw.split()).strip().lower()


def _coerce_features(raw_features: object) -> dict[str, str]:
    if raw_features is None:
        return {}
    if isinstance(raw_features, dict):
        return {str(key): str(value) for key, value in raw_features.items()}

    model_dump = getattr(raw_features, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump()
        features = dumped.get("features")
        if isinstance(features, list):
            coerced: dict[str, str] = {}
            for feature in features:
                if not isinstance(feature, dict):
                    continue
                key = feature.get("key")
                value = feature.get("value_label") or feature.get("value")
                if isinstance(key, str) and isinstance(value, str):
                    coerced[key] = value
            if coerced:
                return coerced

    if hasattr(raw_features, "__dataclass_fields__"):
        return {str(key): str(value) for key, value in asdict(raw_features).items()}
    return {}


def _resolve_nlp_class() -> type[NLP] | None:
    try:
        cltk_module = import_module("cltk")
    except ImportError:
        return None
    nlp_candidate = getattr(cltk_module, "NLP", None)
    if nlp_candidate is None:
        return None
    return nlp_candidate


def _has_stanza() -> bool:
    return find_spec("stanza") is not None


def _configure_nlp_logging() -> None:
    logging.getLogger("stanza").setLevel(logging.ERROR)
    logging.getLogger("cltk").setLevel(logging.ERROR)
