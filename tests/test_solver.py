from problems import (
    BLEND,
    CBC_PREPROCESS_BUG,
    HARD_INTEGER_INFEASIBLE,
    INFEASIBLE,
    INTEGER_INFEASIBLE,
    REDDY_MIKKS,
    WYNDOR,
    unbounded,
)
from pytest import approx, mark

from opt_agent import solver
from opt_agent.highs import solve_with_highs
from opt_agent.schema import LPModel
from opt_agent.solver import Status, solve
from opt_agent.verify import check_solution


def test_wyndor_known_answer():
    s = solve(WYNDOR)
    assert s.status is Status.OPTIMAL
    assert s.objective == approx(36)
    assert s.values == approx({"doors": 2, "windows": 6})
    assert s.slacks == approx({"plant_1_hours": 2, "plant_2_hours": 0, "plant_3_hours": 0})
    assert s.duals == approx({"plant_1_hours": 0, "plant_2_hours": 1.5, "plant_3_hours": 1})
    assert check_solution(WYNDOR, s) == []


def test_blend_known_answer():
    s = solve(BLEND)
    assert s.status is Status.OPTIMAL
    assert s.objective == approx(24)
    assert s.values == approx({"grain": 6, "protein": 4})
    assert s.duals == approx({"demand": 2.5, "recipe": -0.5})
    assert check_solution(BLEND, s) == []


def test_reddy_mikks_integer_optimum_is_not_the_rounded_lp_optimum():
    integer = solve(REDDY_MIKKS)
    assert integer.status is Status.OPTIMAL
    assert integer.objective == approx(20)
    assert integer.values == approx({"exterior": 4, "interior": 0})
    assert integer.duals is None  # shadow prices aren't defined for an integer program
    assert check_solution(REDDY_MIKKS, integer) == []

    relaxed = solve(relax(REDDY_MIKKS))
    assert relaxed.objective == approx(21)
    assert relaxed.values == approx({"exterior": 3, "interior": 1.5})


@mark.parametrize("model", [WYNDOR, BLEND], ids=["wyndor", "blend"])
def test_duals_match_finite_differences(model):
    """Don't trust the solver's dual signs: nudge each rhs and watch the objective move.

    The optimal value is piecewise linear in each rhs, so any step that keeps the same
    constraints binding gives the exact slope (0.5 does, for both problems). A tiny step
    would be swamped by CBC's output precision: it reports values to ~8 significant digits.
    """
    step = 0.5
    base = solve(model)
    for c in model.constraints:
        nudged = solve(with_rhs(model, c.name, c.rhs + step))
        assert base.duals[c.name] == approx((nudged.objective - base.objective) / step, abs=1e-5)


def test_infeasible_reports_no_values():
    s = solve(INFEASIBLE)
    assert s.status is Status.INFEASIBLE
    assert s.objective is None and s.values == {}


def test_integer_infeasible_even_though_lp_relaxation_is_feasible():
    assert solve(INTEGER_INFEASIBLE).status is Status.INFEASIBLE
    assert solve(relax(INTEGER_INFEASIBLE)).status is Status.OPTIMAL


@mark.parametrize("integer", [False, True], ids=["lp", "mip"])
def test_unbounded(integer):
    assert solve(unbounded(integer)).status is Status.UNBOUNDED


def test_regression_cbc_preprocessing_bug():
    s = solve(CBC_PREPROCESS_BUG)
    assert s.status is Status.OPTIMAL
    assert s.objective == approx(0.2)
    assert s.values == approx({"x0": 0, "x1": 0.6, "x2": 1})


def test_cbc_times_out_instead_of_guessing(monkeypatch):
    """A known CBC limit: the honest answer here is "don't know", not a wrong label."""
    monkeypatch.setattr(solver, "CBC_TIME_LIMIT_SECONDS", 1)
    assert solve(HARD_INTEGER_INFEASIBLE).status is Status.ERROR
    assert solve_with_highs(HARD_INTEGER_INFEASIBLE).status is Status.INFEASIBLE


def relax(model: LPModel) -> LPModel:
    """The same model with every integrality requirement dropped."""
    variables = [v.model_copy(update={"integer": False}) for v in model.variables]
    return model.model_copy(update={"variables": variables})


def with_rhs(model: LPModel, name: str, rhs: float) -> LPModel:
    constraints = [
        c.model_copy(update={"rhs": rhs}) if c.name == name else c for c in model.constraints
    ]
    return model.model_copy(update={"constraints": constraints})
