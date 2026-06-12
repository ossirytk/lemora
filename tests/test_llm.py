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
    assert "to proclaim, make known" in synthesis.lower()
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
    assert "dico:" in synthesis.lower()
    assert "vobis:" in synthesis.lower()
