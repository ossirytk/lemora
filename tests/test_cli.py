from lemora.cli import run


def test_translate_command_returns_success() -> None:
    exit_code = run(["translate", "amo"])
    assert exit_code == 0
