from lemora.grammar_reference import load_national_archives_grammar


def test_load_national_archives_grammar_contains_pronoun_forms() -> None:
    grammar = load_national_archives_grammar()
    assert grammar.pronoun_lemma_by_form["eius"] == "is"
    assert grammar.pronoun_lemma_by_form["cuius"] == "qui"


def test_load_national_archives_grammar_contains_grammar_labels() -> None:
    grammar = load_national_archives_grammar()
    assert grammar.case_name_by_abbrev["dat"] == "dative"
    assert grammar.grammar_abbrev_expansions["adj"] == "adjective"


def test_load_national_archives_grammar_contains_verb_forms() -> None:
    grammar = load_national_archives_grammar()
    assert grammar.verb_lemma_by_form["vici"] == "vinco"
