"""The evaluation runner: what it records, resuming, and stopping. Never calls the API."""

import json

import pytest
from fakes import GAS_MODEL, GAS_REPLY, INFEASIBLE_REPLY, FakeClient, model, status_error
from pytest import approx

from opt_agent import api, evaluate
from opt_agent.api import RunStopped
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.evaluate import CONDITIONS, done_pairs, latest_items, worst_case_plan
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records
from opt_agent.scoring import score

DEV = {r.id: r for r in load_records(GROUND_TRUTH_DIR / "dev.json")}
GAS = DEV["439170086"]  # integer optimum 251
LOTION = DEV["-1028228232"]  # infeasible as written
FAKE_CALL_USD = (1200 * 0.10 + 300 * 0.50) / 1e6
CONTINUOUS_GAS = json.dumps({**GAS_MODEL, "variables": [
    {**v, "integer": False} for v in GAS_MODEL["variables"]]})  # fmt: skip


def says(status: str, objective: float | None = None) -> str:
    return json.dumps({"status": status, "objective": objective})


def run(out, *replies, records=(GAS,), conditions=CONDITIONS, cap=1.00):
    client = BudgetedClient(FakeClient(*replies), Budget(cap, out / "spend.jsonl"))
    return evaluate.evaluate(list(records), conditions, client, out)


def correct(item) -> bool:
    return score(DEV[item.problem_id], item.status, item.objective).correct


def lines(path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(api.time, "sleep", lambda s: None)


def test_all_three_conditions_on_one_problem(tmp_path):
    """Self-correction's first attempt replays single-shot's reply, so it isn't paid again."""
    items = run(tmp_path, says("optimal", 251), GAS_REPLY)  # only two calls
    assert [i.condition for i in items] == list(CONDITIONS)
    assert [(i.status, i.objective) for i in items] == [("optimal", 251)] * 3
    assert all(correct(i) and i.no_answer is None for i in items)
    baseline, single, selfc = items
    assert selfc.cached_calls == 1 and selfc.paid_usd == 0
    assert selfc.cost_usd == approx(single.cost_usd) == approx(FAKE_CALL_USD)
    assert sum(i.paid_usd for i in items) == approx(2 * FAKE_CALL_USD)
    assert Budget(1.00, tmp_path / "spend.jsonl").calls == 2


def test_an_item_records_the_answer_not_a_verdict(tmp_path):
    [item] = run(tmp_path, says("optimal", 250), conditions=("baseline",))
    entry = lines(tmp_path / "results.jsonl")[0]
    assert "correct" not in entry and entry["status"] == "optimal"  # scored later, by report.py
    assert item.run_id and item.wall_s >= 0 and item.retry_s == 0


def test_a_finished_run_resumes_to_nothing(tmp_path):
    run(tmp_path, says("optimal", 251), GAS_REPLY)
    assert run(tmp_path) == []  # FakeClient() fails on any call
    assert len(latest_items(tmp_path / "results.jsonl")) == 3


def test_an_api_error_is_logged_as_errored_then_retried_in_a_later_pass(tmp_path):
    [item] = run(tmp_path, status_error(400), conditions=("baseline",))
    assert item.outcome == "errored" and item.status is None and "400" in item.reason
    assert done_pairs(tmp_path / "results.jsonl", item.model_id) == set()
    [again] = run(tmp_path, says("optimal", 251), conditions=("baseline",))
    assert again.outcome == "done" and correct(again)
    assert again.run_id != item.run_id  # two passes
    [latest] = latest_items(tmp_path / "results.jsonl")
    assert latest == again  # the done line replaces the errored one


def test_an_api_error_inside_the_loop_is_errored_too(tmp_path):
    [item] = run(tmp_path, INFEASIBLE_REPLY, status_error(400), conditions=("self-correction",))
    assert item.outcome == "errored" and item.attempts == 2


def test_the_budget_stops_the_run_cleanly_and_a_bigger_cap_resumes_it(tmp_path):
    with pytest.raises(RunStopped, match="could cost up to"):
        run(tmp_path, says("optimal", 251), cap=0.001)
    [stopped] = lines(tmp_path / "results.jsonl")
    assert stopped["kind"] == "stopped" and "cap" in stopped["reason"]
    items = run(tmp_path, says("optimal", 251), GAS_REPLY, cap=1.00)
    assert len(items) == 3


def test_errors_in_a_row_stop_the_run(tmp_path):
    with pytest.raises(RunStopped, match="3 API errors in a row"):
        run(tmp_path, *[status_error(400)] * 3)
    assert [x["kind"] for x in lines(tmp_path / "results.jsonl")] == ["item"] * 3 + ["stopped"]


def test_a_confirmed_answer_is_kept_even_when_wrong(tmp_path):
    [wrong] = run(tmp_path, CONTINUOUS_GAS, conditions=("single-shot",))
    assert (wrong.status, wrong.objective) == ("optimal", approx(250))  # the LP optimum
    assert score(GAS, wrong.status, wrong.objective).failure == "silent"


def test_no_answer_says_what_kind_of_failure_it_was(tmp_path):
    [unusable] = run(tmp_path / "a", '{"variables": []}', conditions=("single-shot",))
    assert unusable.status is None and unusable.no_answer == "unusable reply"
    assert "no usable model" in unusable.reason
    [refused] = run(tmp_path / "b", ("", "refusal"), conditions=("single-shot",))
    assert refused.no_answer == "refusal"
    [cut] = run(tmp_path / "c", ('{"status": "opt', "max_tokens"), conditions=("baseline",))
    assert cut.no_answer == "unusable reply" and "cut off" in cut.reason
    [declined] = run(tmp_path / "d", ("", "refusal"), conditions=("baseline",))
    assert declined.no_answer == "refusal"


def test_a_revision_that_drops_a_constraint_is_flagged(tmp_path):
    dropped = model([("at least 5", ">=", 5)])  # "at most 3" is gone, so it's feasible
    [item] = run(tmp_path, INFEASIBLE_REPLY, dropped, records=[LOTION],
                 conditions=("self-correction",))  # fmt: skip
    assert item.status == "optimal" and item.attempts == 2
    assert any("at most 3" in flag for flag in item.flags)


def test_standing_by_an_infeasible_model_is_right_for_an_infeasible_problem(tmp_path):
    items = run(tmp_path, says("infeasible"), INFEASIBLE_REPLY, INFEASIBLE_REPLY, records=[LOTION])
    assert all(correct(i) for i in items)
    assert items[2].attempts == 2 and items[2].reason == "model unchanged"


def test_results_from_another_prompt_version_are_never_mixed(tmp_path):
    run(tmp_path, says("optimal", 251), conditions=("baseline",))
    path = tmp_path / "results.jsonl"
    [entry] = lines(path)
    path.write_text(json.dumps({**entry, "settings_sha256": "000000000000"}) + "\n")
    with pytest.raises(ValueError, match="another model or prompt version"):
        done_pairs(path, entry["model_id"])


def test_a_resume_must_repeat_the_same_experiment(tmp_path):
    run(tmp_path, says("optimal", 251), conditions=("baseline",))
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["problem_ids"] == [GAS.id] and manifest["conditions"] == ["baseline"]
    with pytest.raises(ValueError, match="different problem_ids"):
        run(tmp_path, records=[GAS, LOTION], conditions=("baseline",))
    with pytest.raises(ValueError, match="different conditions"):
        run(tmp_path, conditions=CONDITIONS)


def test_the_plan_counts_the_most_paid_calls(tmp_path):
    calls, usd = worst_case_plan([GAS, LOTION], CONDITIONS, set(), "claude-haiku-5-5")
    assert calls == 2 * (1 + 1 + 2)  # self-correction's first attempt is single-shot's
    assert 0 < usd < calls * 0.01


def test_the_command_line_plans_without_a_key(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    evaluate.main([GAS.id, "--out", str(tmp_path), "--plan"])
    assert "3 pairs pending: at most 4 paid calls" in capsys.readouterr().out
    assert not (tmp_path / "manifest.json").exists()  # a plan writes nothing
    with pytest.raises(SystemExit, match="not scorable"):
        evaluate.main(["no-such-problem", "--out", str(tmp_path), "--plan"])


def test_the_perturbed_dev_split_runs_and_the_test_splits_wait(tmp_path, capsys):
    evaluate.main([GAS.id, "--split", "dev-perturbed", "--out", str(tmp_path), "--plan"])
    assert "3 pairs pending" in capsys.readouterr().out
    for split in ("test", "test-perturbed"):
        with pytest.raises(SystemExit):
            evaluate.main([GAS.id, "--split", split, "--out", str(tmp_path), "--plan"])
