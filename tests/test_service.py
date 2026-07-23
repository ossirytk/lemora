from lemora.adapters.base import DictionaryAdapter
from lemora.adapters.lewis_short import LewisShortAdapter
from lemora.adapters.national_archives_reference import NationalArchivesReferenceAdapter
from lemora.adapters.whitaker import WhitakerAdapter
from lemora.models import DictionarySense, TokenAnalysis
from lemora.service import LemoraService


def test_translate_normalizes_query() -> None:
    service = LemoraService(dictionaries=[WhitakerAdapter(), LewisShortAdapter()])
    result = service.translate("  ArMa   VirumQue ")
    assert result.normalized_query == "arma virumque"
    lemmas = {sense.lemma for sense in result.senses}
    assert "vir" in lemmas
    assert "arma" in lemmas


def test_translate_merges_duplicate_senses_from_sources() -> None:
    service = LemoraService(
        dictionaries=[
            _StubDictionary(
                source_name="Whitaker",
                senses=[
                    DictionarySense(
                        lemma="amo",
                        gloss="to love",
                        source="Whitaker",
                        confidence=0.61,
                        morphology="verb",
                    ),
                ],
            ),
            _StubDictionary(
                source_name="Lewis & Short",
                senses=[
                    DictionarySense(
                        lemma="amo",
                        gloss="to love",
                        source="Lewis & Short",
                        confidence=0.74,
                        morphology=None,
                    ),
                ],
            ),
        ],
    )

    result = service.translate("amo")

    assert len(result.senses) == 1
    assert result.senses[0].source == "Lewis & Short, Whitaker"
    assert result.senses[0].morphology == "verb"
    assert result.senses[0].confidence > 0.74


def test_translate_ranking_prefers_lewis_short_at_equal_confidence() -> None:
    service = LemoraService(dictionaries=[WhitakerAdapter(), LewisShortAdapter()])
    result = service.translate("virum")
    assert result.senses[0].source.startswith("Lewis & Short")


def test_translate_strips_enclitic_que_for_token_lookup() -> None:
    service = LemoraService(dictionaries=[WhitakerAdapter(), LewisShortAdapter()])
    result = service.translate("virumque")
    assert all(sense.lemma == "vir" for sense in result.senses)


def test_translate_uses_analyzer_lemma_candidates_for_lookup() -> None:
    service = LemoraService(
        dictionaries=[_StubQueryDictionary()],
        analyzer=_StubAnalyzer([TokenAnalysis(token="dixi", lemma_candidates=("dico",))]),  # noqa: S106
    )
    result = service.translate("dixi")
    assert len(result.senses) == 1
    assert result.senses[0].lemma == "dico"
    assert result.senses[0].confidence < 0.7


def test_translate_normalizes_tokens_with_trailing_punctuation() -> None:
    service = LemoraService(dictionaries=[_StubQueryDictionary()])
    result = service.translate('Amor""')
    assert result.normalized_query == "amor"
    assert len(result.senses) == 1
    assert result.senses[0].lemma == "amor"


def test_translate_maps_pronoun_forms_to_reference_lemmas() -> None:
    service = LemoraService(dictionaries=[_StubQueryDictionary()])
    result = service.translate("eius cuius")
    lemmas = {sense.lemma for sense in result.senses}
    assert "is" in lemmas
    assert "qui" in lemmas


def test_translate_maps_reference_verb_forms_to_lemmas() -> None:
    service = LemoraService(dictionaries=[_StubQueryDictionary()])
    result = service.translate("veni vidi vici")
    lemmas = {sense.lemma for sense in result.senses}
    assert "venio" in lemmas
    assert "video" in lemmas
    assert "vinco" in lemmas


def test_translate_prefers_senses_matching_token_pos() -> None:
    service = LemoraService(
        dictionaries=[
            _StubDictionary(
                source_name="Lewis & Short",
                senses=[
                    DictionarySense(
                        lemma="vici",
                        gloss="a village street",
                        source="Lewis & Short",
                        confidence=0.75,
                        morphology="n.",
                    ),
                    DictionarySense(
                        lemma="vinco",
                        gloss="to conquer",
                        source="Lewis & Short",
                        confidence=0.75,
                        morphology="v. a.",
                    ),
                ],
            ),
        ],
        analyzer=_StubAnalyzer([TokenAnalysis(token="vici", lemma_candidates=("vinco",), pos="VERB")]),
    )
    result = service.translate("vici")
    assert result.senses[0].lemma == "vinco"


def test_translate_limits_multi_token_phrase_noise() -> None:
    service = LemoraService(
        dictionaries=[
            _StubDictionary(
                source_name="Lewis & Short",
                senses=[
                    DictionarySense(lemma="venio", gloss="to come", source="Lewis & Short", confidence=0.87, morphology="v. a."),
                    DictionarySense(lemma="video", gloss="to see", source="Lewis & Short", confidence=0.87, morphology="v. a."),
                    DictionarySense(lemma="vinco", gloss="to conquer", source="Lewis & Short", confidence=0.87, morphology="v. a."),
                    DictionarySense(lemma="vicus", gloss="village street", source="Lewis & Short", confidence=0.75, morphology="n."),
                ],
            ),
        ],
        analyzer=_StubAnalyzer(
            [
                TokenAnalysis(token="veni", lemma_candidates=("venio",), pos="VERB"),
                TokenAnalysis(token="vidi", lemma_candidates=("video",), pos="VERB"),
                TokenAnalysis(token="vici", lemma_candidates=("vinco",), pos="VERB"),
            ],
        ),
    )
    result = service.translate("Veni, vidi, vici")
    lemmas = [sense.lemma for sense in result.senses]
    assert lemmas == ["venio", "video", "vinco"]
    assert "vicus" not in lemmas


def test_reference_adapter_covers_common_school_latin_phrase() -> None:
    service = LemoraService(dictionaries=[NationalArchivesReferenceAdapter()])
    result = service.translate("Veritas liberabit vos")
    lemmas = {sense.lemma for sense in result.senses}
    assert {"veritas", "libero", "vos"} <= lemmas


class _StubDictionary(DictionaryAdapter):
    def __init__(self, source_name: str, senses: list[DictionarySense]) -> None:
        self.source_name = source_name
        self._senses = senses

    def lookup(self, query: str) -> list[DictionarySense]:
        _ = query
        return self._senses


class _StubQueryDictionary(DictionaryAdapter):
    source_name = "Stub"

    def lookup(self, query: str) -> list[DictionarySense]:
        if query == "dico":
            return [
                DictionarySense(
                    lemma="dico",
                    gloss="to say",
                    source=self.source_name,
                    confidence=0.7,
                ),
            ]
        if query == "amor":
            return [
                DictionarySense(
                    lemma="amor",
                    gloss="love",
                    source=self.source_name,
                    confidence=0.7,
                ),
            ]
        if query == "is":
            return [
                DictionarySense(
                    lemma="is",
                    gloss="he / she / it; that",
                    source=self.source_name,
                    confidence=0.66,
                ),
            ]
        if query == "qui":
            return [
                DictionarySense(
                    lemma="qui",
                    gloss="who / which",
                    source=self.source_name,
                    confidence=0.66,
                ),
            ]
        if query == "venio":
            return [
                DictionarySense(
                    lemma="venio",
                    gloss="to come",
                    source=self.source_name,
                    confidence=0.66,
                ),
            ]
        if query == "video":
            return [
                DictionarySense(
                    lemma="video",
                    gloss="to see",
                    source=self.source_name,
                    confidence=0.66,
                ),
            ]
        if query == "vinco":
            return [
                DictionarySense(
                    lemma="vinco",
                    gloss="to conquer",
                    source=self.source_name,
                    confidence=0.66,
                ),
            ]
        return []


class _StubAnalyzer:
    def __init__(self, analyses: list[TokenAnalysis]) -> None:
        self._analyses = analyses

    def analyze(self, text: str) -> list[TokenAnalysis]:
        _ = text
        return self._analyses
