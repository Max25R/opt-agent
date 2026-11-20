"""limits.py (ADR-0009): what limits an integer program's optimum, by solving it again. Each
model is small enough that its answers are worked out by hand in the comments; each re-solve
runs both CBC and HiGHS. Then the explainer's request with and without limits, and the agent.
No API calls (FakeClient)."""

import json

import pytest
from fakes import FakeClient

from opt_agent import agent, api, explain, limits
from opt_agent.demo import app
from opt_agent.explain import LIMITS_PROMPT, SYSTEM_PROMPT, Facts, build_request, solver_facts
from opt_agent.limits import Limit, constraint_limits
from opt_agent.schema import LPModel
from opt_agent.solution import Solution, Status
from opt_agent.solver import solve


def model(sense: str, objective: dict[str, float], *constraints, integer: bool = True,
          upper: dict[str, float] | None = None) -> LPModel:  # fmt: skip
    """A small model over the objective's variables, all >= 0."""
    return LPModel.model_validate({
        "variables": [{"name": v, "lower": 0, "upper": (upper or {}).get(v), "integer": integer}
                      for v in objective],
        "objective": {"sense": sense,
                      "terms": [{"var": v, "coef": c} for v, c in objective.items()]},
        "constraints": [{"name": n, "terms": [{"var": v, "coef": c} for v, c in t.items()],
                         "sense": s, "rhs": rhs} for n, t, s, rhs in constraints],
    })  # fmt: skip


# The rickshaw problem's shape (dev -640645082): max 50 r + 30 o
BUDGET = ("budget", {"r": 10, "o": 8}, "<=", 200)  # 10 r + 8 o <= 200
POLLUTION = ("pollution", {"r": 1, "o": -1}, "<=", 0)  # r <= o
CAP = ("cap", {"o": 1}, "<=", 30)  # o <= 30
PROFIT = {"r": 50, "o": 30}


def found(m: LPModel) -> dict[str, Limit] | None:
    return constraint_limits(m, solve(m))


def test_a_constraint_with_slack_can_still_limit_an_integer_program():
    # r = o = 11 earns 880 and spends 198 of 200: the budget has slack 2. Without it, r = o
    # grows forever (unbounded), so it limits the answer. At 201 nothing whole is better
    # (r = o = 11 still; r = 11, o = 12 costs 206): one more dollar buys nothing.
    m = model("max", PROFIT, BUDGET, POLLUTION, CAP)
    facts = solver_facts(m, solve(m))
    assert facts.objective == 880 and facts.slack["budget"] == 2
    assert "budget" not in facts.binding
    result = found(m)
    assert result["budget"] == Limit(dropped_improves=True, loosened_improves=False)
    # The pollution rule binds (r = o); without it r = 20, o = 0 earns 1000, but r <= o + 1
    # buys nothing (r = 11, o = 10 earns 850).
    assert result["pollution"] == Limit(dropped_improves=True, loosened_improves=False)
    # o <= 30 has slack 19 and never matters
    assert result["cap"] == Limit(dropped_improves=False, loosened_improves=False)


def test_a_finite_better_optimum_counts_too():
    # with o <= 15 as a bound, dropping the budget gives r = o = 15: 1200, better than 880
    m = model("max", PROFIT, BUDGET, POLLUTION, upper={"o": 15})
    assert found(m)["budget"].dropped_improves is True
    assert solve(limits.without(m, m.constraints[0])).objective == pytest.approx(1200)


def test_better_means_lower_for_a_minimization():
    # min 10 x + 7 y with 3 x + 3 y >= 4: y = 2 costs 14 and gives 6, slack 2. Without the
    # rule, nothing (0); at >= 3, y = 1 (7). Both better, though the rule has slack.
    m = model("min", {"x": 10, "y": 7}, ("need", {"x": 3, "y": 3}, ">=", 4))
    facts = solver_facts(m, solve(m))
    assert facts.objective == 14 and facts.slack["need"] == 2
    assert found(m)["need"] == Limit(dropped_improves=True, loosened_improves=True)


def test_an_equation_is_dropped_but_never_loosened():
    # max x + y, x = 2 y, x + y <= 10: x = 6, y = 3 (9; 8 and 4 would be 12). Without the
    # equation, 10; without the room limit, unbounded; at 11, still 9.
    m = model("max", {"x": 1, "y": 1}, ("ratio", {"x": 1, "y": -2}, "==", 0),
              ("room", {"x": 1, "y": 1}, "<=", 10))  # fmt: skip
    assert found(m) == {"ratio": Limit(dropped_improves=True, loosened_improves=None),
                        "room": Limit(dropped_improves=True, loosened_improves=False)}  # fmt: skip


def test_the_last_constraint_can_go():
    m = model("max", {"x": 1}, ("room", {"x": 1}, "<=", 3))
    assert found(m) == {"room": Limit(dropped_improves=True, loosened_improves=True)}


def test_an_lp_gets_no_limits():
    # in an LP, slack never limits and shadow prices say what a unit is worth
    m = model("max", PROFIT, BUDGET, POLLUTION, CAP, integer=False)
    assert found(m) is None
    assert solver_facts(m, solve(m), with_limits=True).limits is None


def test_only_an_optimum_is_tested():
    m = model("max", PROFIT, POLLUTION)  # unbounded
    with pytest.raises(ValueError, match="only an optimum"):
        constraint_limits(m, solve(m))


def test_a_re_solve_the_solvers_dont_agree_on_is_unknown(monkeypatch):
    m = model("max", PROFIT, BUDGET, POLLUTION, CAP)
    solution = solve(m)
    other = Solution(solver="highs", status=Status.OPTIMAL, objective=-1.0,
                     values={"r": 0, "o": 0})  # fmt: skip
    monkeypatch.setattr(limits, "solve_with_highs", lambda changed: other)
    assert limits.improves(m, solution, limits.without(m, m.constraints[2])) is None


def test_a_re_solve_that_fails_a_check_or_comes_back_infeasible_is_unknown(monkeypatch):
    m = model("max", PROFIT, BUDGET, POLLUTION, CAP)
    solution, changed = solve(m), limits.without(m, m.constraints[2])
    monkeypatch.setattr(limits, "check_solution", lambda model, s: ["a made-up problem"])
    assert limits.improves(m, solution, changed) is None
    monkeypatch.undo()
    infeasible = Solution(solver="x", status=Status.INFEASIBLE)
    monkeypatch.setattr(limits, "solve", lambda changed: infeasible)
    monkeypatch.setattr(limits, "solve_with_highs", lambda changed: infeasible)
    assert limits.improves(m, solution, changed) is None


# ---- the explainer's request -------------------------------------------------------------


def test_limits_go_to_the_explainer_with_their_paragraph():
    m = model("max", PROFIT, BUDGET, POLLUTION, CAP)
    facts = solver_facts(m, solve(m), with_limits=True)
    request = build_request("Rickshaws.", m, facts, "claude-haiku-5-5")
    assert request["system"] == SYSTEM_PROMPT + LIMITS_PROMPT
    sent = json.loads(request["messages"][0]["content"].split("Model and facts:\n", 1)[1])
    assert sent["facts"]["limits"]["budget"] == {"dropped_improves": True,
                                                 "loosened_improves": False}  # fmt: skip


def test_without_limits_the_request_is_the_one_cached_before_adr_0009():
    """Every explanation the demo cached (two of them integer programs) is rebuilt exactly
    from its own model and facts, so a replay finds it: a request without limits hasn't
    changed."""
    rebuilt = 0
    for path in sorted(app.REPLIES.glob("*.json")):
        request = json.loads(path.read_text())["request"]
        if request["system"] != SYSTEM_PROMPT:
            continue  # not an explanation
        content = request["messages"][0]["content"]
        problem = content.removeprefix("Problem:\n").split("\n\nModel and facts:\n", 1)[0]
        sent = json.loads(content.split("Model and facts:\n", 1)[1])
        m, facts = LPModel.model_validate(sent["model"]), Facts.model_validate(sent["facts"])
        with api.max_tokens_cap(request["max_tokens"]):
            again = build_request(problem, m, facts, request["model"])
        assert api.cache_key(again) == api.cache_key(request)
        rebuilt += 1
    assert rebuilt == 4


def test_the_agent_gives_an_integer_program_its_limits_unless_replaying():
    m = model("max", PROFIT, BUDGET, POLLUTION, CAP)
    for explain_limits, system in ((True, SYSTEM_PROMPT + LIMITS_PROMPT), (False, SYSTEM_PROMPT)):
        client = FakeClient(m.model_dump_json(), "Make 11 of each.")
        result = agent.run("Rickshaws.", client, max_attempts=1, explain_limits=explain_limits)
        assert result.verified and result.explanation is not None
        assert client.requests[-1]["system"] == system
    assert explain.solver_facts(m, solve(m)).limits is None  # off unless asked
