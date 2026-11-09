"""Configuration: find the Anthropic API key without ever hard-coding it."""

import os
from pathlib import Path

from dotenv import dotenv_values

API_KEY_VAR = "ANTHROPIC_API_KEY"
# The .env file is read only when this is exactly "1". Without the gate, a key sitting in
# .env would be picked up by any command run from the checkout, so `unset
# ANTHROPIC_API_KEY` wouldn't be enough to guarantee that nothing can spend
# (docs/audit/2026-11-review.md, section 7.2).
LIVE_VAR = "OPT_AGENT_LIVE"


class MissingAPIKeyError(RuntimeError):
    """Raised when no API key may be used: none in the environment, and .env either
    missing, keyless, or not allowed (OPT_AGENT_LIVE isn't 1)."""


def get_api_key(dotenv_path: Path = Path(".env")) -> str:
    """Return the Anthropic API key.

    The real environment comes first (how CI and Docker inject secrets). The .env file is a
    fallback for development, read only when OPT_AGENT_LIVE=1, so spending from .env is
    always a deliberate choice. The file is read without modifying os.environ, so this has
    no side effects.
    """
    from_env = (os.environ.get(API_KEY_VAR) or "").strip()
    if from_env:
        return from_env
    if os.environ.get(LIVE_VAR) != "1":
        raise MissingAPIKeyError(
            f"{API_KEY_VAR} is not set. To use the key in {dotenv_path}, run with "
            f"{LIVE_VAR}=1 (the file is never read otherwise), or export {API_KEY_VAR}."
        )
    from_file = (dotenv_values(dotenv_path).get(API_KEY_VAR) or "").strip()
    if not from_file:
        raise MissingAPIKeyError(
            f"{LIVE_VAR}=1, but {API_KEY_VAR} is in neither the environment nor "
            f"{dotenv_path}. Copy .env.example to .env and add your key, or export "
            f"{API_KEY_VAR}."
        )
    return from_file
