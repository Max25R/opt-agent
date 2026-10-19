"""The installed packages are the locked ones, so tests and ground-truth rebuilds run on
the exact versions the committed answers were built with."""

import tomllib
from importlib.metadata import version

from packaging.requirements import Requirement

from opt_agent.runs import REPO_ROOT

LOCK = {
    name.lower(): pinned
    for line in (REPO_ROOT / "requirements.lock").read_text().splitlines()
    if line and not line.startswith("#")
    for name, pinned in [line.split("==")]
}


def test_every_installed_version_is_the_locked_one():
    drifted = {
        name: (pinned, version(name)) for name, pinned in LOCK.items() if version(name) != pinned
    }
    assert drifted == {}, "installed versions differ from requirements.lock (locked, installed)"


def test_every_declared_dependency_is_locked():
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]
    declared = project["dependencies"] + project["optional-dependencies"]["dev"]
    for requirement in map(Requirement, declared):
        name = requirement.name.lower()
        assert name in LOCK, f"{name} is declared in pyproject.toml but not locked"
        assert LOCK[name] in requirement.specifier, (
            f"the locked {name} {LOCK[name]} breaks {requirement}"
        )
