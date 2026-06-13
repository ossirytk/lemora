from lemora.nlp.cltk_analyzer import CltkAnalyzer, _clean_token, _coerce_features


def test_cltk_analyzer_fallback_generates_lemma_candidates() -> None:
    analyzer = CltkAnalyzer()
    analysis = analyzer.analyze("virumque")
    assert len(analysis) == 1
    assert analysis[0].token == "virumque"  # noqa: S105
    assert "virum" in analysis[0].lemma_candidates


def test_cltk_analyzer_returns_all_tokens() -> None:
    analyzer = CltkAnalyzer()
    analysis = analyzer.analyze("dico vobis")
    assert [token.token for token in analysis] == ["dico", "vobis"]


def test_clean_token_handles_tag_objects() -> None:
    assert _clean_token(_FakePosTag("VERB")) == "verb"


def test_coerce_features_handles_model_dump_payload() -> None:
    features = _coerce_features(
        _FakeFeatureSet(
            {
                "features": [
                    {"key": "Mood", "value": "Ind", "value_label": "Indicative"},
                    {"key": "Number", "value": "Sing", "value_label": "Singular"},
                ],
            },
        ),
    )
    assert features == {"Mood": "Indicative", "Number": "Singular"}


class _FakePosTag:
    def __init__(self, tag: str) -> None:
        self.tag = tag


class _FakeFeatureSet:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(self) -> dict[str, object]:
        return self._payload
