"""Configuration: find the Anthropic API key without ever hard-coding it."""

import os
from pathlib import Path

from dotenv import dotenv_values

API_KEY_VAR = "ANTHROPIC_API_KEY"


class MissingAPIKeyError(RuntimeError):
    """Raised when the API key is in neither the environment nor the .env file."""


def get_api_key(dotenv_path: Path = Path(".env")) -> str:
    """Return the Anthropic API key.

    Checks the real environment first (how CI and Docker inject secrets),
    then falls back to a local .env file (convenient for development).
    The file is read without modifying os.environ, so this has no side effects.
    """
    from_env = os.environ.get(API_KEY_VAR)
    from_file = dotenv_values(dotenv_path).get(API_KEY_VAR)
    key = (from_env or from_file or "").strip()
    if not key:
        raise MissingAPIKeyError(
            f"{API_KEY_VAR} is not set. Copy .env.example to .env and add your key, "
            f"or export {API_KEY_VAR} in your shell."
        )
    return key
