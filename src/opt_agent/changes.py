"""How a revised model differs from the one before, and which differences look like cheating.

When a model is infeasible or unbounded, the easy way out is to drop or weaken whatever
the solver complained about. So these are *flagged*: deleting or loosening a constraint
(through its right-hand side, its direction, or its coefficients), loosening a bound,
making an integer variable continuous, removing a variable, dropping a variable from the
objective, or flipping the objective. A flag isn't proof of cheating (the first model may
have had a typo), but it marks the revision for review.
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
    signs = _signs(old, new)
    found, matched = [], []
    for c in old.constraints:
        unmatched = [n for n in new.constraints if all(n is not m for m in matched)]
        counterpart = _counterpart(c, unmatched)
        if counterpart is None:
            found.append((f"deleted constraint {c.name!r}", True))
        else:
            matched.append(counterpart)
            found += _constraint_diff(c, counterpart, signs)
    for n in new.constraints:
        if all(n is not m for m in matched):
            found.append((f"added constraint {n.name!r}", False))
    return found


def _counterpart(c: Constraint, candidates: list[Constraint]) -> Constraint | None:
    """The same constraint in the new model: same name, or else the same left-hand side."""
    by_name = next((n for n in candidates if n.name == c.name), None)
    return by_name or next((n for n in candidates if _coefs(n.terms) == _coefs(c.terms)), None)


def _constraint_diff(c: Constraint, n: Constraint, signs: dict[str, int]) -> list[tuple[str, bool]]:
    label = repr(c.name) if c.name == n.name else f"{c.name!r} (now {n.name!r})"
    found = []
    if _coefs(c.terms) != _coefs(n.terms):
        found.append(_term_diff(label, c, n, signs))
    if c.sense != n.sense:
        if c.sense == "==":  # an equation became an inequality: strictly weaker
            return [*found, (f"loosened {label}: == became {n.sense}", True)]
        return [*found, (f"flipped {label}: {c.sense} became {n.sense}", False)]
    if c.rhs != n.rhs:
        looser = (c.sense == "<=" and n.rhs > c.rhs) or (c.sense == ">=" and n.rhs < c.rhs)
        verb = "loosened" if looser else "changed" if c.sense == "==" else "tightened"
        found.append((f"{verb} {label}: right-hand side {c.rhs:g} became {n.rhs:g}", looser))
    return found


def _term_diff(label: str, c: Constraint, n: Constraint, signs: dict[str, int]) -> tuple[str, bool]:
    """Coefficient edits can loosen a row as surely as its right-hand side can: lowering a
    coefficient in a <= row (of a variable that can't go negative), dropping that term, or
    adding a new variable with a negative one (a slack that absorbs any shortfall)."""
    old, new = _coefs(c.terms), _coefs(n.terms)
    edits = [(var, old.get(var, 0.0), new.get(var, 0.0)) for var in {**old, **new}]
    edits = [(var, a, b) for var, a, b in edits if a != b]
    details = ", ".join(f"{var!r} {a:g} became {b:g}" for var, a, b in edits)
    if c.sense != n.sense or c.sense == "==":
        return (f"changed the terms of {label}: {details}", False)  # no direction to judge
    looser = any(_loosens(c.sense, b - a, signs[var]) for var, a, b in edits)
    verb = "loosened" if looser else "tightened"
    return (f"{verb} the terms of {label}: {details}", looser)


def _loosens(sense: str, delta: float, sign: int) -> bool:
    """Does changing one coefficient by `delta` let some point satisfy the row that didn't?

    A <= row loosens if the left-hand side can get smaller: delta * x < 0 for some allowed
    x. A >= row loosens if it can get bigger. For a free variable (sign 0) either can happen.
    """
    if sign == 0:
        return True
    return delta * sign < 0 if sense == "<=" else delta * sign > 0


def _signs(old: LPModel, new: LPModel) -> dict[str, int]:
    """+1 for a variable that can't go negative, -1 for one that can't go positive, 0 if
    it's free. The old model's bounds count; a variable added in the revision uses its own."""
    signs = {}
    for v in [*new.variables, *old.variables]:  # old last, so its bounds win
        nonnegative = v.lower is not None and v.lower >= 0
        signs[v.name] = 1 if nonnegative else -1 if v.upper is not None and v.upper <= 0 else 0
    return signs


def _variable_changes(old: LPModel, new: LPModel) -> list[tuple[str, bool]]:
    found = []
    new_vars = {v.name: v for v in new.variables}
    for v in old.variables:
        n = new_vars.get(v.name)
        if n is None:
            # Dropping a decision dodges whatever it caused: a ray it ran along, or a
            # bound or requirement it couldn't meet. Its terms vanish with it.
            found.append((f"removed variable {v.name!r}", True))
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
    old_terms, new_terms = _coefs(old.objective.terms), _coefs(new.objective.terms)
    if old_terms != new_terms:
        found.append(("changed the objective's terms", False))
    # Zeroing a variable's objective coefficient silences an unbounded direction without
    # touching any constraint. (A variable removed outright is flagged on its own.)
    new_names = {v.name for v in new.variables}
    found += [
        (f"dropped {var!r} from the objective", True)
        for var, coef in old_terms.items()
        if coef != 0 and new_terms.get(var, 0.0) == 0 and var in new_names
    ]
    return found


def _coefs(terms: list[Term]) -> dict[str, float]:
    return {t.var: t.coef for t in terms}


def _as_number(bound: float | None, infinite_side: int) -> float:
    return infinite_side * float("inf") if bound is None else bound


def _show(bound: float | None) -> str:
    return "none" if bound is None else f"{bound:g}"
