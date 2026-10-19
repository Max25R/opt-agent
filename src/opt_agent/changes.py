"""How a revised model differs from the one before, and which differences look like cheating.

When a model is infeasible or unbounded, the easy way out is to drop or weaken whatever
the solver complained about. So deleting or loosening a constraint, loosening a bound,
making an integer variable continuous, or flipping the objective is *flagged*. A flag
isn't proof of cheating (the first model may have had a typo), but it marks the revision
for review.
"""

from pydantic import BaseModel

from opt_agent.schema import Constraint, LPModel, Term, Variable


class Changes(BaseModel):
    changes: list[str]  # every difference, in words
    flags: list[str]  # the ones that delete or loosen something

    @property
    def none(self) -> bool:
        return not self.changes


def compare(old: LPModel, new: LPModel) -> Changes:
    found = _constraint_changes(old, new) + _variable_changes(old, new)
    found += _objective_changes(old, new)
    return Changes(
        changes=[text for text, _ in found], flags=[text for text, flag in found if flag]
    )


# Each helper returns (description, is_flag) pairs.


def _constraint_changes(old: LPModel, new: LPModel) -> list[tuple[str, bool]]:
    found, matched = [], []
    for c in old.constraints:
        unmatched = [n for n in new.constraints if all(n is not m for m in matched)]
        counterpart = _counterpart(c, unmatched)
        if counterpart is None:
            found.append((f"deleted constraint {c.name!r}", True))
        else:
            matched.append(counterpart)
            found += _constraint_diff(c, counterpart)
    for n in new.constraints:
        if all(n is not m for m in matched):
            found.append((f"added constraint {n.name!r}", False))
    return found


def _counterpart(c: Constraint, candidates: list[Constraint]) -> Constraint | None:
    """The same constraint in the new model: same name, or else the same left-hand side."""
    by_name = next((n for n in candidates if n.name == c.name), None)
    return by_name or next((n for n in candidates if _coefs(n.terms) == _coefs(c.terms)), None)


def _constraint_diff(c: Constraint, n: Constraint) -> list[tuple[str, bool]]:
    label = repr(c.name) if c.name == n.name else f"{c.name!r} (now {n.name!r})"
    if _coefs(c.terms) != _coefs(n.terms):
        return [(f"changed the terms of {label}", False)]
    if c.sense != n.sense:
        if c.sense == "==":  # an equation became an inequality: strictly weaker
            return [(f"loosened {label}: == became {n.sense}", True)]
        return [(f"flipped {label}: {c.sense} became {n.sense}", False)]
    if c.rhs == n.rhs:
        return []
    looser = (c.sense == "<=" and n.rhs > c.rhs) or (c.sense == ">=" and n.rhs < c.rhs)
    verb = "loosened" if looser else "changed" if c.sense == "==" else "tightened"
    return [(f"{verb} {label}: right-hand side {c.rhs:g} became {n.rhs:g}", looser)]


def _variable_changes(old: LPModel, new: LPModel) -> list[tuple[str, bool]]:
    found = []
    new_vars = {v.name: v for v in new.variables}
    for v in old.variables:
        n = new_vars.get(v.name)
        if n is None:
            found.append((f"removed variable {v.name!r}", False))
            continue
        if v.integer != n.integer:
            kind = "integer" if n.integer else "continuous"
            found.append((f"made {v.name!r} {kind}", not n.integer))  # relaxing is a flag
        found += _bound_changes(v, n)
    old_names = {v.name for v in old.variables}
    found += [(f"added variable {n!r}", False) for n in new_vars if n not in old_names]
    return found


def _bound_changes(v: Variable, n: Variable) -> list[tuple[str, bool]]:
    found = []
    low, new_low = _as_number(v.lower, -1), _as_number(n.lower, -1)
    if low != new_low:
        verb = "loosened" if new_low < low else "tightened"
        text = f"{verb} the lower bound of {v.name!r}: {_show(v.lower)} became {_show(n.lower)}"
        found.append((text, new_low < low))
    high, new_high = _as_number(v.upper, 1), _as_number(n.upper, 1)
    if high != new_high:
        verb = "loosened" if new_high > high else "tightened"
        text = f"{verb} the upper bound of {v.name!r}: {_show(v.upper)} became {_show(n.upper)}"
        found.append((text, new_high > high))
    return found


def _objective_changes(old: LPModel, new: LPModel) -> list[tuple[str, bool]]:
    found = []
    if old.objective.sense != new.objective.sense:
        found.append((f"flipped the objective: {old.objective.sense} became "
                      f"{new.objective.sense}", True))  # fmt: skip
    if _coefs(old.objective.terms) != _coefs(new.objective.terms):
        found.append(("changed the objective's terms", False))
    return found


def _coefs(terms: list[Term]) -> dict[str, float]:
    return {t.var: t.coef for t in terms}


def _as_number(bound: float | None, infinite_side: int) -> float:
    return infinite_side * float("inf") if bound is None else bound


def _show(bound: float | None) -> str:
    return "none" if bound is None else f"{bound:g}"
