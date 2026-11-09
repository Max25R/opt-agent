"""CBC that doesn't run to completion (audit, finding 6): PuLP raises PulpSolverError when
CBC exits with an error or writes no solution. That must come back as a loud failure, with
its reason, never as an exception that ends a run and never as an answer. Never calls the
API."""

import pulp
import pytest
from fakes import GAS_PROBLEM, GAS_REPLY, FakeClient
from problems import WYNDOR

from opt_agent import solver
from opt_agent.agent import render, run
from opt_agent.solver import Status, solve


@pytest.fixture
def cbc_crashes(monkeypatch):
    def crash(problem):
        raise pulp.PulpSolverError("Pulp: Error while executing COIN_CMD")

    monkeypatch.setattr(solver, "_run_cbc", crash)


def test_a_cbc_crash_is_an_error_with_its_reason(cbc_crashes):
    s = solve(WYNDOR)
    assert s.status is Status.ERROR and s.failed
    assert "Error while executing COIN_CMD" in s.note
    assert s.objective is None and s.values == {}


def test_a_cbc_crash_is_a_loud_failure_of_the_pipeline(cbc_crashes):
    result = run(GAS_PROBLEM, FakeClient(GAS_REPLY), with_explanation=False, max_attempts=1)
    assert result.outcome.stopped == "solver error"
    assert not result.confirmed and not result.verified
    assert "NO ANSWER" in render(result)
