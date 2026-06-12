# lemora

Local-first Latin study dictionary CLI for translating words and short phrases with dictionary-grounded output.

## Features

- Offline-first CLI workflow
- Dictionary-first translation pipeline
- Planned adapters for Whitaker and Lewis & Short
- Optional CLTK sentence analysis and `llama-cpp-python` synthesis

## Installation

Base install:

```bash
uv sync --group dev
```

With CLTK:

```bash
uv sync --group dev --extra nlp
```

With local LLM support:

```bash
uv sync --group dev --extra llm
```

## Usage

Translate a word or phrase:

```bash
uv run lemora translate "arma virumque"
```

Request JSON output:

```bash
uv run lemora translate "amo" --format json
```

## Development

```bash
uv run ruff format .
uv run ruff check .
uv run pytest
```

## Current status

This repository is scaffolded for the first implementation phase:

- CLI entrypoint and command parsing
- Core data models
- Adapter interfaces for dictionary, NLP, and LLM integrations
- Service orchestration shell for dictionary-first translation

