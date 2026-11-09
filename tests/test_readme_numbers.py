"""Pre-registration section 7: every number in the README's Evaluation section comes from
results/eval.json, at the precision the README shows it. So does every number in the "The
rows" sections of Amendments 4 and 5 (docs/amendments/amendment-4.md, amendment-5.md), whose
rows scripts/amendment4.py and amendment5.py generate into eval.json.

How a number in the README is read:
- `-123` in backticks is a problem id: some string in eval.json must equal it.
- `12.3%` is a rate: some value times 100, rounded to the shown decimals, must equal it. In a
  range such as `93.4–98.0%`, both ends are rates.
- `$0.150`, `3.8` and `1e-6` must equal some value rounded to the shown decimals (exactly,
  for scientific notation).
- A whole number such as `264` must equal some whole value exactly.

Not results, so skipped: model names ("Claude Haiku 5.5"), amendment numbers, percentile
names ("p95"), and link targets. Numbers written as words aren't checked, so results are
written in digits.

The check is by value, not by place: a small whole number like 3 matches many values. It
catches numbers that appear nowhere in eval.json, such as a stale or retyped result.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
AMENDMENT_4 = ROOT / "docs" / "amendments" / "amendment-4.md"
AMENDMENT_5 = ROOT / "docs" / "amendments" / "amendment-5.md"
EVAL = ROOT / "results" / "eval.json"
# Each checked document, and the section of it that reports results.
CHECKED = [(README, "Evaluation"), (AMENDMENT_4, "The rows"), (AMENDMENT_5, "The rows")]

NOT_RESULTS = [
    r"\]\([^)]*\)",  # a link's target
    r"Claude (?:Haiku|Sonnet|Opus) \d+(?:\.\d+)?",  # a model's name
    r"Amendments? \d+(?: and \d+)?",  # a document reference
    r"\bp\d\d\b",  # a percentile's name, as in "latency p50 / p95"
]
PROBLEM_ID = re.compile(r"`(-?\d+)`")
RATE_RANGE = re.compile(r"(\d+(?:\.\d+)?)–(\d+(?:\.\d+)?)%")
NUMBER = re.compile(r"\d+(?:\.\d+)?(?:e-?\d+)?%?")


def section(text: str, heading: str) -> str:
    start = text.index(f"\n## {heading}\n")
    end = text.find("\n## ", start + 1)
    return text[start : end if end != -1 else len(text)]


def leaves(data) -> tuple[list[float], set[str]]:
    """Every number and every string in eval.json (booleans aren't numbers here)."""
    numbers, strings = [], set()
    stack = [data]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            stack += item.values()
        elif isinstance(item, list):
            stack += item
        elif isinstance(item, str):
            strings.add(item)
        elif isinstance(item, (int, float)) and not isinstance(item, bool):
            numbers.append(item)
    return numbers, strings


def matches(token: str, numbers: list[float], rate: bool = False) -> bool:
    """Is `token`, as the README shows it, some value in eval.json?"""
    if token.endswith("%"):
        token, rate = token[:-1], True
    if "e" in token:
        return any(v == float(token) for v in numbers)
    decimals = len(token.split(".")[1]) if "." in token else 0
    shown = float(token)
    scale = 100 if rate else 1
    if decimals == 0 and not rate:
        return any(v == shown for v in numbers)  # a whole number: exactly
    return any(round(v * scale, decimals) == shown for v in numbers)


def unmatched(section: str, data: dict) -> list[str]:
    numbers, strings = leaves(data)
    missing = [i for i in PROBLEM_ID.findall(section) if i not in strings]
    section = PROBLEM_ID.sub(" ", section)
    for pattern in NOT_RESULTS:
        section = re.sub(pattern, " ", section)
    for low, high in RATE_RANGE.findall(section):
        missing += [f"{x}% (in a range)" for x in (low, high) if not matches(x, numbers, rate=True)]
    section = RATE_RANGE.sub(" ", section)
    missing += [t for t in NUMBER.findall(section.replace("$", " ")) if not matches(t, numbers)]
    return missing


@pytest.fixture(scope="module", params=CHECKED, ids=lambda c: f"{c[0].name}: {c[1]}")
def section_and_data(request):
    if not EVAL.exists():
        pytest.fail("results/eval.json is missing: python scripts/eval_json.py")
    path, heading = request.param
    return section(path.read_text(), heading), json.loads(EVAL.read_text())


def test_every_number_in_a_checked_section_is_in_eval_json(section_and_data):
    section, data = section_and_data
    assert unmatched(section, data) == []


def test_the_section_has_results_to_check(section_and_data):
    """Guards against a check that passes because it found nothing."""
    section, _ = section_and_data
    assert len(NUMBER.findall(section)) > 40
    assert len(PROBLEM_ID.findall(section)) >= 2


@pytest.mark.parametrize(
    ("text", "bad"),
    [
        ("96.5% accuracy", ["96.5%"]),  # 0.9635 is 96.4%
        ("93.4–98.1%", ["98.1% (in a range)"]),
        ("cost $0.125", ["0.125"]),
        ("265 of 274", ["265"]),
        ("problem `12345`", ["12345"]),
    ],
)
def test_a_number_not_in_eval_json_is_caught(text, bad):
    data = {"rate": 0.9635, "low": 0.934, "high": 0.980, "usd": 0.1242686, "right": 264,
            "n": 274, "ids": ["431521997"]}  # fmt: skip
    assert unmatched(text, data) == bad


def test_numbers_that_are_in_eval_json_pass():
    data = {"rate": 0.9635, "low": 0.934, "high": 0.980, "usd": 0.1242686, "right": 264,
            "n": 274, "ids": ["431521997"], "tolerance": 1e-6}  # fmt: skip
    text = "96.4% (93.4–98.0%), $0.124, 264 of 274, `431521997`, tolerance 1e-6, Claude Opus 5.5"
    assert unmatched(text, data) == []
