"""Parse Döderlein's Hand-book of Latin Synonymes into reference lexicon entries.

Produces a JSON list of {lemma, gloss, forms, confidence, morphology} records
that can be merged into the bundled reference lexicon.

Usage:
    uv run python scripts/parse_doederlein.py > /tmp/doederlein_entries.json
    uv run python scripts/parse_doederlein.py --merge   # merge directly into lexicon
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


SYNONYMES_TXT = Path(__file__).parent.parent / "resources" / "synonymes.txt"
LEXICON_JSON = (
    Path(__file__).parent.parent
    / "src" / "lemora" / "resources" / "national_archives_reference_lexicon.json"
)
BODY_START_MARKER = "A.\n\nABDERE"   # First actual entry after the header
BODY_END_MARKER = "INDEX OF GREEK WORDS"

# Confidence for Döderlein entries — lower than hand-curated (0.98) so our
# bundled entries keep priority, but high enough to beat noisy L&S raw glosses.
DOEDERLEIN_CONFIDENCE = 0.82


def main() -> None:
    merge_mode = "--merge" in sys.argv

    text = SYNONYMES_TXT.read_text(encoding="utf-8").replace("\r\n", "\n")
    entries = list(_parse_entries(text))
    print(f"Parsed {len(entries)} entries from Döderlein.", file=sys.stderr)

    if merge_mode:
        _merge_into_lexicon(entries)
    else:
        json.dump(entries, sys.stdout, indent=2, ensure_ascii=False)


def _parse_entries(text: str) -> list[dict]:
    """Parse all synonym group entries from the full text."""
    # Isolate the dictionary body
    start = text.find(BODY_START_MARKER)
    if start == -1:
        start = 0
    # Find end marker *after* start to skip TOC occurrence
    end = text.upper().find(BODY_END_MARKER.upper(), start)
    if end == -1:
        end = len(text)
    body = text[start:end]

    # Split on blank lines to get paragraphs
    paragraphs = re.split(r"\n{2,}", body)

    entries: list[dict] = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        lines = para.splitlines()
        first_line = lines[0].strip()

        # Headword lines start with ALL-CAPS Latin words (semicolon-separated),
        # followed by '. body text' or ', see _Xref_.' on the same line.
        # Strategy: split on the first '. ' to separate headword cluster from body.
        dot_space = first_line.find(". ")
        if dot_space != -1:
            hw_part = first_line[:dot_space]
            body_start = first_line[dot_space + 2:]
        else:
            hw_part = first_line.rstrip(".")
            body_start = ""

        # The headword part must be all-caps Latin words (with ; , - as separators)
        if not hw_part or not re.match(r"^[A-ZÆŒÁÉÍÓÚ][A-ZÆŒÁÉÍÓÚ\s;,\-]+$", hw_part):
            continue

        # Skip cross-references like "ABDERE, see _Celare_."
        if ", see" in hw_part.lower() or body_start.strip().lower().startswith("see "):
            continue

        rest_lines = " ".join(l.strip() for l in lines[1:]).strip()
        body_text = (body_start + " " + rest_lines).strip()
        full_text = first_line + "\n" + rest_lines

        # Skip pure cross-reference entries ("ABDERE, see _Celare_.")
        if re.search(r",?\s+see\s+_", full_text) and not body_text:
            continue
        if body_text.lower().startswith("see "):
            continue

        # Parse the semicolon-separated headwords from the hw_part
        raw_headwords = [h.strip() for h in hw_part.split(";") if h.strip()]
        headwords = [_normalize_headword(h) for h in raw_headwords if h.strip()]
        if not headwords:
            continue

        # Extract a concise gloss
        gloss = _extract_gloss(body_text, headwords[0])
        if not gloss or len(gloss) < 4:
            continue

        primary = headwords[0]
        forms = list(dict.fromkeys(headwords))  # dedup, preserve order

        entry = {
            "lemma": primary,
            "forms": forms,
            "gloss": gloss,
            "confidence": DOEDERLEIN_CONFIDENCE,
            "morphology": None,
        }
        entries.append(entry)

        # Emit alias entries for each synonym pointing at same gloss
        for synonym in headwords[1:]:
            if synonym == primary:
                continue
            entries.append({
                "lemma": synonym,
                "forms": [synonym],
                "gloss": gloss,
                "confidence": DOEDERLEIN_CONFIDENCE - 0.02,
                "morphology": None,
            })

    return entries


def _normalize_headword(raw: str) -> str:
    return raw.strip().rstrip(".,;:").strip().lower()


def _extract_gloss(body_text: str, primary_lemma: str) -> str:
    """Extract a short English gloss from the entry body text."""
    # Strip formatting marks
    cleaned = re.sub(r"\+([^+]+)\+", r"\1", body_text)   # +bold+
    cleaned = re.sub(r"_([^_]+)_", r"\1", cleaned)         # _italic_
    # Strip leading Greek/non-ASCII parentheticals e.g. "(ὠκύς)"
    cleaned = re.sub(r"^\s*\([^\x00-\x7F]+\)\s*", "", cleaned)
    # Strip trailing citation like "(iv. 250.)"
    cleaned = re.sub(r"\s*\([ivxlcdmIVXLCDM\d\s,.]+\)\s*$", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    # 1. Prefer a quoted gloss: text in 'single quotes' within the first 300 chars
    quote_match = re.search(
        r"['\u2018\u2019\u0027]([^'\u2018\u2019\u0027]{3,80})['\u2018\u2019\u0027]",
        cleaned[:400],
    )
    if quote_match:
        candidate = quote_match.group(1).strip().rstrip(".,;:")
        if _looks_like_gloss(candidate):
            return candidate

    # 2. Take first sentence
    first_sentence = re.split(r"[.;]", cleaned)[0].strip()
    # Drop leading "1. " numbering
    first_sentence = re.sub(r"^\d+\.\s+", "", first_sentence)
    # Drop the primary lemma word from start if echoed
    first_sentence = re.sub(
        r"^" + re.escape(primary_lemma) + r"\s+",
        "",
        first_sentence,
        flags=re.IGNORECASE,
    )
    # Strip leading verbose connectors: "means ", "denotes ", "is ", "and X mean(s) "
    first_sentence = re.sub(r"^and\s+\w+\s+(?:denotes?|means?)\s+", "", first_sentence, flags=re.IGNORECASE)
    first_sentence = re.sub(r"^(?:denotes?|means?|signifies?|indicates?)\s+", "", first_sentence, flags=re.IGNORECASE)
    # Strip leading non-ASCII (Greek/etc.) parenthetical + optional verb
    first_sentence = re.sub(r"^\([^\x00-\x7F()]+\)\s*(?:denotes?|means?)?\s*", "", first_sentence)
    first_sentence = re.sub(r"^(?:denotes?|means?|signifies?|indicates?)\s+", "", first_sentence, flags=re.IGNORECASE)
    # Strip "from X" prefix like "(from κάρφω) means"
    first_sentence = re.sub(r"^\(from\s+[^\)]+\)\s*(?:denotes?|means?)?\s*", "", first_sentence, flags=re.IGNORECASE)
    first_sentence = re.sub(r"^(?:denotes?|means?|signifies?|indicates?)\s+", "", first_sentence, flags=re.IGNORECASE)
    first_sentence = first_sentence.strip()

    if len(first_sentence) > 10:
        return first_sentence[:140].strip().rstrip(".,;:")

    return ""


def _looks_like_gloss(text: str) -> bool:
    if len(text) < 3 or len(text) > 90:
        return False
    # Reject if it looks like Latin (lots of Latin case endings or no English words)
    if re.search(r"\b(esse|erat|sunt|cum|qui|quod|enim)\b", text.lower()):
        return False
    return True


def _merge_into_lexicon(new_entries: list[dict]) -> None:
    """Merge Döderlein entries into the reference lexicon JSON.

    Only adds entries whose lemma is not already present — existing hand-curated
    entries always take priority.
    """
    existing = json.loads(LEXICON_JSON.read_text(encoding="utf-8"))
    existing_lemmas = {e["lemma"].lower() for e in existing}

    added = 0
    for entry in new_entries:
        if entry["lemma"] in existing_lemmas:
            continue
        # Remove the internal 'source' key before writing
        clean = {k: v for k, v in entry.items() if k != "source"}
        existing.append(clean)
        existing_lemmas.add(entry["lemma"])
        added += 1

    result = sorted(existing, key=lambda e: e["lemma"].lower())
    LEXICON_JSON.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Added {added} new entries. Total: {len(result)}.", file=sys.stderr)


if __name__ == "__main__":
    main()
