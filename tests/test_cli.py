import pytest

from gentlii_drift_detector.cli import main


def test_help_describes_cli_interface(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0
    help_text = capsys.readouterr().out
    assert "INPUT.md" in help_text
    assert "--output" in help_text
    assert "--model" in help_text
    assert "--batch-size" in help_text
