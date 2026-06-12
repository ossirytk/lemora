"""Whitaker adapter scaffold."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lemora.models import DictionarySense


class WhitakerAdapter:
    """Dictionary adapter placeholder for Whitaker's Words."""

    source_name = "Whitaker"

    def lookup(self, query: str) -> list[DictionarySense]:
        """Return dictionary senses for query."""
        _ = query
        return []
