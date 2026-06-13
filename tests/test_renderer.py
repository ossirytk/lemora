from io import StringIO

from rich.console import Console

from lemora.models import DictionarySense, TranslationResult
from lemora.renderer import render_result


def test_render_result_collapses_duplicate_lemmas() -> None:
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=False, color_system=None)
    result = TranslationResult(
        query="Dico vobis",
        normalized_query="dico vobis",
        senses=(
            DictionarySense(
                lemma="dico",
                gloss="praes. DEICO, Inscr. Orell. 4848 ; imp. usu. dic; cf. duc, fac, fer, from duco",
                source="Lewis & Short",
                confidence=0.83,
            ),
            DictionarySense(
                lemma="dico",
                gloss="To proclaim, make known . So perh. only in the foll. passage.",
                source="Lewis & Short",
                confidence=0.83,
            ),
            DictionarySense(
                lemma="vobis",
                gloss="vōbīs , dat. and abl. of vos; v. tu.",
                source="Lewis & Short",
                confidence=0.83,
            ),
        ),
    )

    render_result(console=console, result=result, output_format="plain")
    output = buffer.getvalue()

    assert "dico (2)" in output
    assert "To proclaim, make known" in output
    assert "Inscr. Orell. 4848" not in output
    assert "dative/ablative of vos" in output
    assert "plural" in output


def test_render_result_humanizes_imperative_abbreviation() -> None:
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=False, color_system=None)
    result = TranslationResult(
        query="Semper fi",
        normalized_query="semper fi",
        senses=(
            DictionarySense(
                lemma="fi",
                gloss="imper. , from fio, v. facio init",
                source="Lewis & Short",
                confidence=0.83,
            ),
        ),
    )

    render_result(console=console, result=result, output_format="plain")
    output = buffer.getvalue()
    assert "imperative of fio (be/become)" in output
