"""Amendment 3's exploratory row (scripts/amendment3.py): a covered failure counts as correct
only when both judges say `reference`, and the row reproduces the run's numbers. No API
calls."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from opt_agent.run_results import load
from opt_agent.taxonomy import Failure

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "test"
SCRIPT = ROOT / "scripts" / "amendment3.py"
spec = importlib.util.spec_from_file_location("amendment3", SCRIPT)
amendment3 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(amendment3)

needs_run = pytest.mark.skipif(not RUN.exists(), reason="needs the committed test run")


def failure(key: str, problem: str, *conditions: str) -> Failure:
    return Failure(key=key, problem_id=problem, conditions=list(conditions),
                   status="optimal", objective=0.0, model=None)  # fmt: skip


def test_only_both_judges_saying_reference_counts():
    failures = [
        failure("a", "p1", "baseline"),
        failure("b", "p1", "single-shot", "self-correction"),
        failure("c", "p2", "baseline"),  # one judge disagrees
        failure("d", "p3", "baseline"),  # one judge left it unlabeled
        failure("e", "p4", "baseline"),  # not a covered problem
    ]
    labels = {
        "judge": {"a": "reference", "b": "coefficient", "c": "reference", "e": "reference"},
        "second": {"a": "reference", "b": "reference", "c": "integrality", "d": "reference",
                   "e": "reference"},
    }  # fmt: skip
    flipped = amendment3.counted_as_correct(failures, labels, covered=("p1", "p2", "p3"))
    # p1's baseline row has both judges' `reference`; its model row doesn't, so only the
    # baseline's failure counts as correct.
    assert flipped == {"baseline": ["p1"]}


@needs_run
def test_the_row_reproduces_the_test_run():
    row = amendment3.row(load(RUN))
    expected = ["-1540907330", "-2138755435", "-926961422", "1605420061", "2078392466",
                "431521997"]  # fmt: skip
    for condition in ("baseline", "single-shot", "self-correction"):
        r = row["by condition"][condition]
        assert (r["primary"]["right"], r["primary"]["n"]) == (264, 274)
        assert (r["exploratory"]["right"], r["exploratory"]["n"]) == (270, 274)
        assert r["counted as correct"] == expected
        assert r["still wrong"] == ["1344881875", "181608358"]


@pytest.fixture
def run_copy(tmp_path):
    """The test run's scoring inputs and report, in a folder also named `test`, so its
    taxonomy sheets are the committed ones."""
    out = tmp_path / "test"
    out.mkdir()
    for name in ("manifest.json", "results.jsonl", "attempts.jsonl", "report.json"):
        shutil.copy(RUN / name, out / name)
    return out


@needs_run
def test_the_row_goes_after_the_primary_numbers_and_rewrites_the_same(run_copy):
    amendment3.add_to_report(run_copy)
    once = (run_copy / "report.json").read_text()
    keys = list(json.loads(once))
    assert keys[keys.index("conditions") + 1] == amendment3.KEY
    amendment3.add_to_report(run_copy)
    assert (run_copy / "report.json").read_text() == once


@needs_run
def test_a_stale_report_is_refused(run_copy):
    path = run_copy / "report.json"
    report = json.loads(path.read_text())
    report["conditions"]["baseline"]["accuracy"]["all"]["right"] -= 1
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError, match="doesn't match"):
        amendment3.add_to_report(run_copy)
