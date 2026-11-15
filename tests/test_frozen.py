"""opt_agent.frozen: a tag's tree, extracted from git's objects and run with its own package.
No API calls; the trees go to temporary directories."""

import pytest

from opt_agent import frozen
from opt_agent.frozen import FrozenError, Tree
from opt_agent.runs import git

TAG = "followup-freeze"
pytestmark = pytest.mark.skipif(git("rev-parse", "--verify", "--quiet", f"{TAG}^{{commit}}")
                                is None, reason="needs the tag (git fetch --tags)")  # fmt: skip


@pytest.fixture(scope="module")
def tree(tmp_path_factory) -> Tree:
    return Tree.extract(TAG, tmp_path_factory.mktemp("frozen") / "tree")


def test_the_tree_holds_the_tags_files_not_the_working_trees(tree):
    path = "src/opt_agent/followup_report.py"
    assert tree.read(path).decode() == git("show", f"{TAG}:{path}") + "\n"
    assert not (tree.root / "src" / "opt_agent" / "frozen.py").exists()  # newer than the tag


def test_python_runs_the_tags_package(tree):
    printed = tree.python("-c", "import opt_agent; print(opt_agent.__file__)")
    assert printed.strip() == str(tree.root / "src" / "opt_agent" / "__init__.py")


def test_frozen_code_never_sees_the_key(tree, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-made-up")
    monkeypatch.setenv("OPT_AGENT_LIVE", "1")
    script = "import os; print(os.getenv('ANTHROPIC_API_KEY'), os.getenv('OPT_AGENT_LIVE'))"
    assert tree.python("-c", script).strip() == "None None"


def test_a_failure_says_what_was_printed(tree):
    with pytest.raises(FrozenError, match="made-up failure"):
        tree.python("-c", "raise SystemExit('made-up failure')")


def test_copy_adds_a_file_from_this_checkout(tree):
    tree.copy("pyproject.toml")
    assert tree.read("pyproject.toml") == (frozen.REPO_ROOT / "pyproject.toml").read_bytes()
    with pytest.raises(FrozenError, match="isn't here"):
        tree.copy("no/such/file")


def test_a_tree_goes_into_a_new_directory(tree, tmp_path):
    with pytest.raises(FrozenError, match="isn't empty"):
        Tree.extract(TAG, tree.root)
    with pytest.raises(FrozenError, match="no tag no-such-tag"):
        Tree.extract("no-such-tag", tmp_path / "x")
