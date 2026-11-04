"""The repo is public, so no API key may ever be committed. These guard the current tree;
the history was checked by hand on 2026-11-04 (`git log --all -p`, no key found)."""

import re
import subprocess

import pytest

from opt_agent.runs import REPO_ROOT

# Anthropic keys start with "sk-ant-"; a real one is far longer than 20 characters, and
# requiring that length keeps this file's own pattern (and docs that mention the prefix)
# from matching.
KEY_PATTERN = re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)


@pytest.fixture(scope="module")
def tracked_files() -> list[str]:
    listing = git("ls-files")
    if listing.returncode != 0:
        pytest.skip("not a git checkout")
    return listing.stdout.splitlines()


def test_env_file_is_ignored():
    # `check-ignore` exits 0 when the path is ignored, whether or not the file exists.
    assert git("check-ignore", "-q", ".env").returncode == 0


def test_env_file_is_not_tracked(tracked_files):
    assert ".env" not in tracked_files


def test_no_tracked_file_contains_an_api_key(tracked_files):
    found = []
    for name in tracked_files:
        path = REPO_ROOT / name
        if not path.is_file():  # deleted in the working tree but still in the index
            continue
        text = path.read_bytes().decode("utf-8", errors="ignore")
        if KEY_PATTERN.search(text):
            found.append(name)
    assert found == [], f"files that look like they contain an API key: {found}"
