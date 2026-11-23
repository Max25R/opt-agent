"""Pre-registration section 7: every number in the README comes from a generated results
file, at the precision the README shows it: results/eval.json (milestone 6),
results/followup.json (the follow-up, its pre-registration's section 7),
results/resampling.json (the resampling study, its pre-registration's section 7) or
results/second_model.json (the second-model study, its pre-registration's section 7). The
whole README is checked against all four, without its fenced code blocks (commands and the
diagram), and each results section against its own file. So is the full M6 write-up,
docs/EVALUATION.md (the README's Evaluation section until the README was rewritten on
2026-11-15), every number in
the "The rows" sections of Amendments 4 and 5 (docs/amendments/amendment-4.md,
amendment-5.md), whose rows scripts/amendment4.py and amendment5.py generate into eval.json,
docs/followup/RESULTS.md (scripts/followup_results.py), docs/resampling/RESULTS.md
(scripts/resampling_results.py) and docs/second_model/RESULTS.md
(scripts/second_model_results.py), and the IE 2310 summary
(docs/ie2310/summary.md) against both. Three README bullets are exploratory, not results
(EXPLORATORY): the disagreement detector's line and the explanation checker's (owner's
request, 2026-11-19), and the first screen's headline on explanations (owner's request,
2026-11-22), each checked against its own record in docs/analysis/ and left out of the
rest; so is the cost and latency table near the top (TABLE, owner's request,
2026-11-19), against results/headline.json, which scripts/headline.py computes from the
committed test runs' logs.

How a number in the README is read:
- `-123` in backticks is a problem id, and `complexlp:14` a follow-up label: some string in
  the results file must equal it. Any other code span with a letter in it (a path, a hash,
  a model id) isn't a result.
- A sign is part of a number after a space or "(": `-1.7` must equal a negative value.
- `12.3%` is a rate: some value times 100, rounded to the shown decimals, must equal it. In a
  range such as `93.4–98.0%`, both ends are rates.
- `$0.150` and `3.8` must equal some value rounded to the shown decimals, and `2.3e-6` some
  value at the shown significant digits.
- A whole number such as `264` must equal some whole value exactly.
- second_model.json stores each paired difference ("difference", "difference_ci95") as a
  share, and the README gives it in percentage points, so each of those counts times 100 too:
  `-5.8 pp` is a difference of -0.058.

Not results, so skipped: model names ("Claude Haiku 5.5"), amendment numbers, percentile
names ("p95"), link targets, dates, hypothesis names ("H1", "R2", "S1"), the benchmark's name
("NL4Opt"), section, condition, sample, stage and deviation numbers ("section 4", "5b",
"conditions 2 to 4", "samples 3 to 7", "samples 1 and 2", "stage 2", "deviation 1"), a
significance level ("alpha 0.05") and an interval's ("95% Wilson"),
"SHA-256", a cited
paper's venue and year ("ICML 2024"), license versions ("CC BY-SA 4.0"), course numbers
("IE 2310"), Python versions ("Python 3.12"), and fenced code blocks. Numbers written as
words aren't checked, so results are written in digits.

The check is by value, not by place: a small whole number like 3 matches many values. It
catches numbers that appear nowhere in eval.json, such as a stale or retyped result.
"""

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
EVALUATION = ROOT / "docs" / "EVALUATION.md"
AMENDMENT_4 = ROOT / "docs" / "amendments" / "amendment-4.md"
AMENDMENT_5 = ROOT / "docs" / "amendments" / "amendment-5.md"
EVAL = ROOT / "results" / "eval.json"
FOLLOWUP = ROOT / "results" / "followup.json"
FOLLOWUP_RESULTS = ROOT / "docs" / "followup" / "RESULTS.md"
RESAMPLING = ROOT / "results" / "resampling.json"
RESAMPLING_RESULTS = ROOT / "docs" / "resampling" / "RESULTS.md"
SECOND_MODEL = ROOT / "results" / "second_model.json"
SECOND_MODEL_RESULTS = ROOT / "docs" / "second_model" / "RESULTS.md"
# Each exploratory README bullet, by the words it starts with, and the records it comes from
# (the explanation checker's also gives ADR-0009's headline, 21 → 10, from limits_checker.json:
# the owner's request, 2026-11-21, which replaced the rule's count from limits_claims.json; the
# first screen's third headline bullet gives it again: the owner's request, 2026-11-22).
ANALYSIS = ROOT / "docs" / "analysis"
EXPLORATORY = {
    "- **Exploratory: disagreement between attempts as a warning.**":
        (ANALYSIS / "disagreement_detector.json",),
    "- **Exploratory: the explanation checker, on dev.**":
        (ANALYSIS / "explanation_checker.json", ANALYSIS / "limits_checker.json"),
    "- **Exploratory: explanations with a false claim, halved.**":
        (ANALYSIS / "limits_checker.json",),
}  # fmt: skip
WRITE_UP = {"limits_checker": "limits_claims"}  # a record whose write-up has another name
# The README's cost and latency table (owner's request, 2026-11-19): numbers per answer from
# the committed test runs' logs, not results, checked against their own record
# (scripts/headline.py writes it) and left out of the rest.
HEADLINE = ROOT / "results" / "headline.json"
TABLE = ("<!-- cost and latency: results/headline.json -->", "<!-- end of cost and latency -->")
IE2310_SUMMARY = ROOT / "docs" / "ie2310" / "summary.md"
# Each checked document, the section of it that reports results (a heading with its level;
# None: all of it), the results files its numbers come from, how many problem ids it must
# cite at least, and how many numbers it must have at least (so a check can't pass by
# finding nothing).
CHECKED = [
    (README, None, (EVAL, FOLLOWUP, RESAMPLING, SECOND_MODEL), 0, 60),
    (README, "### NL4Opt", (EVAL,), 0, 25),
    (README, "### Harder problems", (FOLLOWUP,), 0, 30),
    (README, "### Resampling", (RESAMPLING,), 0, 12),
    (README, "### Second model", (SECOND_MODEL,), 0, 30),
    (EVALUATION, None, (EVAL,), 2, 40),
    (AMENDMENT_4, "## The rows", (EVAL,), 2, 40),
    (AMENDMENT_5, "## The rows", (EVAL,), 2, 40),
    (FOLLOWUP_RESULTS, None, (FOLLOWUP,), 0, 40),
    (RESAMPLING_RESULTS, None, (RESAMPLING,), 0, 40),
    (SECOND_MODEL_RESULTS, None, (SECOND_MODEL,), 0, 60),
    (IE2310_SUMMARY, None, (EVAL, FOLLOWUP), 0, 25),
]

NOT_RESULTS = [
    r"\]\([^)]*\)",  # a link's target
    r"Claude (?:Haiku|Sonnet|Opus) \d+(?:\.\d+)?",  # a model's name
    r"Amendments? \d+(?: and \d+)?",  # a document reference
    r"\bp\d\d\b",  # a percentile's name, as in "latency p50 / p95"
    r"\b\d{4}-\d{2}-\d{2}\b",  # a date
    r"SHA-256",  # a hash's name
    r"\b[HRS][12]\b",  # a hypothesis's name (the follow-up's H1, R1, the second model's S1)
    r"\b[Ss]ections? \d+\b",  # a section of a pre-registration
    r"\b5[abc]\b",  # a subsection of the follow-up's section 5
    r"\b[Cc]onditions? \d(?: to \d)?\b",  # a condition's number
    r"\b[Ss]amples? \d(?: (?:to|and) \d)?\b",  # a sample's number, as in "samples 3 to 7"
    r"\b[Ss]tages? \d\b",  # a stage of the second-model study
    r"\b[Dd]eviations? \d\b",  # a recorded deviation, as in "deviation 1"
    r"\balpha 0\.05\b",  # a significance level
    r"\b95%(?= (?:Wilson|CI|bootstrap|interval|confidence))",  # an interval's level
    r"\b(?:ICML|ICLR|NeurIPS) \d{4}\b",  # a cited paper's venue and year
    r"\bCC BY(?:-[A-Z]{2})* \d\.\d\b",  # a license's version
    r"\bIE \d{4}\b",  # a course number
    r"\bPython \d+\.\d+\b",  # a Python version, as in "Python 3.12 or newer"
    r"\bNL4Opt\b",  # the benchmark's name, whose 4 isn't a result
]
FENCED = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
PROBLEM_ID = re.compile(r"`(-?\d+)`")
LABEL = re.compile(r"`((?:complexlp|industryor):\d+)`")
CODE_SPAN = re.compile(r"`[^`\n]*[A-Za-z_][^`\n]*`")
RATE_RANGE = re.compile(r"(\d+(?:\.\d+)?)–(\d+(?:\.\d+)?)%")
NUMBER = re.compile(r"(?:(?<=[\s(])[+-])?\d+(?:\.\d+)?(?:e-?\d+)?%?")


def bullet(text: str, marker: str) -> str:
    """An exploratory bullet, from its marker to the next bullet or blank line."""
    start = text.index(marker)
    ends = [i for i in (text.find("\n- ", start + 1), text.find("\n\n", start)) if i != -1]
    return text[start : min(ends)]


def table(text: str) -> str:
    """The README's cost and latency table, between its two markers."""
    start, end = text.index(TABLE[0]), text.index(TABLE[1]) + len(TABLE[1])
    return text[start:end]


def section(text: str, heading: str | None) -> str:
    """From the line starting with `heading` ("## The rows", "### NL4Opt") to the next heading
    of its level or higher; the whole text for None. Fenced code blocks are left out, and so
    are the exploratory bullets and the cost and latency table (each checked on its own)."""
    text = FENCED.sub(" ", text)
    for marker in EXPLORATORY:
        if marker in text:
            text = text.replace(bullet(text, marker), " ")
    if TABLE[0] in text:
        text = text.replace(table(text), " ")
    if heading is None:
        return text
    level = heading.split(" ")[0]
    start = text.index(f"\n{heading}")
    ends = [text.find(f"\n{'#' * n} ", start + 1) for n in range(1, len(level) + 1)]
    ends = [e for e in ends if e != -1]
    return text[start : min(ends) if ends else len(text)]


POINTS = ("difference", "difference_ci95")  # second_model.json's shares, shown in points


def leaves(data) -> tuple[list[float], set[str]]:
    """Every number and every string in eval.json (booleans aren't numbers here), and each
    of second_model.json's paired differences in percentage points too."""
    numbers, strings = [], set()
    stack = [data]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            stack += item.values()
            for key in POINTS:
                value = item.get(key)
                for share in value if isinstance(value, list) else [value]:
                    if isinstance(share, float):
                        numbers.append(100 * share)
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
    if "e" in token:  # at the significant digits shown: 2.3e-6 is 2 of them
        digits = len(token.split("e")[0].replace(".", ""))
        return any(float(f"{v:.{digits - 1}e}") == float(token) for v in numbers)
    decimals = len(token.split(".")[1]) if "." in token else 0
    shown = float(token)
    scale = 100 if rate else 1
    if decimals == 0 and not rate:
        return any(v == shown for v in numbers)  # a whole number: exactly
    return any(round(v * scale, decimals) == shown for v in numbers)


def unmatched(section: str, data: dict) -> list[str]:
    numbers, strings = leaves(data)
    missing = [i for i in PROBLEM_ID.findall(section) if i not in strings]
    missing += [i for i in LABEL.findall(section) if i not in strings]
    section = CODE_SPAN.sub(" ", PROBLEM_ID.sub(" ", LABEL.sub(" ", section)))
    for pattern in NOT_RESULTS:
        section = re.sub(pattern, " ", section)
    for low, high in RATE_RANGE.findall(section):
        missing += [f"{x}% (in a range)" for x in (low, high) if not matches(x, numbers, rate=True)]
    section = RATE_RANGE.sub(" ", section)
    missing += [t for t in NUMBER.findall(section.replace("$", " ")) if not matches(t, numbers)]
    return missing


@pytest.fixture(scope="module", params=CHECKED, ids=lambda c: f"{c[0].name}: {c[1] or 'all'}")
def section_and_data(request):
    path, heading, results, min_ids, min_numbers = request.param
    for file in results:
        if not file.exists():
            pytest.fail(f"{file.relative_to(ROOT)} is missing: see its generating script")
    data = [json.loads(file.read_text()) for file in results]  # leaves() walks a list too
    return section(path.read_text(), heading), data, min_ids, min_numbers


def test_every_number_in_a_checked_section_is_in_its_results_file(section_and_data):
    section, data, _, _ = section_and_data
    assert unmatched(section, data) == []


def test_the_section_has_results_to_check(section_and_data):
    """Guards against a check that passes because it found nothing."""
    section, _, min_ids, min_numbers = section_and_data
    assert len(NUMBER.findall(section)) >= min_numbers
    assert len(PROBLEM_ID.findall(section)) >= min_ids


@pytest.mark.parametrize("marker", EXPLORATORY, ids=lambda m: m.split(":")[1][:20])
def test_each_exploratory_bullet_comes_from_its_own_record(marker):
    text = README.read_text()
    line = bullet(text, marker)
    records = EXPLORATORY[marker]
    for record in records:
        assert f"docs/analysis/{WRITE_UP.get(record.stem, record.stem)}.md" in line  # each write-up
    assert unmatched(line, [json.loads(r.read_text()) for r in records]) == []
    assert len(NUMBER.findall(line)) >= 4  # it has numbers to check
    assert marker not in section(text, None)  # and only here


def test_the_cost_and_latency_table_comes_from_its_own_record():
    text = README.read_text()
    block = table(text)
    assert "scripts/headline.py" in block  # it says where its numbers come from
    assert unmatched(block, [json.loads(HEADLINE.read_text())]) == []
    assert len(NUMBER.findall(block)) >= 25  # it has numbers to check
    assert text.count(TABLE[0]) == 1 and TABLE[0] not in section(text, None)  # and only here


def test_fenced_code_and_citations_arent_results():
    text = "```bash\ndocker run -p 8000:8000 x\n```\nOptiMUS (ICML 2024), CC BY-SA 4.0"
    assert unmatched(section(text, None), {"n": 1}) == []


@pytest.mark.parametrize(
    ("text", "bad"),
    [
        ("96.5% accuracy", ["96.5%"]),  # 0.9635 is 96.4%
        ("93.4–98.1%", ["98.1% (in a range)"]),
        ("cost $0.125", ["0.125"]),
        ("265 of 274", ["265"]),
        ("problem `12345`", ["12345"]),
        ("problem `complexlp:99`", ["complexlp:99"]),
        ("a difference of (-0.4 pp", ["-0.4"]),  # the sign counts
        ("H2 +6.3 pp", ["+6.3"]),
    ],
)
def test_a_number_not_in_eval_json_is_caught(text, bad):
    data = {"rate": 0.9635, "low": 0.934, "high": 0.980, "usd": 0.1242686, "right": 264,
            "n": 274, "ids": ["431521997"], "pp": 0.4, "diff": 6.25}  # fmt: skip
    assert unmatched(text, data) == bad


def test_numbers_that_are_in_eval_json_pass():
    data = {"rate": 0.9635, "low": 0.934, "high": 0.980, "usd": 0.1242686, "right": 264,
            "n": 274, "ids": ["431521997"], "tolerance": 1e-6}  # fmt: skip
    text = "96.4% (93.4–98.0%), $0.124, 264 of 274, `431521997`, tolerance 1e-6, Claude Opus 5.5"
    assert unmatched(text, data) == []


def test_resampling_forms_pass():
    data = {"p": 2.3019010408718335e-06, "q": 3.982601372645805e-06, "tolerance": 1e-6}
    text = ("R1 is supported: p = 2.3e-6 (4.0e-6 without the disputed problems), samples 3 to "
            "7, sample 3, alpha 0.05, 95% Wilson, R2, tolerance 1e-6")  # fmt: skip
    assert unmatched(text, data) == []
    assert unmatched("p = 2.4e-6, or 2.31e-6", data) == ["2.4e-6", "2.31e-6"]


def test_second_model_forms_pass():
    """A difference stored as a share passes in points; nothing else is scaled."""
    data = {"s1": {"difference": -0.05785, "difference_ci95": [-0.13223, 0.00826],
                   "p_value": 0.16707, "sonnet_right": 88}}  # fmt: skip
    text = ("S1: 88, -5.8 pp (95% CI -13.2 to +0.8), p 0.17, stage 2, samples 1 and 2, "
            "[deviation 1](x.md), Claude Sonnet 5.5")  # fmt: skip
    assert unmatched(text, data) == []
    assert unmatched("a gain of -5.9 pp, 16.7 pp, 8800", data) == ["-5.9", "16.7", "8800"]


def test_follow_up_forms_pass():
    data = {"labels": ["complexlp:14"], "low": -1.66, "diff": 6.34, "bound": 4}
    text = (
        "`complexlp:14` (-1.7 to +6.3 pp), within +/-4 pp, H1, section 5b, conditions 2 "
        "to 4, approved 2026-11-13, `runs/followup-test`, SHA-256 `78c9c9a5ae58`"
    )
    assert unmatched(text, data) == []
