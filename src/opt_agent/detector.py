"""A silent-failure detector, tested once (docs/analysis/silent_detector.md, exploratory).

The rule (the owner's): every numeric constant in a problem's text should appear somewhere in
its model, allowing simple unit conversions; an answer whose model misses one is flagged. The
doc fixes the rule and this module implements it. Nothing here was tuned on the answers it's
tested on: the constants below were set before the one run.
"""

import math
import re
from dataclasses import dataclass

from opt_agent.schema import LPModel

# A number right after one of these is part of a name ("Product 1", "Day 3"), not data.
NAMING_WORDS = frozenset({
    "product", "item", "type", "machine", "factory", "plant", "warehouse", "store", "shop",
    "center", "centre", "region", "city", "project", "option", "route", "line", "shift",
    "period", "month", "week", "day", "year", "quarter", "phase", "stage", "step", "level",
    "grade", "model", "version", "class", "category", "zone", "site", "node", "location",
    "depot", "facility", "supplier", "customer", "client", "worker", "employee", "team",
    "vehicle", "truck", "ship", "plane", "car", "crop", "field", "farm", "mine", "job",
    "task", "unit", "room", "area", "station", "port", "market", "source", "destination",
})  # fmt: skip
# The simple unit conversions: percent, minutes and seconds, days, weeks, months, years,
# thousands, millions and billions; each way.
FACTORS = (1.0, 100.0, 60.0, 3600.0, 24.0, 7.0, 12.0, 52.0, 1e3, 1e6, 1e9)
# Relative only: an absolute floor would let a tiny converted target (25 / 1e9) match a
# bound at zero, and zero is never evidence.
TOLERANCE = 1e-6

NUMBER = re.compile(
    r"(?<![\w.#])(?P<sign>-)?(?P<number>\d{1,3}(?:,\d{3})+|\d+)(?:\.(?P<decimals>\d+))?"
    r"(?P<percent>\s*%|\s+percent\b)?"
)
ORDINAL = re.compile(r"(st|nd|rd|th)\b")
FORMAT_WORD = re.compile(r"\s+(decimal|significant|digit)")
WORD_BEFORE = re.compile(r"\b([A-Za-z]+)\s+$")


@dataclass(frozen=True)
class Constant:
    text: str  # as written
    value: float
    percent: bool


@dataclass(frozen=True)
class Verdict:
    constants: list[Constant]
    missing: list[Constant]

    @property
    def flagged(self) -> bool:
        return bool(self.missing)


def constants(text: str) -> list[Constant]:
    """The numbers written in digits, without names, ordinals and format instructions."""
    found = []
    for m in NUMBER.finditer(text):
        after = text[m.end() :]
        if ORDINAL.match(after) or FORMAT_WORD.match(after):
            continue
        before = WORD_BEFORE.search(text[: m.start()])
        if before and before.group(1).lower() in NAMING_WORDS:
            continue
        digits = m["number"].replace(",", "") + (f".{m['decimals']}" if m["decimals"] else "")
        value = float(digits) * (-1 if m["sign"] else 1)
        found.append(Constant(m.group(0).strip(), value, m["percent"] is not None))
    return found


def model_numbers(model: LPModel) -> list[float]:
    """Every coefficient, right-hand side and finite bound."""
    numbers = [t.coef for t in model.objective.terms]
    for c in model.constraints:
        numbers += [t.coef for t in c.terms] + [c.rhs]
    for v in model.variables:
        numbers += [b for b in (v.lower, v.upper) if b is not None and math.isfinite(b)]
    return numbers


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= TOLERANCE * abs(b)


def targets(c: Constant) -> list[float]:
    """What the constant may look like in a model: itself, or converted, up to sign."""
    v = abs(c.value)
    found = [v * f for f in FACTORS] + [v / f for f in FACTORS[1:]]
    if c.percent:
        found += [abs(1 + c.value / 100), abs(1 - c.value / 100)]
    return found


def appears(c: Constant, numbers: list[float]) -> bool:
    if c.value == 0:
        return True  # every variable has a bound at zero, or none
    return any(_close(abs(n), t) for n in numbers for t in targets(c))


def check(text: str, model: LPModel) -> Verdict:
    numbers = model_numbers(model)
    found = constants(text)
    return Verdict(found, [c for c in found if not appears(c, numbers)])
