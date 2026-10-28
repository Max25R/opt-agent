"""Call the real Claude API, so they cost money (a fraction of a cent each). They're excluded
from the default test run and from CI. Run them all with:  python -m pytest -m live -s

Every call goes through a budget guard (budget.py) whose ledger is git-ignored and counts
every run of these tests: one run makes 4 to 8 calls, and the guard refuses any call that
could take the total past LIVE_CAP_USD.

Every problem here is from the dev split: nothing an agent was tuned on may be scored.
"""

import json

import anthropic
import pytest
from fakes import GAS_PROBLEM
from pytest import approx

from opt_agent.agent import run
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.config import get_api_key
from opt_agent.feedback import for_invalid_reply
from opt_agent.formulate import Revision, formulate
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records
from opt_agent.runs import REPO_ROOT, Run
from opt_agent.self_correct import MAX_ATTEMPTS, solve_with_revisions
from opt_agent.solver import solve

pytestmark = pytest.mark.live

LIVE_CAP_USD = 0.25
LEDGER = REPO_ROOT / "logs" / "spend" / "live-tests.jsonl"


def claude() -> BudgetedClient:
    return BudgetedClient(anthropic.Anthropic(api_key=get_api_key()), Budget(LIVE_CAP_USD, LEDGER))


def test_the_gas_problem_with_the_real_api():
    """Dev 439170086. 250 instead of 251 would mean Claude made pipelines and trains
    continuous; the system prompt says countable things are integers."""
    result = run(GAS_PROBLEM, claude())
    assert result.formulation.error is None, result.formulation.error
    assert result.verified
    assert result.solution.objective == approx(251)
    assert result.explanation.problem is None, result.explanation.problem
    assert result.explanation.unsupported_numbers == [], result.explanation.text


def test_a_revision_request_with_the_real_api():
    """Claude gets a broken "previous reply" plus feedback, and must return a usable model."""
    revision = Revision(
        previous_reply='{"variables": []}',
        feedback=for_invalid_reply("objective: Field required\nconstraints: Field required"),
    )
    f = formulate(GAS_PROBLEM, claude(), revision=revision)
    assert f.error is None, f.error
    assert solve(f.model).objective == approx(251)


def test_the_loop_on_a_problem_infeasible_as_written(tmp_path):
    """Checks the loop's mechanics against the real API. Whether Claude rightly stands by an
    infeasible model, or "fixes" it, is what milestone 6 measures; here it's only printed."""
    [lotion] = [r for r in load_records(GROUND_TRUTH_DIR / "dev.json") if r.id == "-1028228232"]
    log = tmp_path / "attempts.jsonl"
    session = Run.start(log_path=log)
    outcome = solve_with_revisions(lotion.document, claude(), session=session)

    assert 1 <= len(outcome.attempts) <= MAX_ATTEMPTS
    assert outcome.final.solution is not None, outcome.final.formulation.error
    lines = [json.loads(line) for line in log.read_text().splitlines()]
    assert lines[0]["kind"] == "run" and lines[0]["git_sha"]
    assert [line["attempt"] for line in lines[1:]] == [a.number for a in outcome.attempts]
    print(f"\nstopped: {outcome.stopped}; final status: {outcome.final.solution.status}")
    print(f"flagged revisions: {outcome.flags or 'none'}")
