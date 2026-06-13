from lemora.adapters.base import DictionaryAdapter
from lemora.adapters.lewis_short import LewisShortAdapter
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
        return []


class _StubAnalyzer:
    def __init__(self, analyses: list[TokenAnalysis]) -> None:
        self._analyses = analyses

    def analyze(self, text: str) -> list[TokenAnalysis]:
        _ = text
        return self._analyses
