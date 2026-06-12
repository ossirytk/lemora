import json

from lemora.adapters.lewis_short import LewisShortAdapter
from lemora.adapters.whitaker import WhitakerAdapter


def test_whitaker_lookup_matches_inflected_form() -> None:
    adapter = WhitakerAdapter()
    senses = adapter.lookup("amat")
    assert any(sense.lemma == "amo" for sense in senses)
    assert all(sense.source == "Whitaker" for sense in senses)


def test_lewis_short_loads_configured_lexicon(tmp_path) -> None:
    payload = [
        {
            "lemma": "porto",
            "forms": ["portat", "portare"],
            "gloss": "to carry",
            "confidence": 0.86,
            "morphology": "verb",
        },
    ]
    lexicon_path = tmp_path / "lewis_short.json"
    lexicon_path.write_text(json.dumps(payload), encoding="utf-8")

    adapter = LewisShortAdapter(lexicon_path)
    senses = adapter.lookup("portat")

    assert len(senses) == 1
    assert senses[0].lemma == "porto"
    assert senses[0].source == "Lewis & Short"
