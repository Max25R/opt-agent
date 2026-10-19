"""Ask Claude to turn a word problem into an LPModel.

Claude answers through structured output: the API guarantees JSON with the shape of our
schema, and our own validator (schema.py) then checks the meaning, e.g. that every term
uses a declared variable. A reply that fails either step becomes a readable `error`, which the
self-correction loop (self_correct.py) sends back to Claude in a `Revision`. A failed API
call is an error too (`api_failed`), but not one Claude can fix.
"""

import anthropic
from pydantic import BaseModel, ValidationError

from opt_agent import api
from opt_agent.api import CallInfo, TokenUsage
from opt_agent.schema import LPModel

# Small and cheap, for bulk evaluation runs (the owner's requirement). Swap in
# "claude-opus-5-5" for the best quality.
DEFAULT_MODEL = "claude-haiku-5-5"

# The schema exactly as the SDK's own parse() helper would send it.
LP_SCHEMA = anthropic.transform_schema(LPModel)

SYSTEM_PROMPT = """\
You are an operations research analyst. Turn the user's word problem into a linear or \
mixed-integer program.

- Declare one variable per decision, named after what it counts or measures.
- Make a variable integer if it counts whole things (vehicles, trips, people, products, \
servings). Keep it continuous for divisible quantities (kilograms, acres, hours, money).
- Variables are >= 0 unless the problem says otherwise.
- Write every requirement the text states as a constraint, and add none it doesn't state.
- Use the numbers exactly as given; write percentages as fractions (30% -> 0.3).
- Every variable must appear with a nonzero coefficient somewhere."""


class Revision(BaseModel):
    """What a revision request carries: Claude's previous reply and what went wrong."""

    previous_reply: str
    feedback: str


def request_text(problem: str, revision: Revision | None = None) -> str:
    """The user message. A revision is self-contained (problem, previous reply, feedback),
    so every attempt can be logged, cached, and replayed on its own."""
    if revision is None:
        return problem
    return (
        f"<problem>\n{problem}\n</problem>\n\n"
        f"<previous_model>\n{revision.previous_reply}\n</previous_model>\n\n"
        f"<feedback>\n{revision.feedback}\n</feedback>\n\n"
        "Return a corrected model. If you're sure the previous model already says what the "
        "problem says, return it unchanged."
    )


def build_request(problem: str, model_id: str, revision: Revision | None = None) -> dict:
    """The whole request, exactly as sent, hashed, cached, and logged."""
    return {
        "model": model_id,
        "max_tokens": api.MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": request_text(problem, revision)}],
        "thinking": api.THINKING,
        "output_config": {
            "effort": api.EFFORT,
            "format": {"type": "json_schema", "schema": LP_SCHEMA},
        },
    }


class Formulation(BaseModel):
    request: dict  # the full request sent (build_request)
    model: LPModel | None  # None if the reply couldn't be used
    error: str | None  # why not, in words Claude can act on (or the API error)
    raw_text: str  # the reply exactly as received, for the logs
    stop_reason: str | None
    usage: TokenUsage
    call: CallInfo  # the cache key, tries, latency, and retry time
    model_id: str

    @property
    def api_failed(self) -> bool:
        """The call itself failed, after every retry: nothing Claude could revise."""
        return self.call.error is not None


def formulate(
    problem: str,
    client: anthropic.Anthropic,
    model_id: str = DEFAULT_MODEL,
    revision: Revision | None = None,
    cache: api.Cache | None = None,
) -> Formulation:
    request = build_request(problem, model_id, revision)
    response, info = api.call(client, request, cache)
    if response is None:
        error = f"the API call failed: {info.error}"
        return Formulation(request=request, model=None, error=error, raw_text="",
                           stop_reason=None, usage=api.usage_of(None), call=info,
                           model_id=model_id)  # fmt: skip
    text = api.reply_text(response)
    model, error = parse_reply(text, response.stop_reason)
    return Formulation(
        request=request,
        model=model,
        error=error,
        raw_text=text,
        stop_reason=response.stop_reason,
        usage=api.usage_of(response),
        call=info,
        model_id=model_id,
    )


def parse_reply(text: str, stop_reason: str | None) -> tuple[LPModel | None, str | None]:
    """(model, None) for a usable reply, else (None, the reason)."""
    if stop_reason in api.UNFINISHED:
        return None, api.UNFINISHED[stop_reason]
    try:
        return LPModel.model_validate_json(text), None
    except ValidationError as error:
        return None, describe(error)


def describe(error: ValidationError) -> str:
    """Pydantic's errors as one line each, e.g. "variables.0.lower: Input should be a number"."""
    lines = []
    for e in error.errors():
        where = ".".join(str(part) for part in e["loc"])
        message = e["msg"].removeprefix("Value error, ")
        lines.append(f"{where}: {message}" if where else message)
    return "\n".join(lines)
