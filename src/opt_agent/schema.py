"""Pydantic schema for a linear or mixed-integer program.

This is the contract between the LLM and the solver: Claude fills it in (milestone 4), and
everything downstream only ever sees a validated LPModel. Linear expressions are lists of
{var, coef} terms rather than {name: coef} dicts because strict tool use requires every
JSON object to have fixed keys.
"""

from collections import Counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    # Unknown keys and NaN/inf are errors, not silently accepted.
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Term(StrictModel):
    var: str = Field(description="The name of a declared variable")
    coef: float


def evaluate(terms: list[Term], values: dict[str, float]) -> float:
    """Value of a linear expression at the given point."""
    return sum(t.coef * values[t.var] for t in terms)


def magnitude(terms: list[Term], values: dict[str, float]) -> float:
    """Size of the numbers being added (not of their sum, which may cancel to ~0)."""
    return sum(abs(t.coef * values[t.var]) for t in terms)


class Variable(StrictModel):
    name: str = Field(description="What the variable counts or measures, e.g. 'trucks'")
    lower: float | None = Field(0.0, description="Lower bound, or null for none")
    upper: float | None = Field(None, description="Upper bound, or null for none")
    integer: bool = Field(False, description="True if it counts whole things")


class Objective(StrictModel):
    sense: Literal["min", "max"]
    terms: list[Term] = Field(description="The linear expression to optimize")


class Constraint(StrictModel):
    name: str = Field(description="A short label, e.g. 'budget'")
    terms: list[Term] = Field(description="The left-hand side")
    sense: Literal["<=", ">=", "=="]
    rhs: float = Field(description="The right-hand side constant")

    def slack(self, values: dict[str, float]) -> float:
        """Distance from violation: >= 0 when satisfied, < 0 when violated.

        An equality has slack 0 when satisfied and -|lhs - rhs| otherwise.
        """
        lhs = evaluate(self.terms, values)
        if self.sense == "<=":
            return self.rhs - lhs
        if self.sense == ">=":
            return lhs - self.rhs
        return -abs(lhs - self.rhs)


class LPModel(StrictModel):
    variables: list[Variable]
    objective: Objective
    constraints: list[Constraint]

    @property
    def is_mip(self) -> bool:
        return any(v.integer for v in self.variables)

    @model_validator(mode="after")
    def _check_consistency(self) -> "LPModel":
        # Collect every problem at once so an LLM can fix them all in one revision.
        problems = _name_problems(self) + _bound_problems(self) + _term_problems(self)
        if problems:
            raise ValueError("; ".join(problems))
        return self


def _duplicates(names: list[str]) -> list[str]:
    return [name for name, count in Counter(names).items() if count > 1]


def _labelled_expressions(model: LPModel) -> list[tuple[str, list[Term]]]:
    """Every linear expression in the model, with a label for error messages."""
    labelled = [("objective", model.objective.terms)]
    for c in model.constraints:
        labelled.append((f"constraint '{c.name}'", c.terms))
    return labelled


def _name_problems(model: LPModel) -> list[str]:
    problems = []
    for name in _duplicates([v.name for v in model.variables]):
        problems.append(f"variable '{name}' is declared more than once")
    for name in _duplicates([c.name for c in model.constraints]):
        problems.append(f"constraint '{name}' is declared more than once")
    return problems


def _bound_problems(model: LPModel) -> list[str]:
    problems = []
    for v in model.variables:
        if v.lower is not None and v.upper is not None and v.lower > v.upper:
            problems.append(f"variable '{v.name}' has lower bound {v.lower} > upper {v.upper}")
    return problems


def _term_problems(model: LPModel) -> list[str]:
    problems = []
    declared = {v.name for v in model.variables}
    used = set()
    for label, terms in _labelled_expressions(model):
        if not any(t.coef != 0 for t in terms):
            problems.append(f"{label} has no nonzero terms")
        for name in _duplicates([t.var for t in terms]):
            problems.append(f"{label} lists variable '{name}' more than once")
        for t in terms:
            if t.var not in declared:
                problems.append(f"{label} uses undeclared variable '{t.var}'")
            if t.coef != 0:
                used.add(t.var)
    # A variable with no nonzero coefficient anywhere is meaningless, and CBC never sees it.
    for v in model.variables:
        if v.name not in used:
            problems.append(f"variable '{v.name}' is declared but never used")
    return problems
