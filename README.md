# lemora

Local-first Latin study dictionary CLI for translating words and short phrases with dictionary-grounded output.

## Features

- Offline-first CLI workflow
- Dictionary-first translation pipeline
- Whitaker and Lewis & Short adapters with local JSON override support
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

For full CLTK parsing, download Latin Stanza assets once:

```bash
uv run python -c "import stanza; stanza.download('la')"
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

Optional lexicon overrides:

```bash
export LEMORA_WHITAKER_PATH=/path/to/whitaker.json
export LEMORA_LEWIS_SHORT_PATH=/path/to/lewis_short.json
```

- Whitaker override expects JSON array entries with `lemma`, `gloss`, and optional `forms`, `confidence`, `morphology`.
- Lewis & Short override accepts the same JSON format **or** Perseus `lat.ls.perseus-eng*.xml` TEI files.

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
