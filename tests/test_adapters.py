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


def test_lewis_short_loads_perseus_xml(tmp_path) -> None:
    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
<TEI>
  <text>
    <body>
      <entryFree key="arma" type="main" id="n1">
        <orth lang="la">arma</orth>
        <pos>noun neuter plural</pos>
        <sense level="1">arms; weapons</sense>
      </entryFree>
      <entryFree key="vir" type="main" id="n2">
        <orth lang="la">vir</orth>
        <pos>noun masculine</pos>
        <sense level="1">a man; husband</sense>
      </entryFree>
    </body>
  </text>
</TEI>
"""
    lexicon_path = tmp_path / "lat.ls.perseus-eng2.xml"
    lexicon_path.write_text(xml_payload, encoding="utf-8")

    adapter = LewisShortAdapter(lexicon_path)
    senses = adapter.lookup("arma")

    assert len(senses) == 1
    assert senses[0].lemma == "arma"
    assert senses[0].source == "Lewis & Short"
    assert senses[0].gloss.startswith("arms; weapons")


def test_lewis_short_normalizes_numbered_entry_keys(tmp_path) -> None:
    xml_payload = """<?xml version="1.0" encoding="UTF-8"?>
<TEI>
  <text>
    <body>
      <entryFree key="dico1" type="main" id="n1">
        <orth lang="la">dīco</orth>
        <pos>verb</pos>
        <sense level="1">to say; to speak</sense>
      </entryFree>
    </body>
  </text>
</TEI>
"""
    lexicon_path = tmp_path / "lat.ls.perseus-eng2.xml"
    lexicon_path.write_text(xml_payload, encoding="utf-8")

    adapter = LewisShortAdapter(lexicon_path)
    senses = adapter.lookup("dico")

    assert len(senses) == 1
    assert senses[0].lemma == "dico"
    assert senses[0].gloss.startswith("to say")
