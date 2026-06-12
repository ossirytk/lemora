"""Lewis & Short adapter scaffold."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lemora.models import DictionarySense


class LewisShortAdapter:
    """Dictionary adapter placeholder for Lewis & Short."""

    source_name = "Lewis & Short"

    def lookup(self, query: str) -> list[DictionarySense]:
        """Return dictionary senses for query."""
        _ = query
        return []
