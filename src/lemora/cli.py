"""Command-line interface for lemora."""

from __future__ import annotations

import argparse
from typing import TYPE_CHECKING

from rich.console import Console

from lemora.adapters.lewis_short import LewisShortAdapter
from lemora.adapters.whitaker import WhitakerAdapter
from lemora.config import LemoraConfig
from lemora.llm.llama_synth import LlamaSynthesizer
from lemora.nlp.cltk_analyzer import CltkAnalyzer
from lemora.renderer import render_result
from lemora.service import LemoraService

if TYPE_CHECKING:
    from collections.abc import Sequence


def build_parser() -> argparse.ArgumentParser:
    """Build CLI parser."""
    parser = argparse.ArgumentParser(prog="lemora", description="Local-first Latin dictionary CLI.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    translate_parser = subparsers.add_parser("translate", help="Translate a Latin word or phrase.")
    translate_parser.add_argument("query", help="Word or phrase to translate.")
    translate_parser.add_argument(
        "--format",
        dest="output_format",
        choices=("plain", "json"),
        default="plain",
        help="Output format.",
    )
    translate_parser.add_argument(
        "--synthesize",
        action="store_true",
        help="Enable optional synthesis via configured local model backend.",
    )
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    """Execute lemora CLI."""
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command != "translate":
        parser.print_help()
        return 1

    config = LemoraConfig.from_env()
    service = LemoraService(
        dictionaries=[
            WhitakerAdapter(config.whitaker_path),
            LewisShortAdapter(config.lewis_short_path),
        ],
        analyzer=CltkAnalyzer(),
        synthesizer=LlamaSynthesizer(config.model_path),
    )
    result = service.translate(query=args.query, synthesize=args.synthesize)

    console = Console()
    render_result(console=console, result=result, output_format=args.output_format)
    return 0
