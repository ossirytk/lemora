from lemora.cli import run


def test_translate_command_returns_success(monkeypatch) -> None:
    monkeypatch.delenv("LEMORA_WHITAKER_PATH", raising=False)
    monkeypatch.delenv("LEMORA_LEWIS_SHORT_PATH", raising=False)
    monkeypatch.delenv("LEMORA_MODEL_PATH", raising=False)
    exit_code = run(["translate", "amo"])
    assert exit_code == 0
