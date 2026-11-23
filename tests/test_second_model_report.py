"""The second-model study's analysis (docs/SECOND_MODEL_PREREGISTRATION.md, section 4, and
Amendment 1), on fake answers: pairs with Haiku's single-shot sample 0 only; anything but a
right done answer is wrong; the exact McNemar test and the four verdicts; the effect by the
follow-up's methods; silent failures and the rest of the wrong answers; cost and latency per
correct answer; the sensitivity rows; stage 2's comparison and its status; and a report json
can write. Then scripts/reproduce.py's step for this study, on a fake run of both stages on all
121 problems, where LLM4OR's data and the committed freeze are."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from fakes import FakeClient

from opt_agent import followup, followup_freeze, freeze, second_model, second_model_report, stats
from opt_agent.evaluate import Item
from opt_agent.followup_report import bootstrap_ci, bound_pp

report = second_model_report
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("reproduce", ROOT / "scripts" / "reproduce.py")
reproduce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reproduce)


def item(problem: str, objective: float | None = 4.0, *, status: str | None = "optimal",
         outcome: str = "done", sample: int = 0, condition: str = "single-shot",
         model: str = "claude-sonnet-5-5", cost: float = 0.04, latency: float = 10.0,
         reason: str | None = None) -> Item:  # fmt: skip
    return Item(problem_id=problem, split="second-model", condition=condition, outcome=outcome,
                sample=sample, model_id=model, settings_sha256="s",
                status=None if objective is None and status == "optimal" else status,
                objective=objective, cost_usd=cost, latency_s=latency, reason=reason)  # fmt: skip


def haiku(problem: str, objective: float | None = 4.0, sample: int = 0, **more) -> Item:
    return item(problem, objective, sample=sample, model="claude-haiku-5-5", cost=0.002,
                latency=20.0, **more)  # fmt: skip


def problem(pid: str, key: float = 4.0) -> followup.Problem:
    return followup.Problem(id=pid, document="toy", answer=key)


def write(path, items: list[Item], lines: list[dict] = ()) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = [*(i.model_dump(mode="json") for i in items), *lines]
    path.write_text("".join(json.dumps(x) + "\n" for x in entries))


def build(tmp_path, problems, sonnet: list[Item], haikus: list[Item], extra=()) -> dict:
    write(tmp_path / "run" / "results.jsonl", sonnet, extra)
    write(tmp_path / "haiku.jsonl", haikus)
    return report.build(tmp_path / "run", problems, tmp_path / "haiku.jsonl")


def pairs(only_sonnet: int, only_haiku: int, both: int = 5) -> tuple[list, list, list]:
    """Problems, Sonnet's items and Haiku's (samples 0 to 2, all alike), with the given counts
    of problems only one model gets right (a wrong answer is 5.0 against a key of 4.0)."""
    plan = [(4.0, 5.0)] * only_sonnet + [(5.0, 4.0)] * only_haiku + [(4.0, 4.0)] * both
    problems = [problem(f"p{i}") for i in range(len(plan))]
    sonnet = [item(p.id, s) for p, (s, _) in zip(problems, plan, strict=True)]
    haikus = [haiku(p.id, h, sample=k) for p, (_, h) in zip(problems, plan, strict=True)
              for k in (0, 1, 2)]  # fmt: skip
    return problems, sonnet, haikus


# ---- pairs and right answers -------------------------------------------------------------


def test_the_pair_is_haikus_single_shot_sample_0_only(tmp_path):
    problems = [problem("p1")]
    haikus = [haiku("p1", 4.0), haiku("p1", 5.0, sample=1),
              haiku("p1", 5.0, condition="baseline")]  # fmt: skip
    s1 = build(tmp_path, problems, [item("p1", 5.0)], haikus)["s1"]
    assert (s1["sonnet_right"], s1["haiku_right"], s1["only_haiku_right"]) == (0, 1, 1)


def test_anything_but_a_right_done_answer_is_wrong(tmp_path):
    problems = [problem(p) for p in ("loud", "errored", "missing", "right")]
    sonnet = [item("loud", None), item("errored", None, outcome="errored"), item("right", 4.0)]
    data = build(tmp_path, problems, sonnet, [haiku(p.id) for p in problems])
    assert [p["sonnet_right"] for p in data["pairs"]] == [False, False, False, True]
    assert data["s1"]["only_haiku_right"] == 3


# ---- S1 ----------------------------------------------------------------------------------


def test_the_verdict_rule():
    assert report.verdict(12, 1, 0.003, complete=True) == "supported"
    assert report.verdict(1, 12, 0.003, complete=True) == "not supported"
    assert report.verdict(5, 3, 0.73, complete=True) == "inconclusive"
    assert report.verdict(12, 1, 0.003, complete=False) == "incomplete"
    assert set(report.VERDICTS) == {"supported", "not supported", "inconclusive", "incomplete"}


@pytest.mark.parametrize(
    ("only_sonnet", "only_haiku", "verdict"),
    [(12, 1, "supported"), (1, 12, "not supported"), (5, 3, "inconclusive")],
)
def test_s1_is_the_exact_two_sided_mcnemar_test(tmp_path, only_sonnet, only_haiku, verdict):
    problems, sonnet, haikus = pairs(only_sonnet, only_haiku)
    s1 = build(tmp_path, problems, sonnet, haikus)["s1"]
    assert (s1["only_sonnet_right"], s1["only_haiku_right"]) == (only_sonnet, only_haiku)
    assert s1["p_value"] == pytest.approx(stats.mcnemar_exact(only_sonnet, only_haiku))
    assert s1["verdict"] == verdict and s1["alpha"] == 0.05
    assert s1["both_right"] == 5 and s1["both_wrong"] == 0


def test_the_report_holds_python_values_json_can_write(tmp_path):
    """mcnemar_exact returns a numpy float when p < 1 (the resampling study's deviation 1):
    here it's a Python float, and every verdict a str, so json writes the report."""
    problems, sonnet, haikus = pairs(12, 1)
    data = build(tmp_path, problems, sonnet, haikus)
    assert type(data["s1"]["p_value"]) is float and data["s1"]["p_value"] < 0.05
    assert json.loads(report.dumps(data)) == data


def test_the_effect_uses_the_followups_interval_and_rule(tmp_path):
    problems, sonnet, haikus = pairs(6, 2)
    s1 = build(tmp_path, problems, sonnet, haikus)["s1"]
    difference = np.array([1.0] * 6 + [-1.0] * 2 + [0.0] * 5)
    assert s1["difference"] == pytest.approx(4 / 13)
    assert s1["difference_ci95"] == bootstrap_ci(difference)
    assert s1["within_pp"] == bound_pp(s1["difference_ci95"])
    assert s1["sonnet_accuracy"]["value"] == pytest.approx(11 / 13)
    assert s1["haiku_accuracy"]["wilson95"] == list(stats.wilson(7, 13))


def test_a_run_with_a_problem_unsettled_gets_no_verdict(tmp_path):
    problems, sonnet, haikus = pairs(12, 1)
    errored = item(problems[0].id, None, outcome="errored")
    data = build(tmp_path, problems, [errored, *sonnet[1:]], haikus)
    assert data["complete"] is False and data["s1"]["verdict"] == "incomplete"
    # The same error on every allowed pass (Amendment 1) settles it: wrong, and complete.
    data = build(tmp_path, problems, [errored] * 4 + sonnet[1:], haikus)
    assert data["complete"] is True and data["sonnet_errored"] == 1
    missing = build(tmp_path, problems, sonnet[1:], haikus)
    assert missing["s1"]["verdict"] == "incomplete"
    assert missing["sonnet_settled"] == len(problems) - 1


# ---- secondary, descriptive, sensitivity ---------------------------------------------------


def test_silent_failures_and_the_rest_of_the_wrong_answers(tmp_path):
    problems = [problem(p) for p in ("right", "silent", "verdict", "cut", "missing")]
    sonnet = [item("right", 4.0), item("silent", 5.0),
              item("verdict", None, status="infeasible"),
              item("cut", None, reason="the reply was cut off at max_tokens")]  # fmt: skip
    failures = build(tmp_path, problems, sonnet, [haiku(p.id) for p in problems])["failures"]
    s = failures["sonnet"]
    assert (s["verified"], s["silent"]["k"], s["silent"]["n"]) == (2, 1, 5)
    assert (s["silent_of_verified"]["k"], s["silent_of_verified"]["n"]) == (1, 2)
    assert (s["wrong_verdicts"], s["loud"], s["cut_off"], s["errored_or_missing"]) == (1, 2, 1, 1)
    assert failures["haiku"]["silent"]["k"] == 0 and failures["haiku"]["verified"] == 5


def test_cost_and_latency_per_correct_answer(tmp_path):
    problems, sonnet, haikus = pairs(2, 1, both=1)  # Sonnet right on 3, Haiku on 2, of 4
    spend = build(tmp_path, problems, sonnet, haikus)["spend"]
    assert spend["sonnet"]["cost_per_right_answer_usd"] == pytest.approx(4 * 0.04 / 3)
    assert spend["sonnet"]["latency_per_right_answer_s"] == pytest.approx(4 * 10.0 / 3)
    assert spend["haiku"]["cost_per_right_answer_usd"] == pytest.approx(4 * 0.002 / 2)
    assert spend["haiku"]["median_latency_s"] == 20.0 and spend["haiku"]["answers"] == 4


def test_sensitivity_compares_with_haikus_other_samples(tmp_path):
    problems = [problem(f"p{i}") for i in range(3)]
    haikus = [haiku(p.id, 5.0) for p in problems]  # sample 0: all wrong
    haikus += [haiku(p.id, 4.0, sample=1) for p in problems]  # sample 1: all right
    haikus += [haiku(p.id, 4.0 if p.id == "p0" else 5.0, sample=2) for p in problems]
    rows = build(tmp_path, problems, [item(p.id) for p in problems], haikus)["sensitivity"]
    assert (rows["haiku_sample_1"]["haiku_right"], rows["haiku_sample_2"]["haiku_right"]) == (3, 1)
    assert rows["haiku_sample_1"]["only_sonnet_right"] == 0
    assert rows["haiku_mean_accuracy"] == pytest.approx(4 / 9)


def test_the_command_writes_the_results_file(tmp_path, monkeypatch):
    problems, sonnet, _ = pairs(2, 0, both=0)
    write(tmp_path / "run" / "results.jsonl", sonnet)
    monkeypatch.setattr(second_model, "inputs", lambda tag=True: (problems, "test"))
    monkeypatch.setattr(report, "RESULTS", tmp_path / "out" / "second_model.json")
    report.main([str(tmp_path / "run")])
    data = json.loads((tmp_path / "out" / "second_model.json").read_text())
    assert data["s1"]["sonnet_right"] == 2 and data["haiku_record"]["sample"] == 0


# ---- scripts/reproduce.py's step for this study ---------------------------------------------


def test_reproduce_has_nothing_to_rebuild_before_the_run(tmp_path):
    assert reproduce.second_model(tmp_path, replay=True, run=tmp_path / "no-run") == ({}, [])


def test_reproduce_rebuilds_a_fake_run_in_the_frozen_tree(tmp_path):
    """The whole path the owner's run will take, on a fake run of both stages on all 121
    problems (FakeClient, no API): scripts/reproduce.py extracts the study's tree (its tag's,
    or HEAD's before the tag exists), replays both stages there from the run's cache through
    scripts/replay_run.py, and the frozen analysis's report there is this one, byte for byte."""
    from opt_agent import second_model_freeze
    from opt_agent.runs import git

    if not all(p.exists() for p in followup_freeze.data_files()):
        pytest.skip("needs LLM4OR's data (python scripts/fetch_llm4or.py)")
    ref = second_model_freeze.FREEZE_TAG if second_model_freeze.tag_exists() else "HEAD"
    committed = git("show", f"{ref}:docs/second_model/FREEZE-2.json")
    if committed is None:
        pytest.skip("needs Amendment 1's freeze committed (docs/second_model/FREEZE-2.json)")
    approval = second_model_freeze.SecondModelApproval.model_validate_json(committed)
    records = second_model_freeze.problems()
    model = json.dumps({
        "variables": [{"name": "x", "lower": 0, "upper": None, "integer": False}],
        "objective": {"sense": "max", "terms": [{"var": "x", "coef": 1}]},
        "constraints": [{"name": "cap", "terms": [{"var": "x", "coef": 1}], "sense": "<=",
                         "rhs": 4}],
    })  # fmt: skip
    direct = json.dumps({"status": "optimal", "objective": 4.0})
    run, digest = tmp_path / "second-model", freeze.digest(approval.fingerprint)
    for stage, reply in zip(second_model.STAGES, (model, direct), strict=True):
        second_model.run(FakeClient(*[reply] * len(records)), run, records, digest, stage)
    files, differences = reproduce.second_model(tmp_path / "work", replay=True, run=run, tag=ref)
    assert differences == []
    expected = report.dumps(report.build(run, records))
    assert files == {"results/second_model.json": expected.encode()}
    assert json.loads(expected)["stage_2"]["status"] == "complete"


# ---- stage 2 (Amendment 1) ----------------------------------------------------------------


def stage_2_case(tmp_path, sonnet_base: list[Item], extra=()) -> dict:
    """Three problems: Sonnet single-shot right on p0 and p1; Haiku single-shot right on p0,
    its no-solver answer on p1; Sonnet's no-solver answers as given."""
    problems = [problem(f"p{i}") for i in range(3)]
    sonnet = [item("p0"), item("p1"), item("p2", 5.0), *sonnet_base]
    haikus = [haiku("p0"), haiku("p1", 5.0), haiku("p2", 5.0),
              haiku("p0", 5.0, condition="baseline"), haiku("p1", condition="baseline"),
              haiku("p2", 5.0, condition="baseline")]  # fmt: skip
    return build(tmp_path, problems, sonnet, haikus, extra)["stage_2"]


def base(problem_id: str, objective: float | None = 4.0, **more) -> Item:
    return item(problem_id, objective, condition="baseline", cost=0.03, **more)


def test_stage_2_compares_single_shot_with_no_solver_for_each_model(tmp_path):
    two = stage_2_case(tmp_path, [base("p0", 5.0), base("p1", 5.0), base("p2")])
    assert two["status"] == "complete" and two["settled"] == 3
    s = two["sonnet"]
    assert (s["single_shot_right"], s["no_solver_right"]) == (2, 1)
    assert (s["only_single_shot_right"], s["only_no_solver_right"]) == (2, 1)
    assert s["p_value"] == pytest.approx(stats.mcnemar_exact(2, 1))
    assert s["difference"] == pytest.approx(1 / 3) and "verdict" not in s
    h = two["haiku"]  # context, from Haiku's record: single-shot on p0, no-solver on p1
    assert (h["only_single_shot_right"], h["only_no_solver_right"]) == (1, 1)
    assert two["spend"]["sonnet"]["cost_usd"] == pytest.approx(0.09)


def test_stage_2_cut_short_is_incomplete_and_leaves_s1_alone(tmp_path):
    two = stage_2_case(tmp_path, [base("p0"), base("p1", None, outcome="errored")])
    assert (two["status"], two["settled"], two["sonnet"]) == ("incomplete", 1, None)
    assert two["haiku"]["no_solver_right"] == 1  # Haiku's context is there either way
    assert two["spend"]["sonnet"]["answers"] == 2


def test_stage_2_not_started_when_stage_1_was_not_complete(tmp_path):
    problems = [problem("p0"), problem("p1")]
    data = build(tmp_path, problems, [item("p0")], [haiku("p0"), haiku("p1")])
    assert data["s1"]["verdict"] == "incomplete"
    assert data["stage_2"]["status"] == "not started" and data["stage_2"]["sonnet"] is None


def test_stage_2s_answers_never_count_as_stage_1s(tmp_path):
    """The conditions are kept apart: a no-solver answer doesn't settle or answer stage 1."""
    problems = [problem("p0")]
    data = build(tmp_path, problems, [base("p0")], [haiku("p0")])
    assert data["complete"] is False and data["s1"]["sonnet_right"] == 0
