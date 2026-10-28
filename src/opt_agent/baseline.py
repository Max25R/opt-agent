"""The no-solver baseline: Claude answers the word problem itself, with no model or solver.

It's scored as pre-registered (docs/PREREGISTRATION.md, section 2a). The reply must be
exactly {"status": ..., "objective": ...}: for "optimal" the objective must be a finite
number, and for the other statuses it's ignored. Anything else (a refusal, a cut-off reply,
a failed validation) is unusable and counts as wrong. One attempt, no revision.

The system prompt gives the same modeling guidance as formulate.SYSTEM_PROMPT, so the one
difference between this condition and single-shot is the solver.
"""

import hashlib
import math
from typing import Literal

import anthropic
from pydantic import BaseModel, ValidationError

from opt_agent import api
from opt_agent.api import CallInfo, TokenUsage
from opt_agent.formulate import DEFAULT_MODEL, describe
from opt_agent.solver import Status


class BaselineAnswer(BaseModel):
    status: Literal["optimal", "infeasible", "unbounded"]
    objective: float | None  # required, but may be null when there's no optimum


ANSWER_SCHEMA = anthropic.transform_schema(BaselineAnswer)

SYSTEM_PROMPT = """\
You are an operations research analyst. Solve the user's word problem yourself, without \
writing or running code. Reply with its status and, if it has an optimal solution, the \
optimal objective value.

- "optimal": some choice meets every requirement, and there is a best one. Give the \
objective value of the best choice.
- "infeasible": no choice meets every requirement.
- "unbounded": the objective can be made better without limit.
- A decision that counts whole things (vehicles, trips, people, products, servings) takes \
whole-number values. Divisible quantities (kilograms, acres, hours, money) can be fractions.
- Decisions are >= 0 unless the problem says otherwise.
- Use every requirement the text states and add none it doesn't state.
- Use the numbers exactly as given."""

# In the logs and results, so answers from different prompt versions can't be mixed.
SYSTEM_PROMPT_SHA256 = hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()[:12]


def build_request(problem: str, model_id: str) -> dict:
    """The whole request, exactly as sent, hashed, cached, and logged. The same pinned
    settings as formulate.build_request; only the system prompt and the schema differ."""
    return {
        "model": model_id,
        "max_tokens": api.MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": problem}],
        "thinking": api.THINKING,
        "output_config": {
            "effort": api.EFFORT,
            "format": {"type": "json_schema", "schema": ANSWER_SCHEMA},
        },
    }


class DirectAnswer(BaseModel):
    request: dict
    status: Status | None  # None if the reply couldn't be used
    objective: float | None  # only for "optimal"
    error: str | None  # why the reply couldn't be used (or the API error)
    raw_text: str
    stop_reason: str | None
    usage: TokenUsage
    call: CallInfo
    model_id: str

    @property
    def api_failed(self) -> bool:
        return self.call.error is not None


def answer_directly(
    problem: str,
    client: anthropic.Anthropic,
    model_id: str = DEFAULT_MODEL,
    cache: api.Cache | None = None,
) -> DirectAnswer:
    request = build_request(problem, model_id)
    response, info = api.call(client, request, cache)
    if response is None:
        return DirectAnswer(request=request, status=None, objective=None,
                            error=f"the API call failed: {info.error}", raw_text="",
                            stop_reason=None, usage=api.usage_of(None), call=info,
                            model_id=model_id)  # fmt: skip
    text = api.reply_text(response)
    status, objective, error = parse_answer(text, response.stop_reason)
    return DirectAnswer(
        request=request,
        status=status,
        objective=objective,
        error=error,
        raw_text=text,
        stop_reason=response.stop_reason,
        usage=api.usage_of(response),
        call=info,
        model_id=model_id,
    )


def parse_answer(
    text: str, stop_reason: str | None
) -> tuple[Status | None, float | None, str | None]:
    """(status, objective, None) for a usable reply, else (None, None, the reason)."""
    if stop_reason in api.UNFINISHED:
        return None, None, api.UNFINISHED[stop_reason]
    try:
        reply = BaselineAnswer.model_validate_json(text)
    except ValidationError as error:
        return None, None, describe(error)
    status = Status(reply.status)
    if status is not Status.OPTIMAL:
        return status, None, None  # the objective is ignored
    if reply.objective is None or not math.isfinite(reply.objective):
        return None, None, f'"optimal" needs a finite objective, not {reply.objective}'
    return status, reply.objective, None
