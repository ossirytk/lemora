from lemora.adapters.whitaker import WhitakerAdapter
from lemora.service import LemoraService


def test_translate_normalizes_query() -> None:
    service = LemoraService(dictionaries=[WhitakerAdapter()])
    result = service.translate("  ArMa   VirumQue ")
    assert result.normalized_query == "arma virumque"
    assert result.senses == ()
