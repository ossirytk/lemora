"""Shared gloss normalization and humanization utilities."""

from __future__ import annotations

import re
import unicodedata

_CASE_NAME_BY_ABBREV = {
    "nom": "nominative",
    "gen": "genitive",
    "dat": "dative",
    "acc": "accusative",
    "abl": "ablative",
    "voc": "vocative",
    "loc": "locative",
}

_PRONOUN_GLOSSES = {
    "ego": "I / me",
    "tu": "you (singular)",
    "nos": "we / us",
    "vos": "you (plural)",
}

_GRAMMAR_ABBREV_REWRITES = (
    (r"\bimper\.", "imperative"),
    (r"\binf\.", "infinitive"),
    (r"\bpart\.", "participle"),
    (r"\bpres\.", "present"),
    (r"\bperf\.", "perfect"),
    (r"\bfut\.", "future"),
    (r"\bsing\.", "singular"),
    (r"\bplur\.", "plural"),
    (r"\bmasc\.", "masculine"),
    (r"\bfem\.", "feminine"),
    (r"\bneut\.", "neuter"),
    (r"\badj\.", "adjective"),
    (r"\badv\.", "adverb"),
    (r"\bprep\.", "preposition"),
    (r"\bconj\.", "conjunction"),
    (r"\bpron\.", "pronoun"),
)


def concise_gloss(gloss: str, *, max_length: int) -> str:
    """Return a shortened and humanized gloss."""
    cleaned = normalize_punctuation(normalize_space(gloss))
    split_pattern = r";|\s[—-]\s|(?<=\w)\.\s+(?=[A-Z])"
    fragments = [part.strip(" .,:;-") for part in re.split(split_pattern, cleaned) if part.strip() != ""]
    if not fragments:
        return humanize_gloss(cleaned)

    best = max(fragments, key=readability_score)
    compact = best[:max_length] if len(best) > max_length else best
    return humanize_gloss(compact)


def readability_score(gloss: str) -> float:
    """Heuristic score for picking the most human-readable gloss fragment."""
    cleaned = normalize_space(gloss).lower()
    score = 0.0
    if re.search(r"\b(to|a|an|the|of|for|with|from)\b", cleaned):
        score += 2.0

    penalties = (
        (r"\b(ap|ib|cf|inscr|naev|plaut|cic|verg|lucil)\.", 0.8),
        (r"\d", 0.2),
    )
    for pattern, weight in penalties:
        score -= len(re.findall(pattern, cleaned)) * weight

    max_readable_length = 140
    if len(cleaned) > max_readable_length:
        score -= 1.0
    return score


def humanize_gloss(gloss: str) -> str:
    """Convert terse dictionary abbreviations into clearer English."""
    stripped = gloss.strip()

    imperative_pattern = re.compile(r"^imper\.\s*,?\s*from\s+(?P<lemma>[^\s.;,]+)", re.IGNORECASE)
    imperative_match = imperative_pattern.match(stripped)
    if imperative_match is not None:
        lemma = imperative_match.group("lemma").strip(".,; ")
        canonical = latin_fold(lemma)
        imperative_glosses = {
            "fio": "be/become",
        }
        if canonical in imperative_glosses:
            return f"imperative of {lemma} ({imperative_glosses[canonical]})"
        return f"imperative of {lemma}"

    case_of_pattern = re.compile(
        r"^(?:(?P<form>[^,]+),\s*)?"
        r"(?P<cases>(?:nom|gen|dat|acc|abl|voc|loc)\.(?:\s*(?:,|and)\s*(?:nom|gen|dat|acc|abl|voc|loc)\.)*)\s+"
        r"of\s+(?P<lemma>[^\s.;,]+)",
        re.IGNORECASE,
    )
    case_match = case_of_pattern.match(stripped)
    if case_match is not None:
        cases = [item.lower() for item in re.findall(r"(nom|gen|dat|acc|abl|voc|loc)\.", case_match.group("cases"))]
        readable_cases = []
        for case in cases:
            expanded = _CASE_NAME_BY_ABBREV.get(case)
            if expanded is not None and expanded not in readable_cases:
                readable_cases.append(expanded)

        lemma = case_match.group("lemma").strip(".,; ")
        case_label = "/".join(readable_cases) if readable_cases else "case"
        canonical = latin_fold(lemma)
        if canonical in _PRONOUN_GLOSSES:
            return f"{case_label} of {lemma} ({_PRONOUN_GLOSSES[canonical]})"
        return f"{case_label} of {lemma}"

    expanded = stripped
    for pattern, replacement in _GRAMMAR_ABBREV_REWRITES:
        expanded = re.sub(pattern, replacement, expanded, flags=re.IGNORECASE)
    return normalize_punctuation(expanded)


def normalize_space(text: str) -> str:
    """Normalize whitespace runs."""
    return " ".join(text.split()).strip()


def normalize_punctuation(text: str) -> str:
    """Normalize spacing around punctuation."""
    normalized = text.replace(" .", ".").replace(" ,", ",")
    normalized = re.sub(r"\s+,", ",", normalized)
    normalized = re.sub(r",(?=\S)", ", ", normalized)
    return normalize_space(normalized)


def latin_fold(text: str) -> str:
    """Fold Latin text to ASCII-like lowercase for robust matching."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return stripped.lower()
