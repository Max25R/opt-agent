"""What a solver returns: in its own module so every solver and checker can share it."""

from enum import StrEnum

from pydantic import BaseModel


class Status(StrEnum):
    OPTIMAL = "optimal"
    INFEASIBLE = "infeasible"
    UNBOUNDED = "unbounded"
    TIMEOUT = "timeout"  # the solver hit its time limit before it could prove anything
    ERROR = "error"  # the solver stopped without a definite answer for another reason


class Solution(BaseModel):
    solver: str
    status: Status
    objective: float | None = None
    values: dict[str, float] = {}
    slacks: dict[str, float] = {}
    # Shadow prices: d(objective)/d(rhs) for each constraint. Pure LPs only; a MIP has none.
    duals: dict[str, float] | None = None
    note: str | None = None  # e.g. why the solver's own claim was overruled, or why it failed

    @property
    def failed(self) -> bool:
        """No verdict at all: not a wrong answer, so it says nothing about the model."""
        return self.status in (Status.TIMEOUT, Status.ERROR)
