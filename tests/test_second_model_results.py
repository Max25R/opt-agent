"""docs/second_model/RESULTS.md (scripts/second_model_results.py): rendered from
results/second_model.json alone, the frozen analysis's report, which scripts/reproduce.py
rebuilds byte for byte from the tag (CI's reproduce job). The README's and RESULTS.md's numbers
are checked against the JSON in test_readme_numbers.py; here, that RESULTS.md is the rendering
of the committed JSON, and that the committed verdicts follow section 4's rule. No API calls,
and nothing here needs the data."""

import copy
import importlib.util
import json
from pathlib import Path

import pytest

from opt_agent import second_model_report, stats

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "second_model_results.py"
spec = importlib.util.spec_from_file_location("second_model_results", SCRIPT)
results = importlib.util.module_from_spec(spec)
spec.loader.exec_module(results)


@pytest.fixture(scope="module")
def committed() -> dict:
    return json.loads(results.JSON.read_text())


def test_results_md_is_rendered_from_the_committed_json(committed):
    assert results.render(committed) == results.RESULTS_MD.read_text()


def test_s1s_verdict_follows_section_4(committed):
    s1 = committed["s1"]
    assert s1["p_value"] == stats.mcnemar_exact(s1["only_sonnet_right"], s1["only_haiku_right"])
    assert s1["verdict"] == second_model_report.verdict(
        s1["only_sonnet_right"], s1["only_haiku_right"], s1["p_value"], committed["complete"]
    )
    assert committed["complete"] and committed["sonnet_settled"] == committed["problems"]
    table = (s1["both_right"], s1["only_sonnet_right"], s1["only_haiku_right"], s1["both_wrong"])
    assert sum(table) == s1["problems"] == committed["problems"]
    # "no difference larger than X points": the smallest whole X the interval fits inside
    assert all(abs(100 * end) <= s1["within_pp"] for end in s1["difference_ci95"])
    assert any(abs(100 * end) > s1["within_pp"] - 1 for end in s1["difference_ci95"])


def test_stage_2_ran_only_after_stage_1_and_has_no_verdict(committed):
    two = committed["stage_2"]
    assert two["status"] == "complete" and two["settled"] == committed["problems"]
    for model in ("sonnet", "haiku"):
        row = two[model]
        assert "verdict" not in row
        assert row["p_value"] == stats.mcnemar_exact(row["only_single_shot_right"],
                                                     row["only_no_solver_right"])  # fmt: skip


def test_each_verdict_reads_as_its_rule(committed):
    """The renderer states the rule for whatever verdict the analysis gave."""
    rules = {"supported": "and Sonnet got more", "not supported": "and Haiku",
             "inconclusive": "at least alpha", "incomplete": "no verdict"}  # fmt: skip
    for verdict, words in rules.items():
        data = copy.deepcopy(committed)
        data["s1"]["verdict"] = verdict
        assert words in results.render(data)


def test_a_stage_2_that_didnt_finish_is_said_so(committed):
    data = copy.deepcopy(committed)
    data["stage_2"].update(status="incomplete", settled=40, sonnet=None)
    text = results.render(data)
    assert "Stage 2 is **incomplete**: it settled 40 of the 121 problems" in text
    assert "Sonnet's no-solver accuracy" not in text
