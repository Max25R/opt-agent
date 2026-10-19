import json

import pytest
from fakes import (
    BAD_EXPLANATION,
    GAS_PROBLEM,
    GAS_REPLY,
    GOOD_EXPLANATION,
    INFEASIBLE_REPLY,
    FakeClient,
    model,
    status_error,
)
from problems import CBC_FREE_VARIABLE_BUG
from pytest import approx

from opt_agent import self_correct
from opt_agent.agent import render, run
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records
from opt_agent.runs import Run, Tags
from opt_agent.solver import Solution, Status


def test_the_demo_problem_is_dev_problem_439170086_verbatim():
    [gas] = [r for r in load_records(GROUND_TRUTH_DIR / "dev.json") if r.id == "439170086"]
    assert GAS_PROBLEM == gas.document
    assert gas.ip.objective == approx(251) and gas.integrality.kind == "integer"


def test_gas_end_to_end():
    client = FakeClient(GAS_REPLY, GOOD_EXPLANATION)
    result = run(GAS_PROBLEM, client)
    assert result.solution.objective == approx(251)
    assert result.solution.values == approx({"pipelines": 83, "trains": 168})
    assert result.verified
    assert result.explanation.text == GOOD_EXPLANATION
    assert result.explanation.unsupported_numbers == []
    assert len(client.requests) == 2  # formulate, then explain


def test_an_unusable_reply_on_every_attempt_never_reaches_the_solver():
    client = FakeClient('{"variables": []}', '{"variables": []}', '{"variables": []}')
    result = run("...", client)
    assert result.outcome.stopped == "attempt limit"
    assert result.formulation.error
    assert result.solution is None and not result.verified
    assert len(client.requests) == 3


def test_an_infeasible_model_claude_stands_by_gets_no_explanation():
    client = FakeClient(INFEASIBLE_REPLY, INFEASIBLE_REPLY)  # revised to the same model
    result = run("...", client)
    assert result.outcome.stopped == "model unchanged"
    assert result.solution.status is Status.INFEASIBLE
    assert result.explanation is None and not result.verified
    assert len(client.requests) == 2


def test_single_shot_makes_one_formulation_call():
    client = FakeClient(INFEASIBLE_REPLY)
    result = run("...", client, max_attempts=1)
    assert result.outcome.stopped == "attempt limit"
    assert len(result.outcome.attempts) == 1 and len(client.requests) == 1


def test_without_an_explanation_there_is_one_call():
    client = FakeClient(GAS_REPLY)
    result = run(GAS_PROBLEM, client, with_explanation=False)
    assert result.verified and result.explanation is None
    assert len(client.requests) == 1


def test_render_shows_the_model_the_answer_and_the_explanation():
    text = render(run(GAS_PROBLEM, FakeClient(GAS_REPLY, GOOD_EXPLANATION)))
    assert "daily gas: 8000*[pipelines] + 2000*[trains] >= 1e+06" in text
    assert "trains at least twice pipelines: 1*[trains] - 2*[pipelines] >= 0" in text
    assert "Objective: 251" in text
    assert GOOD_EXPLANATION in text
    assert "not backed" not in text


def test_render_flags_numbers_the_solver_didnt_produce():
    text = render(run(GAS_PROBLEM, FakeClient(GAS_REPLY, BAD_EXPLANATION)))
    assert "(not backed by the solver's numbers: 249)" in text


def test_render_lists_the_attempts_and_flags():
    fixed = model([("at least 5", ">=", 5)])  # "fixed" by deleting a constraint
    text = render(run("...", FakeClient(INFEASIBLE_REPLY, fixed), with_explanation=False))
    assert "Attempt 1: infeasible" in text and "Attempt 2: optimal" in text
    assert "Stopped: optimal" in text
    assert "flagged revision: deleted constraint 'at most 3'" in text


# CBC's recorded answer for CBC_FREE_VARIABLE_BUG: "optimal" at enormous values, though the
# model is unbounded. c0 is violated by 1, far inside the round-off allowed at that size.
FALSE_OPTIMUM = Solution(
    solver="cbc",
    status=Status.OPTIMAL,
    objective=-6.25e11,
    values={"x0": -5e11, "x1": 6.25e11, "x2": 0.0},
    slacks={"c0": -1.0},
)


@pytest.fixture
def cbc_claims_a_false_optimum(monkeypatch):
    monkeypatch.setattr(self_correct, "solve", lambda model: FALSE_OPTIMUM)
    return CBC_FREE_VARIABLE_BUG.model_dump_json()


def test_a_false_optimum_is_caught_by_the_cross_check_not_by_arithmetic(
    cbc_claims_a_false_optimum,
):
    result = run("...", FakeClient(cbc_claims_a_false_optimum), with_explanation=False)
    assert result.outcome.stopped == "solvers disagree"  # the loop cross-checks: no revision
    assert result.solution.status is Status.OPTIMAL  # CBC's claim is what gets reported
    assert result.check_problems == []  # no duals here, so arithmetic checks only feasibility
    assert result.highs_agrees is False  # HiGHS says unbounded
    assert not result.verified  # so the answer is not verified


def test_an_unverified_answer_is_not_explained(cbc_claims_a_false_optimum):
    client = FakeClient(cbc_claims_a_false_optimum, "An explanation of a wrong answer.")
    result = run("...", client)
    assert result.explanation is None
    assert len(client.requests) == 1  # no explanation call at all


def test_a_solver_disagreement_is_reported_as_such(cbc_claims_a_false_optimum):
    text = render(run("...", FakeClient(cbc_claims_a_false_optimum), with_explanation=False))
    assert "SOLVERS DISAGREE: CBC says optimal (-6.25e+11), HiGHS says unbounded." in text
    assert "No answer is reported." in text
    assert "Objective:" not in text


def test_an_overruled_claim_is_shown():
    """Real CBC on the counterexample: its "optimal" is overruled by an improving ray."""
    result = run("...", FakeClient(CBC_FREE_VARIABLE_BUG.model_dump_json()), max_attempts=1)
    assert result.solution.status is Status.UNBOUNDED and result.highs_agrees
    assert "CBC claimed an optimum, but the objective improves forever" in render(result)


def test_a_time_out_is_shown_as_one_not_as_a_disagreement(monkeypatch):
    timed_out = Solution(
        solver="cbc", status=Status.TIMEOUT, note="CBC hit its 30 s time limit while solving"
    )
    monkeypatch.setattr(self_correct, "solve", lambda model: timed_out)
    text = render(run("...", FakeClient(GAS_REPLY), with_explanation=False))
    assert "Stopped: solver error" in text
    assert "NO ANSWER: CBC hit its 30 s time limit while solving." in text
    assert "DISAGREE" not in text and "Objective:" not in text


def test_an_api_error_is_a_failed_problem_not_a_crash(tmp_path):
    """400 isn't retried. The problem stops, is logged, and counts as a failure."""
    log = tmp_path / "run.jsonl"
    client = FakeClient(status_error(400))
    result = run(GAS_PROBLEM, client, session=Run(log_path=log), tags=Tags(problem_id="p1"))
    assert result.outcome.stopped == "api error"
    assert not result.verified and result.solution is None
    assert "the API call failed: APIStatusError (400)" in render(result)
    attempt, problem = [json.loads(line) for line in log.read_text().splitlines()]
    assert attempt["kind"] == "attempt" and attempt["call"]["error"].startswith("APIStatusError")
    assert problem["kind"] == "problem" and problem["problem_id"] == "p1"
    assert (problem["stopped"], problem["verified"]) == ("api error", False)


def test_an_api_error_after_a_model_keeps_that_model():
    """Attempt 1 is infeasible; the revision call fails. The infeasible model is the answer."""
    client = FakeClient(INFEASIBLE_REPLY, status_error(400))
    result = run("...", client)
    assert result.outcome.stopped == "api error"
    assert result.solution.status is Status.INFEASIBLE


@pytest.mark.parametrize(
    ("reply", "flag"),
    [
        (("", "refusal"), "Claude declined to answer"),
        (("Use 83 pipelines and", "max_tokens"), "the reply was cut off at 16000 tokens"),
        ("", "the reply had no text"),
        (status_error(400), "the API call failed: APIStatusError (400): HTTP 400"),
    ],
    ids=["refused", "truncated", "empty", "failed"],
)
def test_an_unfinished_explanation_is_flagged(reply, flag):
    result = run(GAS_PROBLEM, FakeClient(GAS_REPLY, reply))
    assert result.verified and result.explanation.problem == flag
    assert f"(explanation flagged: {flag})" in render(result)


def test_a_whole_explanation_has_no_flag():
    result = run(GAS_PROBLEM, FakeClient(GAS_REPLY, GOOD_EXPLANATION))
    assert result.explanation.problem is None


def test_wall_time_latency_and_retry_time_are_kept_apart(monkeypatch):
    monkeypatch.setattr("opt_agent.api.time.sleep", lambda s: None)  # don't really wait
    overloaded = status_error(529, {"retry-after": "7"})
    result = run(GAS_PROBLEM, FakeClient(overloaded, GAS_REPLY), with_explanation=False)
    assert result.verified
    [call] = result.calls
    assert call.tries == 2
    assert call.retry_s >= 7  # the wait the server asked for, not counted as latency
    assert result.latency_s < 7 and result.wall_s > 0
    assert "plus 7.0 s retrying" in render(result)


def test_every_line_of_a_run_is_tagged(tmp_path):
    log = tmp_path / "run.jsonl"
    session = Run.start(log_path=log)
    tags = Tags(problem_id="439170086", split="dev", condition="self-correction")
    run(GAS_PROBLEM, FakeClient(GAS_REPLY, GOOD_EXPLANATION), session=session, tags=tags)
    lines = [json.loads(line) for line in log.read_text().splitlines()]
    assert [line["kind"] for line in lines] == ["run", "attempt", "explanation", "problem"]
    assert {line["run_id"] for line in lines} == {session.run_id}
    for line in lines[1:]:
        assert (line["problem_id"], line["split"], line["condition"]) == (
            "439170086", "dev", "self-correction"
        )  # fmt: skip
    explanation = lines[2]
    assert explanation["request"]["system"].startswith("Explain the result")
    assert explanation["reply"] == GOOD_EXPLANATION and explanation["problem"] is None
