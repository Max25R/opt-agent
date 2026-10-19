"""Call the real Claude API, so they cost money (a fraction of a cent each). They're excluded
from the default test run and from CI. Run them all with:  python -m pytest -m live -s
"""

import json

import anthropic
import pytest
from problems import FISHERY
from pytest import approx

from opt_agent.agent import run
from opt_agent.config import get_api_key
from opt_agent.feedback import for_invalid_reply
from opt_agent.formulate import Revision, formulate
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records
from opt_agent.self_correct import MAX_ATTEMPTS, solve_with_revisions
from opt_agent.solver import solve

pytestmark = pytest.mark.live


def claude() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=get_api_key())


def test_fishery_with_the_real_api():
    result = run(FISHERY["document"], claude())
    assert result.formulation.error is None, result.formulation.error
    assert result.verified
    assert result.solution.objective == approx(3000)
    assert result.explanation.unsupported_numbers == [], result.explanation.text


def test_a_revision_request_with_the_real_api():
    """Claude gets a broken "previous reply" plus feedback, and must return a usable model."""
    revision = Revision(
        previous_reply='{"variables": []}',
        feedback=for_invalid_reply("objective: Field required\nconstraints: Field required"),
    )
    f = formulate(FISHERY["document"], claude(), revision=revision)
    assert f.error is None, f.error
    assert solve(f.model).objective == approx(3000)


def test_the_loop_on_a_problem_infeasible_as_written(tmp_path):
    """Checks the loop's mechanics against the real API. Whether Claude rightly stands by an
    infeasible model, or "fixes" it, is what milestone 6 measures; here it's only printed."""
    [ads] = [r for r in load_records(GROUND_TRUTH_DIR / "test.json") if r.id == "-725478241"]
    log = tmp_path / "attempts.jsonl"
    outcome = solve_with_revisions(ads.document, claude(), log_path=log)

    assert 1 <= len(outcome.attempts) <= MAX_ATTEMPTS
    assert outcome.final.solution is not None, outcome.final.formulation.error
    lines = [json.loads(line) for line in log.read_text().splitlines()]
    assert [line["attempt"] for line in lines] == [a.number for a in outcome.attempts]
    print(f"\nstopped: {outcome.stopped}; final status: {outcome.final.solution.status}")
    print(f"flagged revisions: {outcome.flags or 'none'}")
