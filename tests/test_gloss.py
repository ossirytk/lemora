from lemora.gloss import concise_gloss


def test_concise_gloss_humanizes_case_patterns() -> None:
    gloss = "vōbīs , dat. and abl. of vos; v. tu."
    assert concise_gloss(gloss, max_length=96) == "dative/ablative of vos (you (plural))"


def test_concise_gloss_humanizes_imperative_pattern() -> None:
    gloss = "imper. , from fio, v. facio init"
    assert concise_gloss(gloss, max_length=96) == "imperative of fio (be/become)"


def test_concise_gloss_expands_common_grammar_abbreviations() -> None:
    gloss = "adj. and adv. form"
    assert concise_gloss(gloss, max_length=96) == "adjective and adverb form"
