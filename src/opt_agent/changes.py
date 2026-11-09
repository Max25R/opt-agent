"""How a revised model differs from the one before, and which differences look like cheating.

When a model is infeasible or unbounded, the easy way out is to drop or weaken whatever
the solver complained about. So these are *flagged*: deleting or loosening a constraint
(through its right-hand side or its coefficients), flipping a constraint's direction,
changing an equation at all, loosening a bound, making an integer variable continuous,
removing a variable, dropping a variable from the objective or negating its coefficient
there, or flipping the objective. A flag isn't proof of cheating (the first model may have
had a typo, and the one outcome self-correction changed in M6 came from a flagged revision
that was right), but it marks the revision for review.

Constraints are compared by structure (direction, coefficients, right-hand side), not by
text: a renamed, reordered, or rewritten-the-other-way-round row is the same row (audit,
finding 6).
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
    pairs, deleted, added = _pairs(old.constraints, new.constraints)
    found = []
    for c, n in pairs:
        found += _constraint_diff(c, n, signs)
    found += [(f"deleted constraint {c.name!r}", True) for c in deleted]
    found += [(f"added constraint {n.name!r}", False) for n in added]
    return found


def _pairs(
    old: list[Constraint], new: list[Constraint]
) -> tuple[list[tuple[Constraint, Constraint]], list[Constraint], list[Constraint]]:
    """Each old constraint's counterpart in the new model, compared by structure, not text.
    1. The same constraint, whatever its name, its place in the list, the order of its
       terms, or which way round it's written (a >= row is the <= of its negation): no
       change at all.
    2. The same name.
    3. The same variables, the closest first (same direction, fewest coefficient changes,
       nearest right-hand side).
    What's left is deleted (old) or added (new)."""
    left, right = list(old), list(new)
    pairs = []
    for counterpart in (_same_constraint, _same_name, _closest_with_the_same_variables):
        for c in list(left):
            n = counterpart(c, right)
            if n is not None:
                pairs.append((c, n))
                left = [x for x in left if x is not c]
                right = [x for x in right if x is not n]
    position = {id(c): i for i, c in enumerate(old)}
    pairs.sort(key=lambda pair: position[id(pair[0])])
    changed = [(c, n) for c, n in pairs if _canonical(c) != _canonical(n)]
    return changed, left, right


def _same_constraint(c: Constraint, candidates: list[Constraint]) -> Constraint | None:
    return next((n for n in candidates if _canonical(n) == _canonical(c)), None)


def _same_name(c: Constraint, candidates: list[Constraint]) -> Constraint | None:
    return next((n for n in candidates if n.name == c.name), None)


def _closest_with_the_same_variables(
    c: Constraint, candidates: list[Constraint]
) -> Constraint | None:
    same = [n for n in candidates if _coefs(n.terms).keys() == _coefs(c.terms).keys()]
    return min(same, key=lambda n: _distance(c, n), default=None)


def _canonical(c: Constraint) -> tuple:
    """The set of points a constraint allows, as a comparable value."""
    coefs, rhs, sense = _coefs(c.terms), c.rhs, c.sense
    if sense == ">=":
        coefs, rhs, sense = {var: -a for var, a in coefs.items()}, -rhs, "<="
    return sense, frozenset(coefs.items()), rhs


def _distance(c: Constraint, n: Constraint) -> tuple:
    n = _aligned(c, n)
    old, new = _coefs(c.terms), _coefs(n.terms)
    return (c.sense != n.sense, sum(old.get(v) != new.get(v) for v in {**old, **new}),
            abs(c.rhs - n.rhs))  # fmt: skip


def _aligned(c: Constraint, n: Constraint) -> Constraint:
    """`n` written the way round `c` is, when it's c's inequality turned around
    (x <= 7 for -x >= -7); otherwise `n` as it is, so a real flip shows as a flip."""
    opposite = {"<=": ">=", ">=": "<="}
    if opposite.get(c.sense) != n.sense:
        return n
    turned = n.model_copy(update={"terms": [Term(var=t.var, coef=-t.coef) for t in n.terms],
                                  "rhs": -n.rhs, "sense": c.sense})  # fmt: skip
    old = _coefs(c.terms)

    def differing(x: Constraint) -> int:
        new = _coefs(x.terms)
        return sum(old.get(v) != new.get(v) for v in {**old, **new})

    return turned if differing(turned) < differing(n) else n


def _constraint_diff(c: Constraint, n: Constraint, signs: dict[str, int]) -> list[tuple[str, bool]]:
    label = repr(c.name) if c.name == n.name else f"{c.name!r} (now {n.name!r})"
    n = _aligned(c, n)
    details = "; ".join(d for d in (_rhs_text(c, n), _terms_text(c, n)) if d)
    if c.sense != n.sense:
        also = f"; {details}" if details else ""
        if c.sense == "==":  # an equation became an inequality: strictly weaker
            return [(f"loosened {label}: == became {n.sense}{also}", True)]
        if n.sense == "==" and not details:  # the same row, now as an equation: narrower
            return [(f"tightened {label}: {c.sense} became ==", False)]
        # A flip may be the fix the feedback asked for, but it changes which points are
        # allowed: always marked for review, with whatever else changed in the row.
        return [(f"flipped {label}: {c.sense} became {n.sense}{also}", True)]
    if c.sense == "==":  # moving an equation can make an infeasible model feasible
        return [(f"changed the equation {label}: {details}", True)]
    found = []
    if _coefs(c.terms) != _coefs(n.terms):
        found.append(_term_diff(label, c, n, signs))
    if c.rhs != n.rhs:
        looser = (c.sense == "<=" and n.rhs > c.rhs) or (c.sense == ">=" and n.rhs < c.rhs)
        verb = "loosened" if looser else "tightened"
        found.append((f"{verb} {label}: right-hand side {c.rhs:g} became {n.rhs:g}", looser))
    return found


def _rhs_text(c: Constraint, n: Constraint) -> str:
    return f"right-hand side {c.rhs:g} became {n.rhs:g}" if c.rhs != n.rhs else ""


def _terms_text(c: Constraint, n: Constraint) -> str:
    old, new = _coefs(c.terms), _coefs(n.terms)
    edits = [(var, old.get(var, 0.0), new.get(var, 0.0)) for var in {**old, **new}]
    return ", ".join(f"{var!r} {a:g} became {b:g}" for var, a, b in edits if a != b)


def _term_diff(label: str, c: Constraint, n: Constraint, signs: dict[str, int]) -> tuple[str, bool]:
    """Coefficient edits can loosen a row as surely as its right-hand side can: lowering a
    coefficient in a <= row (of a variable that can't go negative), dropping that term, or
    adding a new variable with a negative one (a slack that absorbs any shortfall)."""
    old, new = _coefs(c.terms), _coefs(n.terms)
    edits = [(var, old.get(var, 0.0), new.get(var, 0.0)) for var in {**old, **new}]
    edits = [(var, a, b) for var, a, b in edits if a != b]
    details = _terms_text(c, n)
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
    # Negating a coefficient turns a direction that improved forever into one that doesn't,
    # as surely as dropping the variable would.
    found += [
        (f"negated {var!r} in the objective: {coef:g} became {new_terms[var]:g}", True)
        for var, coef in old_terms.items()
        if new_terms.get(var, 0.0) * coef < 0
    ]
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
    """Coefficients by variable, zeros left out: a zero term says nothing."""
    return {t.var: t.coef for t in terms if t.coef != 0}


def _as_number(bound: float | None, infinite_side: int) -> float:
    return infinite_side * float("inf") if bound is None else bound


def _show(bound: float | None) -> str:
    return "none" if bound is None else f"{bound:g}"
