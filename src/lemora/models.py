"""Core domain models for lemora."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(slots=True, frozen=True)
class DictionarySense:
    """Single dictionary entry candidate."""

    lemma: str
    gloss: str
    source: str
    confidence: float = 0.5
    morphology: str | None = None


@dataclass(slots=True, frozen=True)
class TokenAnalysis:
    """Token-level linguistic analysis result."""

    token: str
    lemma_candidates: tuple[str, ...] = ()
    pos: str | None = None
    features: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class TranslationResult:
    """Assembled translation output for a query."""

    query: str
    normalized_query: str
    senses: tuple[DictionarySense, ...]
    token_analysis: tuple[TokenAnalysis, ...] = ()
    synthesis: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""
        return asdict(self)
