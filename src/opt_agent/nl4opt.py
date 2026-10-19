"""Convert NL4Opt's human-annotated formulations into our LPModel schema.

NL4Opt (github.com/nl4opt/nl4opt-competition, MIT License) annotates each problem with an
objective declaration and typed constraint declarations, but gives no answers. The meaning
of each declaration type follows the official baseline's `convert_to_canonical`, with two
deliberate differences where that code is mathematically wrong. (Its bugs never mattered
there: the competition compared canonical forms built by that same code instead of solving
them.)

- A variable left out of a `linear` constraint has coefficient 0 (the baseline uses 1).
- `x <= y` has right-hand side 0 (the baseline uses 1).

Every other judgment call is written into the problem's notes.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ValidationError

from opt_agent.schema import Constraint, LPModel, Objective, Term, Variable


class ConversionError(ValueError):
    """The annotation can't be turned into a model; the message says why."""


class Note(BaseModel):
    """One judgment call made while converting a problem."""

    kind: Literal[
        "strict-wording",  # "must exceed" etc., annotated (and modeled) as >= or <=
        "unlisted-variable",  # a linear constraint omits a variable: coefficient 0
        "share-above-1",  # a ratio annotated as "60" for 60%
        "empty-objvar",  # "minimize the total number" with no variables listed
        "duplicate-var",  # `vars` lists the same variable twice
        "order-mapping-overridden",  # the mention names a different variable than order_mapping
    ]
    detail: str


@dataclass
class Conversion:
    model: LPModel
    notes: list[Note]  # every assumption made for this problem


def load_split(path: Path) -> dict[str, dict]:
    """Problem id -> raw annotation, in file order. Each line is {"<id>": {...}}."""
    problems = {}
    for line in path.read_text().splitlines():
        [(problem_id, annotation)] = json.loads(line).items()
        problems[problem_id] = annotation
    return problems


def convert(annotation: dict) -> Conversion:
    """Build a continuous LPModel (all variables >= 0) from one problem's annotation."""
    notes: list[Note] = []
    try:
        names = _variable_names(annotation, notes)
        objective = _objective(annotation["obj_declaration"], annotation, names, notes)
        constraints = [
            _constraint(i, decl, annotation, names, notes)
            for i, decl in enumerate(annotation["const_declarations"])
        ]
        model = LPModel(
            variables=[Variable(name=n) for n in names],
            objective=objective,
            constraints=constraints,
        )
    except KeyError as missing:
        raise ConversionError(f"annotation is missing {missing}") from None
    except ValidationError as error:
        reasons = "; ".join(e["msg"] for e in error.errors())
        raise ConversionError(f"the converted model is invalid: {reasons}") from None
    return Conversion(model=model, notes=notes)


# ---- numbers ---------------------------------------------------------------------------

_UNITS = (
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen"
).split()
_TENS = "twenty thirty forty fifty sixty seventy eighty ninety".split()
_NUMBER_WORDS = {w: i for i, w in enumerate(_UNITS)} | {w: 20 + 10 * i for i, w in enumerate(_TENS)}

_FRACTIONS_AND_MULTIPLES = {
    "half": 1 / 2, "a half": 1 / 2, "one half": 1 / 2,
    "third": 1 / 3, "a third": 1 / 3, "one third": 1 / 3,
    "quarter": 1 / 4, "a quarter": 1 / 4, "fourth": 1 / 4, "a fourth": 1 / 4,
    "fifth": 1 / 5, "a fifth": 1 / 5,
    "twice": 2, "thrice": 3,
}  # fmt: skip


def parse_number(text: str) -> float:
    """Read an annotated number such as '4,000', '$500', '60%', 'thirty percent',
    'twice', 'three times', 'a third', or '8000 minutes'.

    Anything else raises ConversionError: a wrong guess here would silently corrupt the
    ground truth, so unreadable numbers fail loudly instead.
    """
    s = text.strip().lower().replace(",", "").replace("$", "").rstrip(".")
    scale = 1.0
    if s.endswith(("%", "percent")):
        s, scale = s.removesuffix("%").removesuffix("percent").strip(), 0.01
    s = s.removesuffix("times").strip()  # "three times" -> "three"
    value = _read_number(s)
    if value is None:
        raise ConversionError(f"can't read the number {text!r}")
    return value * scale


def _read_number(s: str) -> float | None:
    if s in _FRACTIONS_AND_MULTIPLES:
        return _FRACTIONS_AND_MULTIPLES[s]
    digits = re.fullmatch(r"(-?\d+(?:\.\d+)?)(?: [a-z]+)*", s)  # "8000 minutes" -> 8000
    if digits:
        return float(digits.group(1))
    return _number_words(s)


def _number_words(s: str) -> float | None:
    """'one hundred thousand' -> 100000.0; None unless every word is a number word."""
    words = s.replace("-", " ").split()
    if not words:
        return None
    total = current = 0
    for word in words:
        if word in _NUMBER_WORDS:
            current += _NUMBER_WORDS[word]
        elif word == "hundred":
            current *= 100
        elif word in ("thousand", "million"):
            total += current * (1_000 if word == "thousand" else 1_000_000)
            current = 0
        else:
            return None
    return float(total + current)


# ---- directions and operators ----------------------------------------------------------

_OPERATORS = {"LESS_OR_EQUAL": "<=", "GREATER_OR_EQUAL": ">="}

# Wording that implies an operator ("at least" -> >=), flipped when negated ("no more than").
_IMPLIES_GE = re.compile(r"\b(at least|minimum|more|exceeds?|larger|large than|greater)\b")
_IMPLIES_LE = re.compile(r"\b(at most|maximum|most|less|fewer|below)\b")
# Wording that means a strict inequality, unless it's negated.
_STRICT = re.compile(r"\b(more|less than|fewer|exceeds?|larger|large than|greater than|below)\b")
_NEGATED = re.compile(r"\b(no|not|cannot|never|without)\b")


def objective_sense(direction: str) -> str:
    d = direction.strip().lower()
    if d.startswith("max") or d == "highest":
        return "max"
    if d.startswith("min") or d in ("lowest", "reduce", "decrease"):
        return "min"
    raise ConversionError(f"unknown objective direction {direction!r}")


def implied_operator(direction: str, document: str) -> str | None:
    """The operator a constraint's wording implies, or None if the wording doesn't say."""
    d = direction.lower()
    ge, le = bool(_IMPLIES_GE.search(d)), bool(_IMPLIES_LE.search(d))
    if ge == le:  # no hint, or mixed hints
        return None
    if _negated(direction, document):
        ge = not ge
    return ">=" if ge else "<="


def is_strict(direction: str, document: str) -> bool:
    return bool(_STRICT.search(direction.lower())) and not _negated(direction, document)


def _negated(direction: str, document: str) -> bool:
    """Is the wording negated, as in "no more than"?

    The annotated phrase is often clipped ("more than" from "does not want to spend more
    than"), so this also checks the few characters just before it in the problem text.
    """
    d, text = direction.lower(), document.lower()
    before = text.partition(d)[0][-25:] if d and d in text else ""
    return bool(_NEGATED.search(d) or _NEGATED.search(before))


# ---- variables, objective, constraints -------------------------------------------------


def _variable_names(annotation: dict, notes: list[Note]) -> list[str]:
    """Canonical variable names, in order_mapping index order."""
    order = annotation["order_mapping"]
    by_index: dict[int, str] = {}
    for name in annotation["vars"]:
        by_index.setdefault(order[name], name)
    if len(by_index) < len(annotation["vars"]):
        detail = f"`vars` lists a variable twice ({annotation['vars']}); kept one copy"
        notes.append(Note(kind="duplicate-var", detail=detail))
    if sorted(by_index) != list(range(len(by_index))):
        raise ConversionError(f"order_mapping indices {sorted(by_index)} aren't 0..n-1")
    names = [by_index[i] for i in range(len(by_index))]
    if len({tuple(_words(n)) for n in names}) < len(names):
        raise ConversionError(f"variables {names} include one thing annotated twice")
    return names


def _resolve(mention: str, annotation: dict, names: list[str], notes: list[Note]) -> str:
    """'truck' -> 'trucks': which variable a declaration's mention refers to.

    The variable name the mention contains decides ("economical mobile phone" ->
    "economical"). order_mapping, which is hand-annotated and sometimes wrong, decides
    only when the name doesn't (e.g. "Firemen" -> "firefighters").
    """
    index = annotation["order_mapping"].get(mention)
    by_index = names[index] if index is not None and index < len(names) else None
    by_name = _named_variable(mention, names)
    if by_name and by_index and by_name != by_index:
        detail = f"order_mapping maps {mention!r} to {by_index!r}, but it names {by_name!r}"
        note = Note(kind="order-mapping-overridden", detail=detail)
        if note not in notes:
            notes.append(note)
    name = by_name or by_index
    if name is None:
        raise ConversionError(f"unknown variable mention {mention!r}")
    return name


def _named_variable(mention: str, names: list[str]) -> str | None:
    """The one variable whose name appears in the mention, or else the one variable whose
    name contains the mention. None if that isn't a single variable."""
    hits = [n for n in names if _contains(mention, n)]
    if len(hits) != 1:
        hits = [n for n in names if _contains(n, mention)]
    return hits[0] if len(hits) == 1 else None


def _contains(text: str, phrase: str) -> bool:
    """Does `text` contain `phrase` as whole words, ignoring case and a plural "s"?"""
    t, p = _words(text), _words(phrase)
    return bool(p) and any(t[i : i + len(p)] == p for i in range(len(t) - len(p) + 1))


def _words(text: str) -> list[str]:
    return [w.removesuffix("s") for w in re.findall(r"[a-z0-9]+", text.lower())]


def _objective(decl: dict, annotation: dict, names: list[str], notes: list[Note]) -> Objective:
    if decl["type"] == "objective":
        pairs = [(m, parse_number(v)) for m, v in decl["terms"].items()]
    elif decl["type"] == "objvar":  # e.g. "minimize the total number of vehicles"
        listed = decl["vars"]
        if not listed:
            detail = f"objective {decl['name']!r} lists no variables; used their sum"
            notes.append(Note(kind="empty-objvar", detail=detail))
            listed = names
        pairs = [(m, 1.0) for m in listed]
    else:
        raise ConversionError(f"unknown objective type {decl['type']!r}")
    sense = objective_sense(decl["direction"])
    return Objective(sense=sense, terms=_terms(pairs, "objective", annotation, names, notes))


def _constraint(
    index: int, decl: dict, annotation: dict, names: list[str], notes: list[Note]
) -> Constraint:
    kind = decl["type"]
    label = f"c{index}_{kind}"
    sense = _OPERATORS.get(decl["operator"])
    if sense is None:
        raise ConversionError(f"{label}: unknown operator {decl['operator']!r}")
    direction, document = decl.get("direction", ""), annotation["document"]
    implied = implied_operator(direction, document)
    if implied is not None and implied != sense:
        raise ConversionError(f"{label}: text says {direction!r}, but the operator is {sense}")
    if is_strict(direction, document):
        detail = f"{label}: text says {direction!r} (strict); modeled as {sense}"
        notes.append(Note(kind="strict-wording", detail=detail))

    rhs = 0.0
    if kind == "linear":  # sum of coef * var  op  limit
        pairs = [(m, parse_number(v)) for m, v in decl["terms"].items()]
        rhs = parse_number(decl["limit"])
    elif kind == "sum":  # sum of all vars  op  limit
        pairs = [(n, 1.0) for n in names]
        rhs = parse_number(decl["limit"])
    elif kind in ("upperbound", "lowerbound"):  # var  op  limit
        pairs = [(decl["var"], 1.0)]
        rhs = parse_number(decl["limit"])
    elif kind == "xy":  # x  op  y
        pairs = [(decl["x_var"], 1.0), (decl["y_var"], -1.0)]
    elif kind == "xby":  # x  op  param * y
        pairs = [(decl["x_var"], 1.0), (decl["y_var"], -parse_number(decl["param"]))]
    elif kind == "ratio":  # var  op  share * (sum of all vars)
        share = _share(decl["limit"], label, notes)
        pairs = [(n, -share) for n in names] + [(decl["var"], 1.0)]
    else:
        raise ConversionError(f"{label}: unknown constraint type {kind!r}")
    terms = _terms(pairs, label, annotation, names, notes, merging_is_expected=kind == "ratio")
    if kind == "linear":
        _note_unlisted(terms, label, names, notes)
    return Constraint(name=label, terms=terms, sense=sense, rhs=rhs)


def _share(text: str, label: str, notes: list[Note]) -> float:
    share = parse_number(text)
    if share > 1:  # "at most 60% of carts" annotated as "60"
        detail = f"{label}: share {text!r} is above 1; read it as {share:g}%"
        notes.append(Note(kind="share-above-1", detail=detail))
        share /= 100
    return share


def _terms(
    pairs: list[tuple[str, float]],
    label: str,
    annotation: dict,
    names: list[str],
    notes: list[Note],
    merging_is_expected: bool = False,
) -> list[Term]:
    """Resolve mentions to variables.

    Two different mentions resolving to one variable means order_mapping is wrong (the
    annotator meant two variables), so that's an error. Only `ratio` repeats a variable
    on purpose, and there the coefficients add up.
    """
    if not pairs:
        raise ConversionError(f"{label}: the annotation has no terms")
    coefs: dict[str, float] = {}
    for mention, coef in pairs:
        name = _resolve(mention, annotation, names, notes)
        if name in coefs and not merging_is_expected:
            raise ConversionError(f"{label}: two mentions resolve to {name!r}")
        coefs[name] = coefs.get(name, 0.0) + coef
    return [Term(var=name, coef=coef) for name, coef in coefs.items()]


def _note_unlisted(terms: list[Term], label: str, names: list[str], notes: list[Note]) -> None:
    listed = {t.var for t in terms}
    unlisted = [n for n in names if n not in listed]
    if unlisted:
        detail = f"{label}: {unlisted} not listed, so coefficient 0 (the official converter: 1)"
        notes.append(Note(kind="unlisted-variable", detail=detail))
