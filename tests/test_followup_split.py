"""The follow-up split (docs/FOLLOWUP_SPLIT.md): made once from a recorded seed, recorded
by hash, and the follow-up test split sealed. The data is git-ignored, so the tests that
read it skip without it. None of these reads a follow-up test problem's text or answer.
Never calls the API."""

import hashlib
import importlib.util
from pathlib import Path

import pytest

from opt_agent import followup
from opt_agent.followup import Problem, Sealed, is_correct, load, read_split

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("split", ROOT / "scripts" / "followup_split.py")
split_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(split_script)

needs_data = pytest.mark.skipif(not followup.COMPLEXLP.exists(), reason="needs LLM4OR's data")


def test_the_doc_records_the_splits_hash():
    digest = hashlib.sha256(followup.SPLIT_PATH.read_bytes()).hexdigest()
    assert f"SHA-256 `{digest}`" in (ROOT / "docs" / "FOLLOWUP_SPLIT.md").read_text()


def test_25_dev_86_test_disjoint_and_industryor_all_test():
    s = read_split()
    dev, test = set(s["complexlp"]["dev"]), set(s["complexlp"]["test"])
    assert (len(dev), len(test), len(dev | test)) == (25, 86, 111) and not dev & test
    assert s["industryor"] == {"dev": [], "test": list(range(1, 43))}
    assert s["seed"] == split_script.SEED


@needs_data
def test_the_split_reproduces_from_its_seed():
    data = split_script.split()
    assert split_script.dumps(data) == followup.SPLIT_PATH.read_text()
    digest = hashlib.sha256(followup.SPLIT_PATH.read_bytes()).hexdigest()
    assert split_script.doc(data, digest) == (ROOT / "docs" / "FOLLOWUP_SPLIT.md").read_text()


@pytest.mark.parametrize("split", ["complexlp-test", "industryor-test"])
def test_a_follow_up_test_split_is_sealed(split):
    with pytest.raises(Sealed):
        load(split)


@needs_data
def test_the_dev_split_loads_dev_problems_only():
    problems = load("complexlp-dev")
    assert [int(p.id) for p in problems] == read_split()["complexlp"]["dev"]
    assert all(p.document for p in problems)


@pytest.mark.parametrize(
    ("answer", "status", "objective", "right"),
    [
        (57.0, "optimal", 57.004, True),  # within 1e-4 relative
        (57.0, "optimal", 57.1, False),
        (57.0, "infeasible", None, False),
        (None, "infeasible", None, True),  # no optimum, and none claimed
        (57.0, None, None, False),  # no answer
    ],
)
def test_answers_are_compared_at_1e_4(answer, status, objective, right):
    assert is_correct(Problem(id="x", document="", answer=answer), status, objective) is right
