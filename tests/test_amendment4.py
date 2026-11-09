"""Amendment 4's rows (scripts/amendment4.py): the corrected-labels row covers exactly the
problems its criterion picks, reproduces the run's numbers, and never turns a right answer
wrong; the pre-registered rows are the frozen report's; 264/274 stays the result of record.
No API calls."""

import importlib.util
import json
from pathlib import Path

import pytest

from opt_agent.ground_truth import GROUND_TRUTH_DIR, answer, load_records, matching_reading
from opt_agent.run_results import load
from opt_agent.solver import Status

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "test"
spec = importlib.util.spec_from_file_location("amendment4", ROOT / "scripts" / "amendment4.py")
amendment4 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(amendment4)

needs_run = pytest.mark.skipif(not RUN.exists(), reason="needs the committed test run")


@pytest.fixture(scope="module")
def test_records():
    return load_records(GROUND_TRUTH_DIR / "test.json")


@pytest.fixture(scope="module")
def row():
    return amendment4.row(load(RUN), json.loads((RUN / "report.json").read_text()))


def test_the_criterion_picks_exactly_the_corrected_problems(test_records):
    assert amendment4.rule_continuous_with_strict_wording(test_records) == sorted(
        amendment4.CORRECTED
    )


def test_a_corrected_label_brings_the_strict_reading(test_records):
    record = next(r for r in test_records if r.id == "431521997")
    assert record.strict is None  # switched off by the continuous label
    fixed = amendment4.corrected(record, "integer")
    assert fixed.integrality.kind == "integer"
    assert fixed.strict.ip.status is Status.OPTIMAL and fixed.strict.ip.objective == 36
    # The annotated answer is unchanged, and the strict one is now accepted too.
    assert answer(fixed).objective == answer(record).objective == 0
    assert matching_reading(record, Status.OPTIMAL, 36.0) is None
    assert matching_reading(fixed, Status.OPTIMAL, 36.0) == "strict"
    assert matching_reading(fixed, Status.OPTIMAL, 0.0) == "annotated"


def test_a_record_without_strict_wording_is_refused(test_records):
    plain = next(r for r in test_records if r.model is not None and not r.strict and
                 not amendment4.strict_constraints(r.notes))  # fmt: skip
    with pytest.raises(ValueError, match="no strict wording"):
        amendment4.corrected(plain, "integer")


@needs_run
def test_the_rows_reproduce_the_test_run(row):
    for condition in ("baseline", "single-shot", "self-correction"):
        r = row["by condition"][condition]
        assert (r["result of record"]["right"], r["result of record"]["n"]) == (264, 274)
        assert (r["corrected labels"]["right"], r["corrected labels"]["n"]) == (268, 274)
        assert r["counted as correct"] == sorted(amendment4.CORRECTED)
        assert (r["without disputed reviews"]["right"], r["without disputed reviews"]["n"]) == (
            260,
            266,
        )
    lenient = {c: r["lenient"]["right"] for c, r in row["by condition"].items()}
    assert lenient == {"baseline": 264, "single-shot": 266, "self-correction": 266}


@needs_run
def test_the_pre_registered_rows_are_the_frozen_reports(row):
    report = json.loads((RUN / "report.json").read_text())
    for c, r in row["by condition"].items():
        mine = report["conditions"][c]
        assert r["result of record"] == mine["accuracy"]["all"]
        assert r["lenient"] == mine["lenient accuracy"]["all"]
        assert r["without disputed reviews"] == mine["accuracy without disputed reviews"]["all"]


@needs_run
def test_the_operator_errors_are_listed_but_not_corrected(row):
    listed = {e["problem_id"]: e for e in row["key errors"]}
    assert list(listed) == list(amendment4.KEY_ERRORS)
    for problem in ("-926961422", "-2138755435"):
        assert listed[problem]["kind"] == "annotated operator"
        assert not listed[problem]["corrected here"]
        for r in row["by condition"].values():
            assert problem not in r["counted as correct"]


@needs_run
def test_a_criterion_that_disagrees_with_the_list_is_refused(monkeypatch):
    monkeypatch.setitem(amendment4.CORRECTED, "1151835649", "integer")
    with pytest.raises(ValueError, match="the criterion picks"):
        amendment4.row(load(RUN), json.loads((RUN / "report.json").read_text()))


@needs_run
def test_a_label_that_breaks_a_right_answer_is_refused(monkeypatch):
    """A correction must only add accepted answers. A stub correction that accepts nothing,
    applied to a problem every condition got right (`1151835649`), is refused."""
    run = load(RUN)
    report = json.loads((RUN / "report.json").read_text())

    def accepting_nothing(record, kind):
        return record.model_copy(update={"lp": None, "ip": None, "strict": None})

    monkeypatch.setattr(amendment4, "corrected", accepting_nothing)
    monkeypatch.setitem(amendment4.CORRECTED, "1151835649", "integer")
    monkeypatch.setattr(amendment4, "rule_continuous_with_strict_wording",
                        lambda records: sorted(amendment4.CORRECTED))  # fmt: skip
    with pytest.raises(ValueError, match="turn right answers wrong"):
        amendment4.row(run, report)
