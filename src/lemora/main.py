"""Entrypoint module for lemora."""

from __future__ import annotations

from lemora.cli import run


def main() -> int:
    """Run lemora CLI."""
    return run()
