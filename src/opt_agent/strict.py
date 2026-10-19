"""The strict reading: "more than", "must exceed", "less than" taken literally.

NL4Opt's annotation scheme has no strict operators, so nl4opt.py models strict wording as
>= or <= and notes each case ("strict-wording"). An agent that writes "x > y" as
x >= y + 1 then disagrees with the ground truth while being right. So for integer
problems the ground truth also stores the answer with every noted constraint read
strictly, and either reading is accepted (ground_truth.matching_reading).

Over integers a strict inequality is an ordinary one moved by the smallest step its left
side can take. With integer coefficients that step is 1 (x > y means x >= y + 1). With
decimals it's smaller: 0.6x - 0.4y only takes multiples of 0.2, so 0.6x - 0.4y > 0 means
0.6x - 0.4y >= 0.2. In general, clear the denominators (L) and take the gcd (g) of the
cleared coefficients: the step is g / L. Exact fractions keep 0.6 from becoming
0.59999999999999997779.

Over continuous variables there's no smallest step, and a strict inequality that binds at
the optimum leaves no optimum at all (only a supremum), so there's no strict reading.
"""

import math
from fractions import Fraction

from opt_agent.nl4opt import Note
from opt_agent.schema import Constraint, LPModel


def strict_constraints(notes: list[Note]) -> list[str]:
    """Names of the constraints whose wording is strict. A note's detail starts with the
    constraint's name: "c2_xy: text says 'must exceed' (strict); modeled as >="."""
    return [n.detail.split(":", 1)[0] for n in notes if n.kind == "strict-wording"]


def strict_model(model: LPModel, names: list[str]) -> tuple[LPModel, list[str]]:
    """The model with each named constraint read strictly, and what changed, in words.
    Meant for all-integer models: the step assumes every variable is an integer."""
    constraints, changed = [], []
    for c in model.constraints:
        if c.name in names and c.sense != "==":
            tight = tighten(c)
            changed.append(f"{c.name}: {c.sense} {c.rhs:g} became {tight.sense} {tight.rhs:g}")
            constraints.append(tight)
        else:
            constraints.append(c)
    missing = set(names) - {c.name for c in model.constraints}
    if missing:
        raise ValueError(f"no constraint named {sorted(missing)}")
    return model.model_copy(update={"constraints": constraints}), changed


def tighten(c: Constraint) -> Constraint:
    """a.x > b  ->  a.x >= b + (the next value a.x can take); likewise for <."""
    s, b = step(c), _exact(c.rhs)
    if c.sense == ">=":
        rhs = (math.floor(b / s) + 1) * s
    elif c.sense == "<=":
        rhs = (math.ceil(b / s) - 1) * s
    else:
        raise ValueError(f"{c.name}: an equation can't be strict")
    return c.model_copy(update={"rhs": float(rhs)})


def step(c: Constraint) -> Fraction:
    """The smallest positive change in the left side over integer points: g / L."""
    coefs = [_exact(t.coef) for t in c.terms]
    denominator = math.lcm(*(f.denominator for f in coefs))
    return Fraction(math.gcd(*(int(f * denominator) for f in coefs)), denominator)


def _exact(x: float) -> Fraction:
    """The number as written in the text: Fraction("0.6") is 3/5, Fraction(0.6) isn't."""
    return Fraction(repr(x))
