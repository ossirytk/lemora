"""Curated grammar resource loader for National Archives stage materials."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files


@dataclass(frozen=True, slots=True)
class NationalArchivesGrammar:
    """Curated subset of Stage 1/2 grammar resources used by lemora."""

    pronoun_lemma_by_form: dict[str, str]
    verb_lemma_by_form: dict[str, str]
    case_name_by_abbrev: dict[str, str]
    grammar_abbrev_expansions: dict[str, str]


@lru_cache(maxsize=1)
def load_national_archives_grammar() -> NationalArchivesGrammar:
    """Load bundled grammar reference from package resources."""
    payload = json.loads(
        files("lemora.resources").joinpath("national_archives_grammar.json").read_text(encoding="utf-8"),
    )
    return NationalArchivesGrammar(
        pronoun_lemma_by_form={str(key): str(value) for key, value in payload["pronoun_lemma_by_form"].items()},
        verb_lemma_by_form={str(key): str(value) for key, value in payload["verb_lemma_by_form"].items()},
        case_name_by_abbrev={str(key): str(value) for key, value in payload["case_name_by_abbrev"].items()},
        grammar_abbrev_expansions={
            str(key): str(value) for key, value in payload["grammar_abbrev_expansions"].items()
        },
    )
