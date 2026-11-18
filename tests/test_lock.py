"""The installed packages are the locked ones, so tests and ground-truth rebuilds run on
the exact versions the committed answers were built with. The two optional locks,
requirements-docs.lock (the picture tools) and requirements-checks.lock (mypy and coverage),
are checked too: each may add packages, never re-pin one."""

import tomllib
from importlib.metadata import PackageNotFoundError, version

from packaging.requirements import Requirement

from opt_agent.freeze import drifted_packages, locked_versions
from opt_agent.runs import REPO_ROOT

LOCK = locked_versions()  # the freeze checks the same thing before a test run
DOCS_LOCK = REPO_ROOT / "requirements-docs.lock"
CHECKS_LOCK = REPO_ROOT / "requirements-checks.lock"


def pins(path) -> dict[str, str]:
    lines = [line.strip() for line in path.read_text().splitlines()]
    return {name.lower().replace("_", "-"): pinned for name, pinned in
            (line.split("==") for line in lines if line and not line.startswith("#"))}  # fmt: skip


def test_every_installed_version_is_the_locked_one():
    drifted = drifted_packages()
    assert drifted == {}, "installed versions differ from requirements.lock (locked, installed)"


def test_every_declared_dependency_is_locked():
    project = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())["project"]
    extras = project["optional-dependencies"]  # dev, and demo (fastapi, uvicorn)
    declared = project["dependencies"] + [r for group in extras.values() for r in group]
    for requirement in map(Requirement, declared):
        name = requirement.name.lower()
        assert name in LOCK, f"{name} is declared in pyproject.toml but not locked"
        assert LOCK[name] in requirement.specifier, (
            f"the locked {name} {LOCK[name]} breaks {requirement}"
        )


def test_the_docs_lock_pins_the_picture_tools_and_never_a_study_package():
    docs = pins(DOCS_LOCK)
    assert {"playwright", "matplotlib"} <= set(docs)
    assert not set(docs) & set(pins(REPO_ROOT / "requirements.lock")), (
        "requirements-docs.lock re-pins a package of requirements.lock"
    )


def test_installed_picture_tools_are_the_docs_locks_versions():
    """Only where they're installed (they're optional; CI's test job doesn't have them)."""
    for name, pinned in pins(DOCS_LOCK).items():
        try:
            installed = version(name)
        except PackageNotFoundError:
            continue
        assert installed == pinned, f"{name}: installed {installed}, docs lock {pinned}"


def test_the_checks_lock_pins_mypy_and_coverage_and_never_another_locks_package():
    checks = pins(CHECKS_LOCK)
    assert {"mypy", "coverage"} <= set(checks)
    assert not set(checks) & set(pins(REPO_ROOT / "requirements.lock")), (
        "requirements-checks.lock re-pins a package of requirements.lock"
    )
    assert not set(checks) & set(pins(DOCS_LOCK)), "the two optional locks share a package"


def test_installed_checkers_are_the_checks_locks_versions():
    """Only where they're installed (they're optional; CI's test job doesn't have them)."""
    for name, pinned in pins(CHECKS_LOCK).items():
        try:
            installed = version(name)
        except PackageNotFoundError:
            continue
        assert installed == pinned, f"{name}: installed {installed}, checks lock {pinned}"
