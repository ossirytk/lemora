from lemora.llm.llama_synth import LlamaSynthesizer
from lemora.models import DictionarySense


def test_synthesize_prefers_readable_gloss_for_same_lemma(tmp_path) -> None:
    synthesizer = LlamaSynthesizer(tmp_path / "model.gguf")
    senses = [
        DictionarySense(
            lemma="dico",
            gloss="praes. DEICO, Inscr. Orell. 4848 ; imp. usu. dic; cf. duc",
            source="Lewis & Short",
            confidence=0.83,
        ),
        DictionarySense(
            lemma="dico",
            gloss="To proclaim, make known.",
            source="Lewis & Short",
            confidence=0.83,
        ),
    ]

    synthesis = synthesizer.synthesize("dico", senses)

    assert synthesis is not None
    assert "verb: dico = to proclaim, make known" in synthesis.lower()
    assert "praes. deico" not in synthesis.lower()


def test_synthesize_includes_multiple_tokens(tmp_path) -> None:
    synthesizer = LlamaSynthesizer(tmp_path / "model.gguf")
    senses = [
        DictionarySense(
            lemma="dico",
            gloss="To proclaim, make known.",
            source="Lewis & Short",
            confidence=0.83,
        ),
        DictionarySense(
            lemma="vobis",
            gloss="dat. and abl. of vos",
            source="Lewis & Short",
            confidence=0.83,
        ),
    ]

    synthesis = synthesizer.synthesize("dico vobis", senses)

    assert synthesis is not None
    assert "components:" in synthesis.lower()
    assert "verb: dico =" in synthesis.lower()
    assert "addressee: vobis =" in synthesis.lower()
    assert "dative/ablative of vos (you (plural))" in synthesis.lower()


def test_synthesize_humanizes_imperative_gloss(tmp_path) -> None:
    synthesizer = LlamaSynthesizer(tmp_path / "model.gguf")
    senses = [
        DictionarySense(
            lemma="fi",
            gloss="imper. , from fio, v. facio init",
            source="Lewis & Short",
            confidence=0.83,
        ),
    ]
    synthesis = synthesizer.synthesize("fi", senses)
    assert synthesis is not None
    assert "verb: fi = imperative of fio (be/become)" in synthesis.lower()
