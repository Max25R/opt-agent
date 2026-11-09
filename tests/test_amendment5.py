"""Amendment 5's rows (scripts/amendment5.py): the frozen answers against LLM4OR's cleaned
NL4Opt key. The data is git-ignored (docs/EXTERNAL_DATA.md), so the tests that read it skip
without it, as in CI; there, eval_json.py keeps the committed block, which a test here
checks. 264/274 stays the result of record. No API calls."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

from opt_agent.run_results import load

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "test"
EVAL = ROOT / "results" / "eval.json"


def _script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


amendment5 = _script("amendment5")
eval_json = _script("eval_json")

needs_data = pytest.mark.skipif(
    not (amendment5.available() and RUN.exists()),
    reason="needs LLM4OR's cleaned NL4Opt (docs/EXTERNAL_DATA.md) and the test run",
)


@pytest.fixture(scope="module")
def row():
    return json.loads(eval_json.dumps(amendment5.row(load(RUN))))


@pytest.mark.parametrize(
    ("status", "objective", "theirs", "matches"),
    [
        ("optimal", 33.5, 33, False),  # a truncated key isn't matched
        ("optimal", 100.004, 100, True),  # within 1e-4 relative
        ("optimal", 100.02, 100, False),
        ("infeasible", None, None, True),  # their null: no optimum
        ("optimal", 1.0, None, False),
        (None, None, 5.0, False),  # no answer
    ],
)
def test_an_answer_matches_their_key_by_status_and_1e_4(status, objective, theirs, matches):
    assert amendment5.matches_llm4or(status, objective, theirs) is matches


@needs_data
def test_the_committed_rows_are_the_datas(row):
    assert json.loads(EVAL.read_text())["amendment_5"] == row


@needs_data
def test_every_cleaned_problem_matches_one_of_ours_exactly(row):
    o = row["overlap"]
    assert (o["cleaned problems"], o["matched exactly"], o["scorable"]) == (214, 214, 210)


@needs_data
def test_the_rows_and_their_misses_add_up(row):
    for r in row["by condition"].values():
        assert (r["LLM4OR key"]["right"], r["LLM4OR key"]["n"]) == (185, 210)
        missed = sum(r["wrong against the LLM4OR key"].values())
        assert missed == r["LLM4OR key"]["n"] - r["LLM4OR key"]["right"]
    ours = {c: r["our frozen key"]["right"] for c, r in row["by condition"].items()}
    assert ours == {"baseline": 206, "single-shot": 205, "self-correction": 205}


@needs_data
def test_amendment_4s_errors(row):
    errors = row["amendment 4 key errors"]
    assert errors["removed by LLM4OR"] == [
        "431521997", "1605420061", "2078392466", "-926961422", "-2138755435"
    ]  # fmt: skip
    (kept,) = errors["kept"]
    assert kept["problem_id"] == "-1540907330"
    assert (kept["LLM4OR key"], kept["our frozen key"]) == (0, 0)
    assert kept["corrected label also accepts"] == 17
    assert kept["LLM4OR key agrees with"] == "our frozen key"


@needs_data
def test_on_the_differing_keys_every_condition_matched_ours_but_one(row):
    d = row["differing keys"]
    assert d["n"] == 14 and d["kinds"] == {"disagrees": 9, "other integrality": 5}
    assert d["each condition matched"] == {
        "baseline": {"our key": 13, "the LLM4OR key": 0, "neither": 1},
        "single-shot": {"our key": 14, "the LLM4OR key": 0, "neither": 0},
        "self-correction": {"our key": 14, "the LLM4OR key": 0, "neither": 0},
    }
    (exception,) = [x for x in d["items"] if x["matched"]["baseline"] != "our key"]
    assert exception["problem_id"] == "-38093970" and exception["answers"]["baseline"] == 35


@needs_data
def test_a_copy_that_isnt_the_recorded_one_is_refused(tmp_path):
    copy = tmp_path / "llm4or-clean"
    shutil.copytree(amendment5.DATA / "NL4Opt", copy / "NL4Opt")
    (copy / "NL4Opt" / "prob_1" / "sample.json").write_text('[{"output": [1]}]')
    with pytest.raises(ValueError, match="isn't the copy"):
        amendment5.load_llm4or(copy)


def test_without_the_data_eval_json_keeps_the_committed_block(monkeypatch):
    """As in CI: the data is never committed, so the block is carried over unchanged."""
    monkeypatch.setattr(eval_json.amendment5, "available", lambda data=None: False)
    built = json.loads(eval_json.dumps(eval_json.build()))
    assert built["amendment_5"] == json.loads(EVAL.read_text())["amendment_5"]


def test_the_result_of_record_is_unchanged():
    data = json.loads(EVAL.read_text())
    assert "264/274" in data["amendment_5"]["result of record"]
    assert {c: r["right"] for c, r in data["primary"]["accuracy"].items()} == {
        "baseline": 264, "single-shot": 264, "self-correction": 264
    }  # fmt: skip
