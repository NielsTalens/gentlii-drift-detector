import subprocess
from collections.abc import Callable


SECRET_TOOL_COMMAND = [
    "secret-tool",
    "lookup",
    "key",
    "GNTL_DD",
    "app",
    "gentlii-drift-detection",
]


class SecretLookupError(RuntimeError):
    """Raised when the OpenAI API key cannot be loaded safely."""


def load_openai_api_key(
    *, runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run
) -> str:
    try:
        result = runner(
            SECRET_TOOL_COMMAND,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        raise SecretLookupError("Secret lookup tool is not available.") from None

    if result.returncode != 0:
        raise SecretLookupError("Secret lookup failed.")

    secret = result.stdout.strip()
    if not secret:
        raise SecretLookupError("Secret lookup returned no value.")

    return secret
