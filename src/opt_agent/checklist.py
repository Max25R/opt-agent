"""The formulation checklist: a separate call that reads the problem text and lists what a
correct formulation must contain, to be compared with Claude's model (audit, finding 2).

**What it sees.** The problem text and the model's variable names, nothing else: no kinds,
bounds, constraints or objective. The names are how the checklist and the model are matched
(the schema asks for names that say what each variable counts or measures), so there's no
fuzzy mapping. A quantity the text needs that isn't among the names can't be written; the
checklist lists it under `cannot_express`, and no flag is raised for it: a missing variable
is a known gap of this check.

**Contamination.** The prompt was written after seeing the M6 test failures. So it's tuned
on dev only (NL4Opt dev, follow-up dev), and any number it gives on M6 test is exploratory:
"prompt designed after seeing these failures".

The diff and its flags are report-only (agent.run with `checklist`): nothing here changes an
answer, a score or a revision.
"""

import math
from typing import Literal

import anthropic
from pydantic import BaseModel, ValidationError

from opt_agent import api
from opt_agent.api import CallInfo, TokenUsage
from opt_agent.formulate import DEFAULT_MODEL, describe
from opt_agent.schema import Constraint, LPModel, StrictModel, Term
from opt_agent.strict import tighten

# ---- what the checklist says ------------------------------------------------------------


class ChecklistTerm(StrictModel):
    var: str
    coef: float


class ChecklistVariable(StrictModel):
    name: str
    kind: Literal["integer", "continuous", "unclear"]
    quote: str


class ChecklistObjective(StrictModel):
    sense: Literal["min", "max"]
    terms: list[ChecklistTerm]
    quote: str


class Requirement(StrictModel):
    quote: str
    terms: list[ChecklistTerm]
    sense: Literal["<=", ">=", "=="]
    rhs: float
    strict: bool  # "more than": also accept the strict reading
    could_be_equal: bool  # "twice as many as": also accept "="
    scope: Literal["single", "combined", "per item"]


class NotARequirement(StrictModel):
    quote: str
    why: str
    # The inequality someone might wrongly make of it; empty terms if there's none.
    terms: list[ChecklistTerm]
    sense: Literal["<=", ">=", "=="]
    rhs: float


class CannotExpress(StrictModel):
    quote: str
    needs: str


class Checklist(StrictModel):
    variables: list[ChecklistVariable]
    objective: ChecklistObjective
    requirements: list[Requirement]
    not_requirements: list[NotARequirement]
    cannot_express: list[CannotExpress]


CHECKLIST_SCHEMA = anthropic.transform_schema(Checklist)

SYSTEM_PROMPT = """\
You are checking an operations research model before it is solved. Read the word problem \
and list what any correct formulation of it must contain. Don't write the model, and don't \
solve the problem.

The model's decision variables are listed by name in <variables>. Use exactly those names \
and no others. If a requirement needs a quantity that isn't one of them, put it in \
cannot_express instead.

- variables: for each listed name, say whether it counts whole things ("integer": vehicles, \
trips, people, products, servings), measures a divisible quantity ("continuous": kilograms, \
acres, hours, money), or the text supports both ("unclear"). Quote the words that decide it.
- objective: its direction (min or max) and its terms over the listed names, with the \
numbers exactly as given. Quote the words it comes from.
- requirements: every requirement the text states, as a linear inequality or equation over \
the listed names. Use the numbers exactly as given, and write percentages as fractions \
(30% as 0.3). Quote the exact words each one comes from.
  - strict: true if the wording is strict ("more than", "must exceed", "fewer than"); still \
write it with >= or <=.
  - could_be_equal: true if the wording names no inequality at all ("twice as many as", \
"three times the number of"), so "=" would be a fair reading too.
  - scope: "combined" if one limit covers several items together, "per item" if it applies \
to each item separately, "single" if it involves one quantity. Decide this from the text: \
"at most 50 cakes of either type" may be one total or one limit per type, so quote why.
  - Leave out non-negativity, unless the text says a quantity can be negative.
- not_requirements: every sentence that states a preference, a motivation, popularity, or \
background rather than a requirement ("prefers", "is more popular", "would like", "sells \
better"), with its quote, why it isn't a requirement, and the inequality someone might \
wrongly make of it (empty terms if there's none). Never turn one of these into a requirement.
- cannot_express: each requirement that needs a quantity not among the listed names, with \
its quote and the quantity it needs.
- Don't add anything the text doesn't state."""


def request_text(problem: str, names: list[str]) -> str:
    listed = "\n".join(names)
    return f"<problem>\n{problem}\n</problem>\n\n<variables>\n{listed}\n</variables>"


def build_request(problem: str, names: list[str], model_id: str = DEFAULT_MODEL) -> dict:
    """The whole request, exactly as sent, hashed, cached and logged. The same pinned
    settings as formulate.build_request."""
    return {
        "model": model_id,
        "max_tokens": api.MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": request_text(problem, names)}],
        "thinking": api.THINKING,
        "output_config": {
            "effort": api.EFFORT,
            "format": {"type": "json_schema", "schema": CHECKLIST_SCHEMA},
        },
    }


class ChecklistReply(BaseModel):
    request: dict
    checklist: Checklist | None  # None if the reply couldn't be used
    error: str | None
    raw_text: str
    stop_reason: str | None
    usage: TokenUsage
    call: CallInfo
    model_id: str

    @property
    def api_failed(self) -> bool:
        return self.call.error is not None


def ask(
    problem: str,
    names: list[str],
    client: anthropic.Anthropic,
    model_id: str = DEFAULT_MODEL,
    cache: api.Cache | None = None,
) -> ChecklistReply:
    request = build_request(problem, names, model_id)
    response, info = api.call(client, request, cache)
    if response is None:
        return ChecklistReply(request=request, checklist=None,
                              error=f"the API call failed: {info.error}", raw_text="",
                              stop_reason=None, usage=api.usage_of(None), call=info,
                              model_id=model_id)  # fmt: skip
    text = api.reply_text(response)
    checklist, error = parse_reply(text, response.stop_reason)
    return ChecklistReply(request=request, checklist=checklist, error=error, raw_text=text,
                          stop_reason=response.stop_reason, usage=api.usage_of(response),
                          call=info, model_id=model_id)  # fmt: skip


def parse_reply(text: str, stop_reason: str | None) -> tuple[Checklist | None, str | None]:
    if stop_reason in api.UNFINISHED:
        return None, api.UNFINISHED[stop_reason]
    try:
        return Checklist.model_validate_json(text), None
    except ValidationError as error:
        return None, describe(error)


# ---- the diff: the checklist against the model -------------------------------------------

TOLERANCE = 1e-6  # after scaling every row so its largest coefficient is 1

FlagKind = Literal[
    "integrality", "coefficient", "missing", "extra", "invented-from-preference", "objective"
]  # fmt: skip


class ChecklistFlag(BaseModel):
    kind: FlagKind
    detail: str
    quote: str | None = None  # the problem's words the checklist cites, if any
    constraint: str | None = None  # the model's row, if one is involved


class ChecklistReview(BaseModel):
    flags: list[ChecklistFlag]
    notes: list[str]  # what couldn't be checked, and why (never a flag)


class _Row(BaseModel):
    label: str  # e.g. "constraint 'budget'", "the upper bound of 'x'"
    coefs: dict[str, float]
    sense: Literal["<=", ">=", "=="]
    rhs: float
    implicit: bool = False  # a default lower bound of 0: matchable, never "extra"


def review(model: LPModel, checklist: Checklist) -> ChecklistReview:
    """Every way the model differs from the checklist, as typed flags. The four checks
    (integrality, requirements, objective, not-requirements) are independent."""
    names = {v.name for v in model.variables}
    notes: list[str] = []
    flags = _integrality(model, checklist, notes)
    flags += _requirements(model, checklist, names, notes)
    flags += _objective(model, checklist, names, notes)
    notes += [f"can't be written with the model's variables (not checked): {c.quote!r} needs "
              f"{c.needs}" for c in checklist.cannot_express]  # fmt: skip
    return ChecklistReview(flags=flags, notes=notes)


def _integrality(model: LPModel, checklist: Checklist, notes: list[str]) -> list[ChecklistFlag]:
    kinds = {v.name: v.integer for v in model.variables}
    flags = []
    for v in checklist.variables:
        if v.name not in kinds:
            notes.append(f"the checklist names a variable the model doesn't have: {v.name!r}")
        elif v.kind == "integer" and not kinds[v.name]:
            flags.append(ChecklistFlag(kind="integrality", quote=v.quote,
                                       detail=f"{v.name!r} counts whole things, but the model "
                                              "makes it continuous"))  # fmt: skip
        elif v.kind == "continuous" and kinds[v.name]:
            flags.append(ChecklistFlag(kind="integrality", quote=v.quote,
                                       detail=f"{v.name!r} is a divisible quantity, but the "
                                              "model makes it integer"))  # fmt: skip
    return flags


def _requirements(
    model: LPModel, checklist: Checklist, names: set[str], notes: list[str]
) -> list[ChecklistFlag]:
    """Pair each requirement with a model row: the same row (or an accepted variant) first,
    then a row on the same variables (a coefficient flag). What's left is missing (a
    requirement) or extra (a row), unless a not-requirement explains the row."""
    rows = _model_rows(model)
    usable = []
    for r in checklist.requirements:
        unknown = sorted({t.var for t in r.terms} - names)
        if unknown:
            notes.append(f"requirement not checked (unknown names {unknown}): {r.quote!r}")
        elif not _coefs(r.terms):
            notes.append(f"requirement not checked (no terms): {r.quote!r}")
        else:
            usable.append(r)
    flags, left = [], []
    for r in usable:
        row = next((x for x in rows if _accepted(r, x, model)), None)
        if row is None:
            left.append(r)
        else:
            rows.remove(row)
    for r in left:
        support = _coefs(r.terms).keys()
        near = [x for x in rows if not x.implicit and x.coefs.keys() == support]
        if near:
            row = min(near, key=lambda x: _differences(r, x))
            rows.remove(row)
            text_says, model_says = _show_requirement(r), _show_row(row)
            detail = f"the text gives {text_says}; the model's {row.label} is {model_says}"
            flags.append(ChecklistFlag(kind="coefficient", quote=r.quote, constraint=row.label,
                                       detail=detail))  # fmt: skip
        else:
            detail = f"no row of the model is {_show_requirement(r)}"
            flags.append(ChecklistFlag(kind="missing", quote=r.quote, detail=detail))
    for row in (x for x in rows if not x.implicit):
        reason = next((n for n in checklist.not_requirements if _explains(n, row, names)), None)
        if reason is not None:
            detail = (f"the model's {row.label} ({_show_row(row)}) makes a requirement of "
                      f"something that isn't one: {reason.why}")  # fmt: skip
            flags.append(ChecklistFlag(kind="invented-from-preference", quote=reason.quote,
                                       constraint=row.label, detail=detail))  # fmt: skip
        else:
            detail = f"the model's {row.label} ({_show_row(row)}) is not among the requirements"
            flags.append(ChecklistFlag(kind="extra", constraint=row.label, detail=detail))
    return flags


def _objective(
    model: LPModel, checklist: Checklist, names: set[str], notes: list[str]
) -> list[ChecklistFlag]:
    o = checklist.objective
    if model.objective.sense != o.sense:
        return [ChecklistFlag(kind="objective", quote=o.quote,
                              detail=f"the text asks to {o.sense}imize; the model "
                                     f"{model.objective.sense}imizes")]  # fmt: skip
    unknown = sorted({t.var for t in o.terms} - names)
    if unknown:
        notes.append(f"objective not checked (unknown names {unknown}): {o.quote!r}")
        return []
    theirs, ours = _scaled(_coefs(o.terms)), _scaled(_coefs(model.objective.terms))
    if theirs.keys() == ours.keys() and all(_close(theirs[v], ours[v]) for v in theirs):
        return []
    text_says = f"{o.sense} {_expression(_coefs(o.terms))}"
    model_says = f"{model.objective.sense} {_expression(_coefs(model.objective.terms))}"
    detail = f"the text's objective is {text_says}; the model's is {model_says}"
    return [ChecklistFlag(kind="objective", quote=o.quote, detail=detail)]


def _model_rows(model: LPModel) -> list[_Row]:
    rows = [_Row(label=f"constraint {c.name!r}", coefs=_coefs(c.terms), sense=c.sense, rhs=c.rhs)
            for c in model.constraints]  # fmt: skip
    for v in model.variables:
        if v.lower is not None:
            rows.append(_Row(label=f"the lower bound of {v.name!r}", coefs={v.name: 1.0},
                             sense=">=", rhs=v.lower, implicit=v.lower == 0))  # fmt: skip
        if v.upper is not None:
            rows.append(_Row(label=f"the upper bound of {v.name!r}", coefs={v.name: 1.0},
                             sense="<=", rhs=v.upper))  # fmt: skip
    return rows


def _variants(r: Requirement, model: LPModel) -> list[tuple]:
    """The canonical forms a correct row may take: as written; "=" if the wording names no
    inequality; and, over integer variables only, the strict reading of strict wording, as
    scoring accepts them (ground_truth.readings)."""
    coefs = _coefs(r.terms)
    found = [_canonical(coefs, r.sense, r.rhs)]
    if r.could_be_equal and r.sense != "==":
        found.append(_canonical(coefs, "==", r.rhs))
    integer = {v.name for v in model.variables if v.integer}
    if r.strict and r.sense != "==" and coefs.keys() <= integer:
        row = Constraint(name="checklist", sense=r.sense, rhs=r.rhs,
                         terms=[Term(var=v, coef=a) for v, a in coefs.items()])  # fmt: skip
        tight = tighten(row)
        found.append(_canonical(coefs, tight.sense, tight.rhs))
    return found


def _accepted(r: Requirement, row: _Row, model: LPModel) -> bool:
    """Is the model's row the requirement, or one of its accepted variants?"""
    return any(_same(v, _canonical(row.coefs, row.sense, row.rhs)) for v in _variants(r, model))


def _explains(n: NotARequirement, row: _Row, names: set[str]) -> bool:
    coefs = _coefs(n.terms)
    if not coefs or not coefs.keys() <= names:
        return False
    return _same(_canonical(coefs, n.sense, n.rhs), _canonical(row.coefs, row.sense, row.rhs))


def _canonical(coefs: dict[str, float], sense: str, rhs: float) -> tuple | None:
    """A row as the set of points it allows: >= as the <= of its negation, scaled so its
    largest coefficient is 1 in size (an equation's first one positive)."""
    if not coefs:
        return None
    if sense == ">=":
        coefs, rhs, sense = {v: -a for v, a in coefs.items()}, -rhs, "<="
    scale = max(abs(a) for a in coefs.values())
    if sense == "==" and coefs[min(coefs)] < 0:
        scale = -scale
    return sense, {v: a / scale for v, a in coefs.items()}, rhs / scale


def _same(a: tuple | None, b: tuple | None) -> bool:
    if a is None or b is None or a[0] != b[0] or a[1].keys() != b[1].keys():
        return False
    return all(_close(a[1][v], b[1][v]) for v in a[1]) and _close(a[2], b[2])


def _differences(r: Requirement, row: _Row) -> int:
    """How far a row on the same variables is from the requirement: direction, coefficients
    and right-hand side, each difference counted once."""
    ours = _canonical(_coefs(r.terms), r.sense, r.rhs)
    theirs = _canonical(row.coefs, row.sense, row.rhs)
    coefficients = sum(not _close(ours[1][v], theirs[1][v]) for v in ours[1])
    return coefficients + (ours[0] != theirs[0]) + (not _close(ours[2], theirs[2]))


def _scaled(coefs: dict[str, float]) -> dict[str, float]:
    scale = max((abs(a) for a in coefs.values()), default=1.0)
    return {v: a / scale for v, a in coefs.items()}


def _close(x: float, y: float) -> bool:
    return math.isclose(x, y, rel_tol=TOLERANCE, abs_tol=TOLERANCE)


def _coefs(terms) -> dict[str, float]:
    return {t.var: float(t.coef) for t in terms if t.coef != 0}


def _expression(coefs: dict[str, float]) -> str:
    return " + ".join(f"{a:g}*{v}" for v, a in coefs.items()).replace("+ -", "- ")


def _show(coefs: dict[str, float], sense: str, rhs: float) -> str:
    return f"{_expression(coefs)} {sense} {rhs:g}"


def _show_requirement(r: Requirement) -> str:
    return _show(_coefs(r.terms), r.sense, r.rhs)


def _show_row(row: _Row) -> str:
    return _show(row.coefs, row.sense, row.rhs)
