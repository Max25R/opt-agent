"""The live tests run only with OPT_AGENT_LIVE=1, whatever -m says (tests/conftest.py)."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_selected_live_tests_are_skipped_without_opt_agent_live():
    # No key in the environment either, so even a broken gate couldn't spend.
    env = {k: v for k, v in os.environ.items() if k not in ("OPT_AGENT_LIVE", "ANTHROPIC_API_KEY")}
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "live", "-q", "-p", "no:cacheprovider",
         "tests/test_live.py"],
        cwd=ROOT, env=env, capture_output=True, text=True,
    )  # fmt: skip
    assert done.returncode == 0, done.stdout + done.stderr
    summary = done.stdout.strip().splitlines()[-1]
    assert "skipped" in summary and "passed" not in summary and "failed" not in summary, summary
