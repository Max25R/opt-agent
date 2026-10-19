"""Ask Claude to turn a word problem into an LPModel.

Claude answers through structured output: the API guarantees JSON with the shape of our
schema, and our own validator (schema.py) then checks the meaning, e.g. that every term
uses a declared variable. A reply that fails either step becomes a readable `error`, which the
self-correction loop (self_correct.py) sends back to Claude in a `Revision`.
"""

import time

import anthropic
from pydantic import BaseModel, ValidationError

from opt_agent.schema import LPModel

# Small and cheap, for bulk evaluation runs (the owner's requirement). Swap in
# "claude-opus-5-5" for the best quality.
DEFAULT_MODEL = "claude-haiku-5-5"
MAX_TOKENS = 16_000  # leaves room for thinking, which is on by default for current models

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


class TokenUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


class Formulation(BaseModel):
    request: str  # the user message sent
    model: LPModel | None  # None if the reply couldn't be used
    error: str | None  # why not, in words Claude can act on
    raw_text: str  # the reply exactly as received, for the logs
    stop_reason: str | None
    usage: TokenUsage
    latency_s: float
    model_id: str


def formulate(
    problem: str,
    client: anthropic.Anthropic,
    model_id: str = DEFAULT_MODEL,
    revision: Revision | None = None,
) -> Formulation:
    request = request_text(problem, revision)
    start = time.perf_counter()
    response = client.messages.create(
        model=model_id,
        max_tokens=MAX_TOKENS,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": request}],
        output_config={"format": {"type": "json_schema", "schema": LP_SCHEMA}},
    )
    latency = time.perf_counter() - start
    text = "".join(block.text for block in response.content if block.type == "text")
    model, error = parse_reply(text, response.stop_reason)
    return Formulation(
        request=request,
        model=model,
        error=error,
        raw_text=text,
        stop_reason=response.stop_reason,
        usage=usage_of(response),
        latency_s=latency,
        model_id=model_id,
    )


def parse_reply(text: str, stop_reason: str | None) -> tuple[LPModel | None, str | None]:
    """(model, None) for a usable reply, else (None, the reason)."""
    if stop_reason == "refusal":
        return None, "Claude declined to answer"
    if stop_reason == "max_tokens":
        return None, f"the reply was cut off at {MAX_TOKENS} tokens"
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


def usage_of(response) -> TokenUsage:
    u = response.usage
    return TokenUsage(
        input_tokens=u.input_tokens,
        output_tokens=u.output_tokens,
        cache_read_input_tokens=u.cache_read_input_tokens or 0,
        cache_creation_input_tokens=u.cache_creation_input_tokens or 0,
    )
