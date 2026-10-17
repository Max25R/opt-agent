"""Cross-check against ORLM's NL4Opt answers, a third-party answer set made with GPT-4.

ORLM's problems carry only the question text, so they're matched to NL4Opt by normalized
text. A disagreement means "look at this problem", not "we're wrong": either side can be
the one in error.
"""

import json
import math
from pathlib import Path
from typing import Literal

MATCH_TOLERANCE = 1e-4  # the same relative tolerance the evaluation will use

# How ORLM marks a problem whose program found no optimum.
NO_SOLUTION_MARKERS = {"no best solution", "-99999", "-99999.0"}

Verdict = Literal[
    "matches both",
    "matches IP only",
    "matches LP only",
    "both find no optimum",
    "only we find an optimum",
    "only ORLM finds an optimum",
    "matches neither",
]


def load_answers(path: Path) -> dict[str, str]:
    """Normalized question text -> ORLM's answer, exactly as published."""
    answers = {}
    for line in path.read_text().splitlines():
        if line.strip():
            row = json.loads(line)
            answers[normalize(row["en_question"])] = row["en_answer"]
    return answers


def normalize(text: str) -> str:
    return " ".join(text.lower().split())


def verdict(answer: str, lp: float | None, ip: float | None) -> Verdict:
    """How ORLM's answer relates to our LP (continuous) and IP (all-integer) optima."""
    theirs_missing = answer.strip().lower() in NO_SOLUTION_MARKERS
    ours_missing = lp is None and ip is None
    if theirs_missing and ours_missing:
        return "both find no optimum"
    if theirs_missing:
        return "only we find an optimum"
    if ours_missing:
        return "only ORLM finds an optimum"
    value = _as_number(answer)
    matches_lp = _close(value, lp)
    matches_ip = _close(value, ip)
    if matches_lp and matches_ip:
        return "matches both"
    if matches_ip:
        return "matches IP only"
    if matches_lp:
        return "matches LP only"
    return "matches neither"


def _as_number(answer: str) -> float | None:
    try:
        return float(answer)
    except ValueError:  # e.g. a message instead of a number
        return None


def _close(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return False
    return math.isclose(a, b, rel_tol=MATCH_TOLERANCE, abs_tol=MATCH_TOLERANCE)
