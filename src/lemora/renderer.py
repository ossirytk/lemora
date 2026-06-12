"""Rendering utilities for CLI output."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from rich.table import Table

if TYPE_CHECKING:
    from rich.console import Console

    from lemora.models import TranslationResult


def render_result(console: Console, result: TranslationResult, output_format: str) -> None:
    """Render translation result in requested format."""
    if output_format == "json":
        console.print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return

    if not result.senses:
        console.print(f"[yellow]No dictionary matches found for:[/yellow] {result.query}")
        return

    table = Table(title=f"lemora: {result.query}")
    table.add_column("Lemma")
    table.add_column("Gloss")
    table.add_column("Source")
    table.add_column("Confidence", justify="right")

    for sense in result.senses:
        table.add_row(sense.lemma, sense.gloss, sense.source, f"{sense.confidence:.2f}")

    console.print(table)
    if result.synthesis:
        console.print(f"\n[bold]Synthesis:[/bold] {result.synthesis}")
