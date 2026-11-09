"""The follow-up study's problems: LLM4OR's cleaned ComplexLP and IndustryOR
(docs/EXTERNAL_DATA.md, git-ignored), split once into dev and follow-up test
(docs/FOLLOWUP_SPLIT.md, data/followup/split.json).

The follow-up test split is sealed until its pre-registration is frozen: nothing here
returns a test problem's text or answer, and asking for one raises Sealed. The dev split is
for building and tuning; its answers are compared at 1e-4 relative, the tolerance used for
published external keys (their values can be rounded).
"""

import json
import math
from pathlib import Path

from pydantic import BaseModel

from opt_agent.runs import REPO_ROOT
from opt_agent.solver import Status

SPLIT_PATH = REPO_ROOT / "data" / "followup" / "split.json"
DATA = REPO_ROOT / "data" / "external" / "llm4or-clean"
COMPLEXLP = DATA / "Mamo_complex_lp_clean.jsonl"
DEV_SPLITS = {"complexlp-dev"}
SEALED = {"complexlp-test", "industryor-test"}
TOLERANCE = 1e-4


class Sealed(Exception):
    """The follow-up test split can't be read before its pre-registration is frozen."""


class Problem(BaseModel):
    id: str
    document: str
    answer: float | None  # the benchmark's objective; None if it gives no optimum


def read_split(path: Path = SPLIT_PATH) -> dict:
    return json.loads(path.read_text())


def load(split: str) -> list[Problem]:
    """The dev split's problems, in id order. A follow-up test split raises Sealed. Every
    line of the source file is parsed for its id, and only dev lines are kept."""
    if split in SEALED:
        raise Sealed(f"{split} is sealed until the follow-up pre-registration is frozen")
    if split not in DEV_SPLITS:
        raise ValueError(f"no follow-up split {split!r}; dev splits: {sorted(DEV_SPLITS)}")
    dev = set(read_split()["complexlp"]["dev"])
    problems = []
    for line in COMPLEXLP.read_text().splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["id"] in dev:
            problems.append(Problem(id=str(row["id"]), document=row["Question"],
                                    answer=_answer(row["Answer"])))  # fmt: skip
    if len(problems) != len(dev):
        raise ValueError(f"{COMPLEXLP} has {len(problems)} of the {len(dev)} dev problems")
    return sorted(problems, key=lambda p: int(p.id))


def is_correct(problem: Problem, status: str | None, objective: float | None) -> bool:
    """Status and objective against the benchmark's answer, at 1e-4 relative."""
    if status is None:
        return False
    if problem.answer is None:
        return status != Status.OPTIMAL
    return status == Status.OPTIMAL and math.isclose(
        objective, problem.answer, rel_tol=TOLERANCE, abs_tol=TOLERANCE
    )


def _answer(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
