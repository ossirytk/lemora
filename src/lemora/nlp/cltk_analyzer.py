"""CLTK-based sentence analysis scaffold."""

from __future__ import annotations

from lemora.models import TokenAnalysis


class CltkAnalyzer:
    """Sentence analyzer that currently provides a safe fallback."""

    def analyze(self, text: str) -> list[TokenAnalysis]:
        """Return basic token analysis until CLTK pipeline is wired."""
        tokens = [token for token in text.split() if token]
        return [TokenAnalysis(token=token) for token in tokens]
