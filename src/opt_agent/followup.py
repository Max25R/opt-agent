"""The follow-up study's problems: LLM4OR's cleaned ComplexLP and IndustryOR
(docs/EXTERNAL_DATA.md, git-ignored), split once into dev and follow-up test
(docs/FOLLOWUP_SPLIT.md, data/followup/split.json).

The follow-up test split is sealed until its pre-registration is frozen: load() raises Sealed
for it, and load_sealed() reads it only once followup_freeze.check() passes (the owner's
approval exists and the inputs still match it). Neither prints or logs a problem, and a
Problem's repr leaves out its text and answer, so an error message can't show them. The dev
split is for building and tuning; its answers are compared at 1e-4 relative, the tolerance
used for published external keys (their values can be rounded).

The test run reads both sealed splits as one, TEST_SPLIT ("followup-test"), whose problem ids
are their labels ("complexlp:1", "industryor:1"), since the two benchmarks' ids overlap.
Results, resumes, the manifest, the run order and the report all use those labels.

**Keys** (pre-registration, section 4) are parsed by parse_key, by their format alone:
explicit infeasible or unbounded wording gives that status; a number, after removing
thousands separators, whitespace, a currency sign and trailing units, gives an optimum; anything
else makes the problem unscorable, and it is left out of every condition before the run.
An unparseable key is never read as "no optimum".
"""

import hashlib
import json
import math
import re
from pathlib import Path

from pydantic import BaseModel, Field, ValidationError, model_validator

from opt_agent.runs import REPO_ROOT
from opt_agent.solver import Status

SPLIT_PATH = REPO_ROOT / "data" / "followup" / "split.json"
DATA = REPO_ROOT / "data" / "external" / "llm4or-clean"
COMPLEXLP = DATA / "Mamo_complex_lp_clean.jsonl"
INDUSTRYOR = DATA / "IndustryOR.jsonl"
DEV_SPLITS = {"complexlp-dev"}
SEALED = {"complexlp-test", "industryor-test"}
TEST_SPLIT = "followup-test"  # both sealed splits as one run, ids as labels
TOLERANCE = 1e-4


class Sealed(Exception):
    """The follow-up test split can't be read before its pre-registration is frozen."""


class Problem(BaseModel):
    id: str
    # repr=False: a sealed problem's text and key never reach a log or a traceback
    document: str = Field(repr=False)
    answer: float | None = Field(repr=False)  # the key's objective, for an optimal key
    # the key's status; None: the key couldn't be parsed, so the problem isn't scorable
    key_status: Status | None = Field(default=Status.OPTIMAL, repr=False)
    # decimal places the key is written with, for a key that isn't a whole number (the
    # rounding clause, section 4); None for whole-number keys and statuses
    key_decimals: int | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def _consistent(self) -> "Problem":
        if (self.key_status == Status.OPTIMAL) != (self.answer is not None):
            raise ValueError("an optimal key has a value, and only an optimal key")
        return self

    @property
    def scorable(self) -> bool:
        return self.key_status is not None

    @classmethod
    def from_key(cls, id: str, document: str, raw: object) -> "Problem":
        status, value = parse_key(raw)
        return cls(id=id, document=document, answer=value, key_status=status,
                   key_decimals=written_decimals(raw))  # fmt: skip


# ---- keys -------------------------------------------------------------------------------

_INFEASIBLE = re.compile(r"\binfeasible\b|\bno feasible solution", re.IGNORECASE)
_UNBOUNDED = re.compile(r"\bunbounded\b", re.IGNORECASE)
_KEY_NUMBER = re.compile(
    r"(?P<sign>[+-])?\s*[$€£¥]?\s*"  # an optional sign, then an optional currency sign
    r"(?P<number>(?:\d{1,3}(?:[,\s]\d{3})+|\d+)(?:\.\d*)?|\.\d+)"  # thousands separators
    r"(?P<exponent>[eE][+-]?\d+)?"
    r"\s*(?:[A-Za-z%][A-Za-z%/.\s]*)?"  # trailing units: "dollars", "kg", "%", "units/day"
)


def parse_key(raw: object) -> tuple[Status | None, float | None]:
    """A benchmark key as (status, value), by its format alone (section 4):
    - text with no digit and explicit infeasible or unbounded wording (not both): that
      status, no value;
    - a JSON number, or text that is one number once thousands separators, whitespace, a
      leading currency sign and trailing units are removed: optimal, that value;
    - anything else, including a non-finite number: (None, None), so the problem is left
      out. Never "no optimum": a key we can't read says nothing about the problem."""
    if isinstance(raw, bool):
        return None, None
    if isinstance(raw, int | float):
        return (Status.OPTIMAL, float(raw)) if math.isfinite(raw) else (None, None)
    if not isinstance(raw, str):
        return None, None
    text = raw.strip()
    if not any(c.isdigit() for c in text):
        infeasible, unbounded = _INFEASIBLE.search(text), _UNBOUNDED.search(text)
        if infeasible and not unbounded:
            return Status.INFEASIBLE, None
        if unbounded and not infeasible:
            return Status.UNBOUNDED, None
        return None, None
    found = _KEY_NUMBER.fullmatch(text)
    if found is None:
        return None, None
    digits = re.sub(r"[,\s]", "", found["number"])
    value = float(f"{found['sign'] or ''}{digits}{found['exponent'] or ''}")
    return (Status.OPTIMAL, value) if math.isfinite(value) else (None, None)


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
            problems.append(Problem.from_key(str(row["id"]), row["Question"], row["Answer"]))
    if len(problems) != len(dev):
        raise ValueError(f"{COMPLEXLP} has {len(problems)} of the {len(dev)} dev problems")
    return sorted(problems, key=lambda p: int(p.id))


def load_sealed(split: str) -> list[Problem]:
    """A follow-up test split's problems, in id order, only on the frozen inputs:
    followup_freeze.check() first (FreezeError if nothing is approved or anything differs,
    the data files' hashes included), then every id must be exactly split.json's. A
    IndustryOR problem's id is its line number (1-based). Prints and logs nothing."""
    from opt_agent import followup_freeze  # here: it imports this module

    if split not in SEALED:
        raise ValueError(f"no sealed split {split!r}; sealed splits: {sorted(SEALED)}")
    followup_freeze.check()
    benchmark = split.split("-")[0]
    expected = {str(i) for i in read_split()[benchmark]["test"]}
    if benchmark == "complexlp":
        rows = [json.loads(line) for line in COMPLEXLP.read_text().splitlines() if line.strip()]
        found = [(str(r["id"]), r["Question"], r["Answer"]) for r in rows]
    else:
        lines = INDUSTRYOR.read_text().splitlines()
        found = [(str(n), (r := json.loads(line))["en_question"], r["en_answer"])
                 for n, line in enumerate(lines, start=1) if line.strip()]  # fmt: skip
    problems = []
    for pid, document, answer in found:
        if pid in expected:
            try:
                problems.append(Problem.from_key(pid, document, answer))
            except ValidationError:  # its message would quote the input: name the id only
                raise ValueError(f"{split}: problem {pid} isn't a valid problem") from None
    if sorted(p.id for p in problems) != sorted(expected):
        raise ValueError(f"{split}: the data file's ids aren't split.json's")  # ids only
    return sorted(problems, key=lambda p: int(p.id))


def load_test() -> list[Problem]:
    """TEST_SPLIT: both sealed splits (each through load_sealed, so only on the frozen
    inputs), with each problem's label as its id, ComplexLP first, each in id order.
    Unscorable keys included: the caller leaves them out and the report lists them."""
    return [p.model_copy(update={"id": label(split, p.id)})
            for split in ("complexlp-test", "industryor-test")
            for p in load_sealed(split)]  # fmt: skip


ORDER_SEED = 20261109  # follow-up pre-registration, section 6


def label(split: str, problem_id: str) -> str:
    """A problem's name across benchmarks, as the pre-registration writes it:
    "complexlp:19", "industryor:7". In TEST_SPLIT the id already is one."""
    if ":" in problem_id:
        return problem_id
    return f"{split.split('-')[0]}:{problem_id}"


def in_run_order(split: str, problems: list, seed: int = ORDER_SEED) -> list:
    """The problems sorted by the SHA-256 of "order:<seed>:<label>": a fixed shuffle that
    anyone can recompute from the ids alone, so a run stopped by its cap stops on a random,
    pre-registered set of problems rather than the lowest ids."""

    def key(p) -> str:
        return hashlib.sha256(f"order:{seed}:{label(split, p.id)}".encode()).hexdigest()

    return sorted(problems, key=key)


def written_decimals(raw: object) -> int | None:
    """The decimal places a key is written with, if it's an optimum that isn't a whole
    number ("4.53" -> 2); None otherwise. A whole-number key ("14", "14.0") gets None, so it
    stays at 1e-4 and a missed integrality constraint still fails."""
    status, value = parse_key(raw)
    if status != Status.OPTIMAL or value == round(value) or isinstance(raw, bool):
        return None
    found = _KEY_NUMBER.fullmatch(str(raw).strip())
    if found is None or found["exponent"] or "." not in found["number"]:
        return None
    return len(found["number"].split(".")[1])


def is_correct(problem: Problem, status: str | None, objective: float | None) -> bool:
    """Status and objective against the benchmark's key (section 4). An optimum is right
    within 1e-4 relative, or, for a key written with decimals that isn't a whole number, if
    it rounds to the key at those decimals (a rounded key mustn't fail an exact answer). An
    infeasible or unbounded key needs that status. An unscorable problem has no right
    answer to compare with, so asking is an error: it should have been left out."""
    return right_by(problem, status, objective) is not None


def right_by(problem: Problem, status: str | None, objective: float | None) -> str | None:
    """Why an answer is right: "tolerance" (within 1e-4, or the status a status key names),
    "rounding" (only by the rounding clause), or None if it's wrong."""
    if not problem.scorable:
        raise ValueError(f"problem {problem.id} has an unparseable key: it isn't scored")
    if status is None:
        return None
    if problem.key_status != Status.OPTIMAL:
        return "tolerance" if status == problem.key_status else None
    if status != Status.OPTIMAL:
        return None
    if math.isclose(objective, problem.answer, rel_tol=TOLERANCE, abs_tol=TOLERANCE):
        return "tolerance"
    if problem.key_decimals is not None and rounds_to(objective, problem.answer,
                                                      problem.key_decimals):  # fmt: skip
        return "rounding"
    return None


def rounds_to(objective: float, key: float, decimals: int) -> bool:
    """`objective` rounded to `decimals` places gives `key`: within half a unit of the last
    written place (a tie counts, as either rounding direction would give it). The 1e-12
    slack absorbs binary floating point, nothing more."""
    half = 0.5 * 10.0**-decimals
    return abs(objective - key) <= half * (1 + 1e-12)
