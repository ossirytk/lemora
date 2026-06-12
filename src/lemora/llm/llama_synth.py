"""llama-cpp-python synthesis scaffold."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from lemora.models import DictionarySense


class LlamaSynthesizer:
    """Optional synthesis backend placeholder."""

    def __init__(self, model_path: Path | None) -> None:
        self._model_path = model_path

    def synthesize(self, query: str, senses: list[DictionarySense]) -> str | None:
        """Return placeholder synthesis if model path is configured."""
        if self._model_path is None:
            return None
        if not senses:
            return f"No grounded synthesis available for: {query}"
        top_sense = senses[0]
        return f"{query} -> {top_sense.gloss} (grounded in {top_sense.source})"
