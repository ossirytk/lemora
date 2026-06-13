"""Rendering utilities for CLI output."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rich.table import Table

from lemora.gloss import concise_gloss, readability_score

if TYPE_CHECKING:
    from rich.console import Console

    from lemora.models import DictionarySense, TranslationResult


def render_result(console: Console, result: TranslationResult, output_format: str) -> None:
    """Render translation result in requested format."""
    if output_format == "json":
        console.print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return

    if not result.senses:
        console.print(f"[yellow]No dictionary matches found for:[/yellow] {result.query}")
        return

    display_senses = _display_senses(result.senses)

    table = Table(title=f"lemora: {result.query}")
    table.add_column("Lemma")
    table.add_column("Gloss")
    table.add_column("Source")
    table.add_column("Confidence", justify="right")

    for sense, duplicate_count in display_senses:
        lemma_label = sense.lemma if duplicate_count == 1 else f"{sense.lemma} ({duplicate_count})"
        table.add_row(
            lemma_label,
            concise_gloss(sense.gloss, max_length=96),
            sense.source,
            f"{sense.confidence:.2f}",
        )

    console.print(table)
    if result.synthesis:
        console.print(f"\n[bold]Synthesis:[/bold] {result.synthesis}")


def _display_senses(senses: tuple[DictionarySense, ...]) -> list[tuple[DictionarySense, int]]:
    grouped: dict[str, list[DictionarySense]] = {}
    for sense in senses:
        grouped.setdefault(_normalize(sense.lemma), []).append(sense)

    collapsed: list[tuple[DictionarySense, int]] = []
    for group in grouped.values():
        best_sense = max(group, key=lambda sense: (readability_score(sense.gloss), sense.confidence))
        collapsed.append((best_sense, len(group)))

    return sorted(
        collapsed,
        key=lambda item: (-item[0].confidence, _normalize(item[0].lemma), _normalize(item[0].gloss)),
    )


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip().lower()
