"""Self-correction: when an attempt fails, tell Claude what went wrong and let it revise.

An attempt fails if its reply can't be used as a model, or if the model is infeasible or
unbounded. Every model is solved by both CBC and HiGHS, and feedback is only sent when they
agree. Each revision gets specific feedback (feedback.py). The loop stops at:

- an optimal model;
- a solver time-out or error, or CBC and HiGHS disagreeing: not Claude's fault, so no
  revision is asked for;
- the attempt limit;
- the same model again: Claude stands by it, which is the right answer for a problem
  that's infeasible as written;
- a refusal.

Every attempt is appended to a JSONL log, one line each, with the full request and reply.
"""

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel

from opt_agent.changes import Changes, compare
from opt_agent.feedback import for_invalid_reply, for_status
from opt_agent.formulate import DEFAULT_MODEL, SYSTEM_PROMPT, Formulation, Revision, formulate
from opt_agent.highs import solve_with_highs
from opt_agent.schema import LPModel
from opt_agent.solver import Solution, Status, solve
from opt_agent.verify import same_answer

MAX_ATTEMPTS = 3
# Identifies the prompt version in the logs, so runs with different prompts can't be mixed.
SYSTEM_PROMPT_SHA256 = hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()[:12]

StopReason = Literal[
    "optimal", "attempt limit", "model unchanged", "refused", "solver error", "solvers disagree"
]


class Attempt(BaseModel):
    number: int
    formulation: Formulation
    solution: Solution | None = None  # CBC's; None if the reply couldn't be used
    highs_solution: Solution | None = None  # the independent second opinion
    changes: Changes | None = None  # compared with the previous attempt's model
    feedback: str | None = None  # sent for the next attempt; None if the loop stopped here


class Outcome(BaseModel):
    run_id: str
    attempts: list[Attempt]
    stopped: StopReason

    @property
    def final(self) -> Attempt:
        """The answer: the last attempt that produced a model, else simply the last one."""
        with_model = [a for a in self.attempts if a.formulation.model is not None]
        return (with_model or self.attempts)[-1]

    @property
    def flags(self) -> list[str]:
        """Revisions that deleted or loosened something, across all attempts."""
        return [flag for a in self.attempts if a.changes for flag in a.changes.flags]


def solve_with_revisions(
    problem: str,
    client: anthropic.Anthropic,
    model_id: str = DEFAULT_MODEL,
    max_attempts: int = MAX_ATTEMPTS,
    log_path: Path | None = None,
) -> Outcome:
    """max_attempts=1 is the single-shot baseline: no revisions."""
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    run_id = uuid.uuid4().hex
    attempts: list[Attempt] = []
    revision, last_model = None, None
    for number in range(1, max_attempts + 1):
        formulation = formulate(problem, client, model_id, revision)
        attempt, stopped = _judge(number, formulation, last_model)
        if stopped is None and number == max_attempts:
            stopped = "attempt limit"
        if stopped is None:
            feedback = _feedback(attempt)
            attempt = attempt.model_copy(update={"feedback": feedback})
            revision = Revision(previous_reply=formulation.raw_text, feedback=feedback)
        attempts.append(attempt)
        _log(log_path, run_id, attempt, stopped)
        if stopped is not None:
            return Outcome(run_id=run_id, attempts=attempts, stopped=stopped)
        last_model = formulation.model or last_model
    raise AssertionError("unreachable: the last attempt always stops the loop")


def _judge(
    number: int, formulation: Formulation, last_model: LPModel | None
) -> tuple[Attempt, StopReason | None]:
    """Solve the attempt's model with both solvers; say why to stop, or None to revise."""
    attempt = Attempt(number=number, formulation=formulation)
    if formulation.stop_reason == "refusal":
        return attempt, "refused"
    model = formulation.model
    if model is None:
        return attempt, None  # the reply couldn't be used: revise
    changes = compare(last_model, model) if last_model is not None else None
    cbc, highs = solve(model), solve_with_highs(model)
    attempt = attempt.model_copy(
        update={"solution": cbc, "highs_solution": highs, "changes": changes}
    )
    if cbc.failed or highs.failed:
        return attempt, "solver error"  # a time-out or an error: no verdict to act on
    if not same_answer(model, cbc, highs):
        return attempt, "solvers disagree"  # feedback would rest on one solver's word
    if cbc.status is Status.OPTIMAL:
        return attempt, "optimal"
    if changes is not None and changes.none:
        return attempt, "model unchanged"
    return attempt, None  # infeasible or unbounded, and both solvers agree: revise


def _feedback(attempt: Attempt) -> str:
    f = attempt.formulation
    if f.model is None:
        return for_invalid_reply(f.error)
    return for_status(f.model, attempt.solution.status)


def _log(path: Path | None, run_id: str, attempt: Attempt, stopped: StopReason | None) -> None:
    if path is None:
        return
    f, s, h = attempt.formulation, attempt.solution, attempt.highs_solution
    record = {
        "run_id": run_id,
        "attempt": attempt.number,
        "time": datetime.now(UTC).isoformat(timespec="seconds"),
        "model_id": f.model_id,
        "system_prompt_sha256": SYSTEM_PROMPT_SHA256,
        "request": f.request,
        "reply": f.raw_text,
        "stop_reason": f.stop_reason,
        "usage": f.usage.model_dump(),
        "latency_s": round(f.latency_s, 3),
        "error": f.error,
        "status": s.status.value if s else None,
        "objective": s.objective if s else None,
        "highs_status": h.status.value if h else None,
        "highs_objective": h.objective if h else None,
        "changes": attempt.changes.changes if attempt.changes else None,
        "flags": attempt.changes.flags if attempt.changes else None,
        "feedback": attempt.feedback,
        "stopped": stopped,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as log:
        log.write(json.dumps(record) + "\n")
