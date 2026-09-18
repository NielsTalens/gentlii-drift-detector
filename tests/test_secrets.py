import subprocess
from unittest.mock import Mock

import pytest

from gentlii_drift_detector.secrets import SecretLookupError, load_openai_api_key


SECRET_TOOL_COMMAND = [
    "secret-tool",
    "lookup",
    "key",
    "GNTL_DD",
    "app",
    "gentlii-drift-detection",
]


def test_loads_stripped_secret_using_exact_safe_command() -> None:
    runner = Mock(
        return_value=subprocess.CompletedProcess(
            args=SECRET_TOOL_COMMAND,
            returncode=0,
            stdout="  test-secret\n",
            stderr="",
        )
    )

    result = load_openai_api_key(runner=runner)

    assert result == "test-secret"
    runner.assert_called_once_with(
        SECRET_TOOL_COMMAND,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("stdout", ["", " \n\t"])
def test_rejects_empty_secret_without_disclosing_command_output(stdout: str) -> None:
    runner = Mock(
        return_value=subprocess.CompletedProcess(
            args=SECRET_TOOL_COMMAND,
            returncode=0,
            stdout=stdout,
            stderr="sensitive stderr",
        )
    )

    with pytest.raises(SecretLookupError) as exc_info:
        load_openai_api_key(runner=runner)

    message = str(exc_info.value)
    assert "sensitive stderr" not in message
    assert stdout.strip() not in message if stdout.strip() else True


def test_reports_missing_secret_tool_safely() -> None:
    runner = Mock(side_effect=FileNotFoundError("secret-tool unavailable"))

    with pytest.raises(SecretLookupError) as exc_info:
        load_openai_api_key(runner=runner)

    assert "secret-tool unavailable" not in str(exc_info.value)


def test_reports_nonzero_exit_without_disclosing_output() -> None:
    runner = Mock(
        return_value=subprocess.CompletedProcess(
            args=SECRET_TOOL_COMMAND,
            returncode=1,
            stdout="sensitive stdout",
            stderr="sensitive stderr",
        )
    )

    with pytest.raises(SecretLookupError) as exc_info:
        load_openai_api_key(runner=runner)

    message = str(exc_info.value)
    assert "sensitive stdout" not in message
    assert "sensitive stderr" not in message
