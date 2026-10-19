"""One run of the pipeline (one problem from the CLI, or many in an evaluation).

A run has an id, a JSONL log, and optionally a response cache (api.Cache). The log starts
with a "run" line saying what the run ran on: the git commit, whether the working tree had
uncommitted changes, and the versions of Python and of every package that can change an
answer. Then come one line per API call ("attempt", "explanation") and one per problem
("problem"), each carrying the problem's tags, so a line can be traced to its problem,
split, and condition without any other file.
"""

import json
import platform
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pydantic import BaseModel

from opt_agent.api import Cache

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ["anthropic", "pydantic", "pulp", "cbcbox", "scipy", "numpy"]


class Tags(BaseModel):
    """Which problem a log line belongs to. All optional: the CLI has none of them."""

    problem_id: str | None = None
    split: str | None = None  # "dev" or "test"
    condition: str | None = None  # e.g. "single-shot", "self-correction"


@dataclass
class Run:
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    log_path: Path | None = None
    cache: Cache | None = None

    @classmethod
    def start(cls, log_path: Path | None = None, cache: Cache | None = None) -> "Run":
        run = cls(log_path=log_path, cache=cache)
        run.write("run", **environment())
        return run

    def write(self, kind: str, tags: Tags | None = None, **fields) -> None:
        if self.log_path is None:
            return
        line = {
            "kind": kind,
            "run_id": self.run_id,
            "time": datetime.now(UTC).isoformat(timespec="seconds"),
            **(tags or Tags()).model_dump(),
            **fields,
        }
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with self.log_path.open("a") as log:
            log.write(json.dumps(line, ensure_ascii=False) + "\n")


def environment() -> dict:
    return {
        "git_sha": _git("rev-parse", "HEAD"),
        "git_dirty": None if (status := _git("status", "--porcelain")) is None else bool(status),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {name: _version(name) for name in PACKAGES},
    }


def _git(*args: str) -> str | None:
    try:
        done = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    except OSError:  # no git at all
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def _version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None
