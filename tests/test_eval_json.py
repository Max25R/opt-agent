"""results/eval.json (scripts/eval_json.py): the same inputs give the same bytes, the
committed file is up to date, and a report without the Amendment 3 row is refused. No API
calls."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


eval_json = _script("eval_json")
amendment3 = _script("amendment3")

pytestmark = pytest.mark.skipif(
    not (eval_json.TEST.exists() and eval_json.PERTURBED.exists()),
    reason="needs the committed test runs",
)


def test_the_same_inputs_give_the_same_bytes():
    once = eval_json.dumps(eval_json.build())
    assert eval_json.dumps(eval_json.build()) == once


def test_the_committed_file_is_up_to_date():
    assert eval_json.OUT.read_text() == eval_json.dumps(eval_json.build()), (
        "results/eval.json is stale: python scripts/eval_json.py"
    )


def test_amendment_4_keeps_the_result_of_record():
    """Its rows sit next to the primary numbers and never replace them."""
    data = json.loads(eval_json.OUT.read_text())
    for condition, rows in data["amendment_4"]["by condition"].items():
        assert rows["result of record"] == data["primary"]["accuracy"][condition]
        assert rows["result of record"]["right"] == 264


def test_it_names_the_amendment_3_row_as_the_script_does():
    assert eval_json.AMENDMENT_3 == amendment3.KEY


def test_a_report_without_the_amendment_3_row_is_refused(tmp_path):
    """A frozen rebuild (python -m opt_agent.report runs/test) drops the row."""
    run = tmp_path / "test"
    run.mkdir()
    report = json.loads((eval_json.TEST / "report.json").read_text())
    del report[eval_json.AMENDMENT_3]
    (run / "report.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="no Amendment 3 row"):
        eval_json.build(test_dir=run)
