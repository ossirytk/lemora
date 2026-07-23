import lemora.config as config_module


def test_default_lewis_short_path_uses_existing_candidate(tmp_path, monkeypatch) -> None:
    lexicon_path = tmp_path / "lat.ls.perseus-eng2.xml"
    lexicon_path.write_text("<xml />", encoding="utf-8")
    monkeypatch.setattr(config_module, "_LEWIS_SHORT_CANDIDATES", (lexicon_path,))

    assert config_module._default_lewis_short_path() == lexicon_path


def test_from_env_prefers_auto_detected_lewis_path(monkeypatch, tmp_path) -> None:
    lexicon_path = tmp_path / "lat.ls.perseus-eng2.xml"
    lexicon_path.write_text("<xml />", encoding="utf-8")
    monkeypatch.delenv("LEMORA_LEWIS_SHORT_PATH", raising=False)
    monkeypatch.setattr(config_module, "_LEWIS_SHORT_CANDIDATES", (lexicon_path,))

    cfg = config_module.LemoraConfig.from_env()
    assert cfg.lewis_short_path == lexicon_path
