"""Parse Meissner's Latin Phrase-Book into reference lexicon phrase entries.

Each entry is a Latin phrase (possibly multi-word) with an English gloss,
sourced from 'Latin Phrase-Book' by Carl Meissner (Project Gutenberg).

Usage:
    uv run python scripts/parse_meissner.py > /tmp/meissner_entries.json
    uv run python scripts/parse_meissner.py --merge   # merge into lexicon
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


PHRASE_BOOK_TXT = Path(__file__).parent.parent / "resources" / "latin_phrase_book.txt"
LEXICON_JSON = (
    Path(__file__).parent.parent
    / "src" / "lemora" / "resources" / "national_archives_reference_lexicon.json"
)

# Slightly higher than Döderlein (0.82) since these are complete phrases with
# verified English glosses — but still lower than hand-curated (0.98).
MEISSNER_CONFIDENCE = 0.84

# Em-dash or en-dash separating Latin from English
_DASH_RE = re.compile(r"[—–]")


def main() -> None:
    merge_mode = "--merge" in sys.argv

    text = PHRASE_BOOK_TXT.read_text(encoding="utf-8").replace("\r\n", "\n")
    entries = list(_parse_entries(text))
    print(f"Parsed {len(entries)} entries from Meissner.", file=sys.stderr)

    if merge_mode:
        _merge_into_lexicon(entries)
    else:
        json.dump(entries, sys.stdout, indent=2, ensure_ascii=False)


def _parse_entries(text: str) -> list[dict]:
    """Extract all _Latin phrase_—English gloss pairs from the body text."""
    # Skip the Gutenberg header and table of contents; body begins at the first
    # section that contains phrase entries (after the second occurrence of
    # the section title "1. The World").
    toc_end = text.find("1. The World")
    body_start = text.find("1. The World", toc_end + 100)
    end_marker = "*** END OF THE PROJECT GUTENBERG"
    body_end = text.find(end_marker)
    if body_start == -1:
        body_start = 0
    if body_end == -1:
        body_end = len(text)
    body = text[body_start:body_end]

    # Join wrapped lines: a line that ends without sentence punctuation and
    # the next line is a continuation of an entry.  We detect entry lines as
    # starting with `_` and join lines that are clearly continuations.
    # Simpler: just scan all lines for the italic+dash pattern, handling
    # multi-line entries by pre-joining them.
    joined_lines = _join_wrapped_lines(body.splitlines())

    entries: list[dict] = []
    seen_lemmas: set[str] = set()

    for line in joined_lines:
        line = line.strip()
        if not line:
            continue
        # Footnote lines like "[1] ..." — skip
        if re.match(r"^\[\d+\]", line):
            continue
        # Must contain a Latin phrase in _italics_ followed by a dash
        if not line.startswith("_"):
            continue

        # Split on the em/en dash to get Latin and English parts
        dash_match = _DASH_RE.search(line)
        if not dash_match:
            continue
        before_dash = line[: dash_match.start()]
        after_dash = line[dash_match.end() :].strip()

        # Strip negation/alternate forms: everything from "(not" or "or"
        before_paren = re.split(r"\s+\(not\b|\s+or\b", before_dash)[0]
        # Take only the first italic span as the primary phrase
        first_span = re.match(r"^_([^_]+)_", before_paren.strip())
        if not first_span:
            continue
        latin_phrase = first_span.group(1).strip()

        gloss = _clean_gloss(after_dash)
        if not gloss or len(gloss) < 3:
            continue

        lemma = latin_phrase.lower()
        if lemma in seen_lemmas:
            continue
        seen_lemmas.add(lemma)

        entries.append({
            "lemma": lemma,
            "forms": [lemma],
            "gloss": gloss,
            "confidence": MEISSNER_CONFIDENCE,
            "morphology": "phrase",
        })

    return entries


def _join_wrapped_lines(lines: list[str]) -> list[str]:
    """Join lines that are continuations of a multi-line entry."""
    result: list[str] = []
    pending = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if pending:
                result.append(pending)
                pending = ""
            continue
        # A new entry starts with `_`.
        # Continuations: lines that start with `_word_)` (closing a parenthetical
        # from the previous line) are NOT new entries.
        is_continuation = bool(re.match(r"^_[^_]+_[\)\]]", stripped))
        is_new_entry = (
            stripped.startswith("_") and not is_continuation
        ) or bool(re.match(r"^\[\d+\]", stripped))
        if is_new_entry:
            if pending:
                result.append(pending)
            pending = stripped
        elif pending:
            pending = pending.rstrip() + " " + stripped
        else:
            result.append(stripped)
    if pending:
        result.append(pending)
    return result


def _clean_gloss(raw: str) -> str:
    """Clean up the English gloss text."""
    # Strip italic/bold markers
    cleaned = re.sub(r"_([^_]+)_", r"\1", raw)
    cleaned = re.sub(r"\+([^+]+)\+", r"\1", cleaned)
    # Strip footnote markers
    cleaned = re.sub(r"\[\d+\]", "", cleaned)
    # Strip trailing citation refs like "(Fin. 1.2)"
    cleaned = re.sub(r"\s*\([A-Z][a-z]+\..*?\)\s*$", "", cleaned)
    # Normalise whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(".,;:")
    return cleaned[:140]


def _merge_into_lexicon(entries: list[dict]) -> None:
    existing = json.loads(LEXICON_JSON.read_text(encoding="utf-8"))
    existing_lemmas = {e["lemma"] for e in existing}
    new_entries = [e for e in entries if e["lemma"] not in existing_lemmas]
    merged = existing + new_entries
    LEXICON_JSON.write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Added {len(new_entries)} new entries. Total: {len(merged)}.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
