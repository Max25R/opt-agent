"""Hypothesis strategies that generate small, random, valid LPModels.

Coefficients, bounds, and right-hand sides are small integers. That keeps every problem
well-conditioned, so when two solvers disagree it's a real bug, not floating-point noise.
"""

from hypothesis import strategies as st

from opt_agent.schema import Constraint, LPModel, Objective, Term, Variable

nonzero_coefs = st.sampled_from([c for c in range(-5, 6) if c != 0])


@st.composite
def variables(draw, name: str) -> Variable:
    if draw(st.booleans()):
        # Integer variables always get finite bounds. Over unbounded integers,
        # branch-and-bound may never finish (see test_cbc_times_out_instead_of_guessing),
        # and a time-out isn't a disagreement worth reporting.
        lower = draw(st.integers(-5, 5))
        return Variable(
            name=name, lower=lower, upper=lower + draw(st.integers(0, 10)), integer=True
        )
    lower = draw(st.one_of(st.just(0), st.none(), st.integers(-5, 5)))
    width = draw(st.one_of(st.none(), st.integers(0, 10)))  # None: no upper bound
    upper = None if width is None else (lower or 0) + width
    return Variable(name=name, lower=lower, upper=upper)


@st.composite
def constraints(draw, name: str, var_names: list[str]) -> Constraint:
    used = draw(st.lists(st.sampled_from(var_names), min_size=1, unique=True))
    return Constraint(
        name=name,
        terms=[Term(var=v, coef=draw(nonzero_coefs)) for v in used],
        sense=draw(st.sampled_from(["<=", ">=", "=="])),
        rhs=draw(st.integers(-10, 20)),
    )


@st.composite
def lp_models(draw, max_vars: int = 4, max_constraints: int = 4) -> LPModel:
    names = [f"x{i}" for i in range(draw(st.integers(1, max_vars)))]
    # Every variable gets a nonzero objective coefficient, so none is ever "unused".
    objective = Objective(
        sense=draw(st.sampled_from(["min", "max"])),
        terms=[Term(var=n, coef=draw(nonzero_coefs)) for n in names],
    )
    count = draw(st.integers(0, max_constraints))
    return LPModel(
        variables=[draw(variables(n)) for n in names],
        objective=objective,
        constraints=[draw(constraints(f"c{i}", names)) for i in range(count)],
    )
