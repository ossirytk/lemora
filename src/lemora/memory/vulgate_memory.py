"""Local JSON-backed memory index for Vulgate passages.

This is a minimal first step toward vector memory. It stores compact passage
records from the local Vulgate project and can later be replaced with actual
embedding/chroma persistence without changing the CLI surface.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(slots=True, frozen=True)
class MemoryRecord:
    """A single indexed passage."""

    source: str
    reference: str
    latin_text: str
    english_text: str


class VulgateMemoryIndex:
    """Persist and load Vulgate passage records."""

    def __init__(self, path: Path | None) -> None:
        self.path = path

    def ensure_parent_directory(self) -> None:
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> list[MemoryRecord]:
        if self.path is None or not self.path.exists():
            return []
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return [MemoryRecord(**item) for item in payload]

    def save(self, records: list[MemoryRecord]) -> None:
        if self.path is None:
            raise ValueError("Vulgate memory path is not configured")
        self.ensure_parent_directory()
        self.path.write_text(
            json.dumps([asdict(record) for record in records], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
