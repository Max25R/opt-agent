import pytest
from problems import CBC_FREE_VARIABLE_BUG, FISHERY, HIGHS_FREE_VARIABLE_BUG, WYNDOR, terms
from pytest import mark

from opt_agent import highs
from opt_agent.highs import solve_with_highs
from opt_agent.nl4opt import convert
from opt_agent.rays import certified_ray, improvement, is_ray_from, ray_model
from opt_agent.schema import LPModel
from opt_agent.solver import Status, solve

SOLVERS = [solve, solve_with_highs]
# A feasible point of each counterexample, to start the long step from.
POINTS = {
    "cbc-bug": (CBC_FREE_VARIABLE_BUG, {"x0": 1.0, "x1": 0.0, "x2": 0.0}),
    "highs-bug": (HIGHS_FREE_VARIABLE_BUG, {"x0": -7.0, "x1": -4.0, "x2": 0.0, "x3": 0.0}),
}
# A bounded LP (optimum 1e6, both solvers agree) where a near-zero "direction" used to pass:
# max 1e6*y subject to y + 0.001x <= 1 and y - 0.001x <= 1.
BOUNDED = LPModel.model_validate(
    {
        "variables": [{"name": "x", "lower": None}, {"name": "y", "lower": None}],
        "objective": {"sense": "max", "terms": terms({"y": 1e6})},
        "constraints": [
            {"name": "a", "terms": terms({"y": 1, "x": 0.001}), "sense": "<=", "rhs": 1},
            {"name": "b", "terms": terms({"y": 1, "x": -0.001}), "sense": "<=", "rhs": 1},
        ],
    }
)


def test_the_ray_model_keeps_constraints_and_makes_every_direction_bounded():
    rays = ray_model(CBC_FREE_VARIABLE_BUG)
    assert [(v.lower, v.upper) for v in rays.variables] == [(-1, 1), (-1, 1), (0, 1)]
    assert [(c.terms, c.sense, c.rhs) for c in rays.constraints] == [
        (CBC_FREE_VARIABLE_BUG.constraints[0].terms, "<=", 0.0)
    ]


def test_bounded_both_ways_means_no_direction_and_integers_are_relaxed():
    rays = ray_model(HIGHS_FREE_VARIABLE_BUG)
    assert [(v.lower, v.upper, v.integer) for v in rays.variables] == [
        (-1, 1, False), (0, 0, False), (0, 0, False), (-1, 0, False),
    ]  # fmt: skip


def test_a_true_ray_passes_both_checks():
    model, point = POINTS["cbc-bug"]
    assert is_ray_from(model, point, {"x0": 1, "x1": 0, "x2": 0})
    assert improvement(model, {"x0": 1, "x1": 0, "x2": 0}) == 5


@pytest.mark.parametrize(
    "d",
    [
        {"x0": -1, "x1": 0, "x2": 0},  # breaks c0
        {"x0": 0, "x1": 0, "x2": -1},  # x2 >= 0
        {"x0": 0, "x1": 0, "x2": 1},  # costs more: no improvement
    ],
)
def test_a_false_ray_is_rejected(d):
    model, point = POINTS["cbc-bug"]
    assert not is_ray_from(model, point, d)


def test_a_near_zero_direction_is_rejected():
    """d = (0, 1e-7) bends each constraint by only 1e-7, inside an absolute tolerance, while
    improving the objective. Scaled to (0, 1) it plainly breaks y + 0.001x <= 0. (It used
    to pass.)"""
    assert solve(BOUNDED).status is Status.OPTIMAL
    assert not is_ray_from(BOUNDED, {"x": 0.0, "y": 0.0}, {"x": 0.0, "y": 1e-7})


@mark.parametrize("solve_once", SOLVERS, ids=["cbc", "highs"])
@mark.parametrize("case", POINTS, ids=list(POINTS))
def test_both_solvers_certify_a_ray_for_both_counterexamples(case, solve_once):
    model, point = POINTS[case]
    assert certified_ray(model, point, solve_once) is not None


@mark.parametrize("solve_once", SOLVERS, ids=["cbc", "highs"])
def test_no_ray_is_certified_from_an_infeasible_point(solve_once):
    """ "Feasible and has an improving ray" is the proof; without a feasible point, no proof."""
    model, _ = POINTS["cbc-bug"]
    infeasible = {"x0": 0.0, "x1": 0.0, "x2": 0.0}  # 5*x0 + 4*x1 >= 1 fails
    assert certified_ray(model, infeasible, solve_once) is None
    assert certified_ray(model, None, solve_once) is None


@mark.parametrize("solve_once", SOLVERS, ids=["cbc", "highs"])
@mark.parametrize(
    ("model", "point"),
    [
        (WYNDOR, {"doors": 2.0, "windows": 6.0}),
        (convert(FISHERY).model, {"sled dogs": 0.0, "trucks": 10.0}),
    ],
    ids=["wyndor", "fishery"],
)
def test_a_true_optimum_has_no_ray(model, point, solve_once):
    assert certified_ray(model, point, solve_once) is None


def test_unbounded_comes_with_its_certificate():
    s = solve_with_highs(CBC_FREE_VARIABLE_BUG)
    assert s.status is Status.UNBOUNDED
    assert "improves forever along" in s.note


def test_scipy_status_4_on_a_bounded_model_is_an_error(monkeypatch):
    """SciPy's status 4 ("other") also covers HiGHS solve errors. On a bounded model there's
    no certified ray, so it must not become "unbounded"."""
    real_milp, calls = highs.milp, []

    def first_call_fails(*args, **kwargs):
        calls.append(1)
        if len(calls) == 1:
            return type("Result", (), {"status": 4, "x": None, "fun": None})()
        return real_milp(*args, **kwargs)

    monkeypatch.setattr(highs, "milp", first_call_fails)
    s = solve_with_highs(WYNDOR)
    assert s.status is Status.ERROR
    assert "no certified ray" in s.note


@mark.parametrize("solve_once", SOLVERS, ids=["cbc", "highs"])
def test_a_variable_only_in_the_objective_still_gets_a_feasible_point(solve_once):
    """With the objective zeroed for the feasibility solve, CBC never sees z and gives it no
    value (it used to crash the ray check). z touches no constraint, so any value in its
    bounds will do."""
    model = LPModel.model_validate(
        {
            "variables": [{"name": "y"}, {"name": "z", "lower": 2, "integer": True}],
            "objective": {"sense": "max", "terms": terms({"y": 1, "z": 1})},
            "constraints": [{"name": "cap", "terms": terms({"y": 1}), "sense": "<=", "rhs": 1}],
        }
    )
    s = solve_once(model)
    assert s.status is Status.UNBOUNDED
    assert "z +1" in s.note
