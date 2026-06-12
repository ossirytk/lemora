"""Protocols for pluggable backend adapters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from lemora.models import DictionarySense, TokenAnalysis


class DictionaryAdapter(Protocol):
    """Dictionary lookup contract."""

    source_name: str

    def lookup(self, query: str) -> list[DictionarySense]:
        """Return candidate senses for a query."""


class SentenceAnalyzer(Protocol):
    """Sentence-level linguistic analysis contract."""

    def analyze(self, text: str) -> list[TokenAnalysis]:
        """Return token analyses."""


class Synthesizer(Protocol):
    """Optional response synthesis contract."""

    def synthesize(self, query: str, senses: list[DictionarySense]) -> str | None:
        """Return an optional synthesized explanation or translation."""
