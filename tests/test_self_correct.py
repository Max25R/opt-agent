import json

from fakes import FISHERY_REPLY, INFEASIBLE_REPLY, FakeClient, model

from opt_agent.self_correct import SYSTEM_PROMPT_SHA256, solve_with_revisions
from opt_agent.solver import Status

BAD_REPLY = '{"variables": []}'  # not a model: objective and constraints are missing


def requests_sent(client: FakeClient) -> list[str]:
    return [r["messages"][0]["content"] for r in client.requests]


def test_an_optimal_first_attempt_needs_no_revision():
    client = FakeClient(FISHERY_REPLY)
    outcome = solve_with_revisions("the problem", client)
    assert outcome.stopped == "optimal"
    assert len(outcome.attempts) == 1
    assert requests_sent(client) == ["the problem"]  # identical to single-shot


def test_an_unusable_reply_is_sent_back_with_the_error():
    client = FakeClient(BAD_REPLY, FISHERY_REPLY)
    outcome = solve_with_revisions("the problem", client)
    assert outcome.stopped == "optimal"
    assert len(outcome.attempts) == 2
    revision = requests_sent(client)[1]
    assert "<problem>\nthe problem\n</problem>" in revision
    assert f"<previous_model>\n{BAD_REPLY}\n</previous_model>" in revision
    assert "objective: Field required" in revision  # the validator's own words


def test_infeasible_feedback_names_the_conflicting_constraints():
    client = FakeClient(INFEASIBLE_REPLY, model([("at least 5", ">=", 5)]))
    outcome = solve_with_revisions("the problem", client)
    first = outcome.attempts[0]
    assert first.solution.status is Status.INFEASIBLE
    assert "can't all hold at once: 'at least 5', 'at most 3'" in first.feedback
    assert first.feedback in requests_sent(client)[1]


def test_a_fix_that_deletes_a_constraint_is_flagged():
    client = FakeClient(INFEASIBLE_REPLY, model([("at least 5", ">=", 5)]))
    outcome = solve_with_revisions("the problem", client)
    assert outcome.stopped == "optimal"
    assert outcome.flags == ["deleted constraint 'at most 3'"]


def test_returning_the_same_model_ends_the_loop():
    """Claude stands by its model: right for a problem that's infeasible as written."""
    client = FakeClient(INFEASIBLE_REPLY, INFEASIBLE_REPLY)
    outcome = solve_with_revisions("the problem", client)
    assert outcome.stopped == "model unchanged"
    assert outcome.final.solution.status is Status.INFEASIBLE
    assert outcome.flags == []


def test_unbounded_feedback_and_a_legitimate_fix():
    unbounded = model([("at least 1", ">=", 1)], sense="max")
    fixed = model([("at least 1", ">=", 1), ("capacity", "<=", 10)], sense="max")
    outcome = solve_with_revisions("the problem", FakeClient(unbounded, fixed))
    assert "the objective can increase forever" in outcome.attempts[0].feedback
    assert outcome.stopped == "optimal"
    assert outcome.attempts[1].changes.changes == ["added constraint 'capacity'"]
    assert outcome.flags == []  # adding a limit is not loosening


def test_the_loop_stops_after_three_attempts():
    client = FakeClient(BAD_REPLY, BAD_REPLY, BAD_REPLY)
    outcome = solve_with_revisions("the problem", client)
    assert outcome.stopped == "attempt limit"
    assert len(outcome.attempts) == 3 and len(client.requests) == 3
    assert outcome.final.feedback is None  # nothing is sent after the last attempt


def test_single_shot_is_one_attempt():
    outcome = solve_with_revisions("the problem", FakeClient(INFEASIBLE_REPLY), max_attempts=1)
    assert outcome.stopped == "attempt limit"
    assert len(outcome.attempts) == 1


def test_a_refusal_ends_the_loop():
    outcome = solve_with_revisions("the problem", FakeClient(("", "refusal")))
    assert outcome.stopped == "refused"
    assert len(outcome.attempts) == 1


def test_the_answer_is_the_last_usable_model():
    """An unusable last reply doesn't erase the infeasible model found before it."""
    client = FakeClient(INFEASIBLE_REPLY, BAD_REPLY, BAD_REPLY)
    outcome = solve_with_revisions("the problem", client)
    assert outcome.stopped == "attempt limit"
    assert outcome.final.number == 1
    assert outcome.final.solution.status is Status.INFEASIBLE


def test_every_attempt_is_logged(tmp_path):
    log = tmp_path / "logs" / "attempts.jsonl"
    client = FakeClient(INFEASIBLE_REPLY, model([("at least 5", ">=", 5)]))
    outcome = solve_with_revisions("the problem", client, log_path=log)
    first, second = [json.loads(line) for line in log.read_text().splitlines()]
    assert first["run_id"] == second["run_id"] == outcome.run_id
    assert (first["attempt"], first["status"], first["stopped"]) == (1, "infeasible", None)
    assert first["request"] == "the problem" and first["reply"] == INFEASIBLE_REPLY
    assert first["feedback"].startswith("The solver found the model infeasible")
    assert first["system_prompt_sha256"] == SYSTEM_PROMPT_SHA256
    assert first["usage"]["input_tokens"] == 1200
    assert (second["status"], second["objective"], second["stopped"]) == ("optimal", 5.0, "optimal")
    assert second["flags"] == ["deleted constraint 'at most 3'"]
