from problems import (
    BLEND,
    HIGHS_FREE_VARIABLE_BUG,
    INFEASIBLE,
    INTEGER_INFEASIBLE,
    REDDY_MIKKS,
    WYNDOR,
    unbounded,
)
from pytest import approx, mark
from test_metamorphic import reverse_everything

from opt_agent import highs
from opt_agent.highs import solve_with_highs
from opt_agent.solver import Status
from opt_agent.verify import check_solution


@mark.parametrize(
    ("model", "expected"),
    [(WYNDOR, 36), (BLEND, 24), (REDDY_MIKKS, 20)],
    ids=["wyndor", "blend", "reddy_mikks"],
)
def test_known_answers(model, expected):
    s = solve_with_highs(model)
    assert s.status is Status.OPTIMAL
    assert s.objective == approx(expected)
    assert check_solution(model, s) == []


def test_infeasible():
    assert solve_with_highs(INFEASIBLE).status is Status.INFEASIBLE
    assert solve_with_highs(INTEGER_INFEASIBLE).status is Status.INFEASIBLE


@mark.parametrize("integer", [False, True], ids=["lp", "mip"])
def test_unbounded(integer):
    # For the MIP, HiGHS answers "infeasible or unbounded"; the zero-objective solve decides.
    assert solve_with_highs(unbounded(integer)).status is Status.UNBOUNDED


@mark.parametrize("reverse", [False, True], ids=["as-listed", "reversed"])
def test_regression_highs_false_optimum_in_a_mip(reverse):
    """HiGHS reported "optimal" (-144) for this unbounded MIP when listed in reverse."""
    model = reverse_everything(HIGHS_FREE_VARIABLE_BUG) if reverse else HIGHS_FREE_VARIABLE_BUG
    assert solve_with_highs(model).status is Status.UNBOUNDED


def test_highs_runs_with_a_time_limit_and_reports_hitting_it(monkeypatch):
    """Our problems are too small to make HiGHS slow, so SciPy's status 1 is faked; the
    option must still be passed, so that a hard model can't hang a run."""
    passed = []

    def hits_the_limit(*args, options, **kwargs):
        passed.append(options)
        return type("Result", (), {"status": 1, "x": None, "fun": None})()

    monkeypatch.setattr(highs, "milp", hits_the_limit)
    s = solve_with_highs(WYNDOR)
    assert passed[0]["time_limit"] == highs.HIGHS_TIME_LIMIT_SECONDS
    assert s.status is Status.TIMEOUT and s.failed
    assert s.note == "HiGHS hit its 30 s time limit while solving"
