"""How one answer is scored, as pre-registered (docs/PREREGISTRATION.md, sections 1 and 3g).

A run records only what each condition answered (evaluate.Item: a status and objective, or
no answer and why). Scoring happens afterwards, here, against the ground truth. Keeping it
out of the run means one scoring path for the run's table and the report, and the same
answers can be scored again (the 1e-4 sensitivity, lenient integrality, a review the owner
corrects) without a single new API call.
"""

from typing import Literal

from pydantic import BaseModel

from opt_agent.ground_truth import TOLERANCE, Reading, Record, matching_reading
from opt_agent.solver import Status


class Score(BaseModel):
    correct: bool
    reading: Reading | None = None  # which accepted answer matched, if one did
    # Wrong with an answer someone could act on: silent. Wrong with no answer: loud.
    failure: Literal["silent", "loud"] | None = None


def score(
    record: Record,
    status: Status | str | None,
    objective: float | None,
    tolerance: float = TOLERANCE,
    lenient: bool = False,
) -> Score:
    """`status` is None when there's no answer: nothing confirmed, or the baseline's reply
    couldn't be parsed. That's wrong, and loud."""
    if status is None:
        return Score(correct=False, failure="loud")
    reading = matching_reading(record, Status(status), objective, tolerance, lenient)
    if reading is None:
        return Score(correct=False, failure="silent")
    return Score(correct=True, reading=reading)
