"""The formulation checklist: a separate call that reads the problem text and lists what a
correct formulation must contain, to be compared with Claude's model (audit, finding 2).

**What it sees.** The problem text and the model's variable names, nothing else: no kinds,
bounds, constraints or objective. The names are how the checklist and the model are matched
(the schema asks for names that say what each variable counts or measures), so there's no
fuzzy mapping. A quantity the text needs that isn't among the names can't be written; the
checklist lists it under `cannot_express`, and no flag is raised for it: a missing variable
is a known gap of this check.

**Contamination.** The prompt was written after seeing the M6 test failures. So it's tuned
on dev only (NL4Opt dev, follow-up dev), and any number it gives on M6 test is exploratory:
"prompt designed after seeing these failures".

The diff and its flags are report-only (agent.run with `checklist`): nothing here changes an
answer, a score or a revision.
"""

from typing import Literal

import anthropic
from pydantic import BaseModel, ValidationError

from opt_agent import api
from opt_agent.api import CallInfo, TokenUsage
from opt_agent.formulate import DEFAULT_MODEL, describe
from opt_agent.schema import StrictModel

# ---- what the checklist says ------------------------------------------------------------


class ChecklistTerm(StrictModel):
    var: str
    coef: float


class ChecklistVariable(StrictModel):
    name: str
    kind: Literal["integer", "continuous", "unclear"]
    quote: str


class ChecklistObjective(StrictModel):
    sense: Literal["min", "max"]
    terms: list[ChecklistTerm]
    quote: str


class Requirement(StrictModel):
    quote: str
    terms: list[ChecklistTerm]
    sense: Literal["<=", ">=", "=="]
    rhs: float
    strict: bool  # "more than": also accept the strict reading
    could_be_equal: bool  # "twice as many as": also accept "="
    scope: Literal["single", "combined", "per item"]


class NotARequirement(StrictModel):
    quote: str
    why: str
    # The inequality someone might wrongly make of it; empty terms if there's none.
    terms: list[ChecklistTerm]
    sense: Literal["<=", ">=", "=="]
    rhs: float


class CannotExpress(StrictModel):
    quote: str
    needs: str


class Checklist(StrictModel):
    variables: list[ChecklistVariable]
    objective: ChecklistObjective
    requirements: list[Requirement]
    not_requirements: list[NotARequirement]
    cannot_express: list[CannotExpress]


CHECKLIST_SCHEMA = anthropic.transform_schema(Checklist)

SYSTEM_PROMPT = """\
You are checking an operations research model before it is solved. Read the word problem \
and list what any correct formulation of it must contain. Don't write the model, and don't \
solve the problem.

The model's decision variables are listed by name in <variables>. Use exactly those names \
and no others. If a requirement needs a quantity that isn't one of them, put it in \
cannot_express instead.

- variables: for each listed name, say whether it counts whole things ("integer": vehicles, \
trips, people, products, servings), measures a divisible quantity ("continuous": kilograms, \
acres, hours, money), or the text supports both ("unclear"). Quote the words that decide it.
- objective: its direction (min or max) and its terms over the listed names, with the \
numbers exactly as given. Quote the words it comes from.
- requirements: every requirement the text states, as a linear inequality or equation over \
the listed names. Use the numbers exactly as given, and write percentages as fractions \
(30% as 0.3). Quote the exact words each one comes from.
  - strict: true if the wording is strict ("more than", "must exceed", "fewer than"); still \
write it with >= or <=.
  - could_be_equal: true if the wording names no inequality at all ("twice as many as", \
"three times the number of"), so "=" would be a fair reading too.
  - scope: "combined" if one limit covers several items together, "per item" if it applies \
to each item separately, "single" if it involves one quantity. Decide this from the text: \
"at most 50 cakes of either type" may be one total or one limit per type, so quote why.
  - Leave out non-negativity, unless the text says a quantity can be negative.
- not_requirements: every sentence that states a preference, a motivation, popularity, or \
background rather than a requirement ("prefers", "is more popular", "would like", "sells \
better"), with its quote, why it isn't a requirement, and the inequality someone might \
wrongly make of it (empty terms if there's none). Never turn one of these into a requirement.
- cannot_express: each requirement that needs a quantity not among the listed names, with \
its quote and the quantity it needs.
- Don't add anything the text doesn't state."""


def request_text(problem: str, names: list[str]) -> str:
    listed = "\n".join(names)
    return f"<problem>\n{problem}\n</problem>\n\n<variables>\n{listed}\n</variables>"


def build_request(problem: str, names: list[str], model_id: str = DEFAULT_MODEL) -> dict:
    """The whole request, exactly as sent, hashed, cached and logged. The same pinned
    settings as formulate.build_request."""
    return {
        "model": model_id,
        "max_tokens": api.MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": request_text(problem, names)}],
        "thinking": api.THINKING,
        "output_config": {
            "effort": api.EFFORT,
            "format": {"type": "json_schema", "schema": CHECKLIST_SCHEMA},
        },
    }


class ChecklistReply(BaseModel):
    request: dict
    checklist: Checklist | None  # None if the reply couldn't be used
    error: str | None
    raw_text: str
    stop_reason: str | None
    usage: TokenUsage
    call: CallInfo
    model_id: str

    @property
    def api_failed(self) -> bool:
        return self.call.error is not None


def ask(
    problem: str,
    names: list[str],
    client: anthropic.Anthropic,
    model_id: str = DEFAULT_MODEL,
    cache: api.Cache | None = None,
) -> ChecklistReply:
    request = build_request(problem, names, model_id)
    response, info = api.call(client, request, cache)
    if response is None:
        return ChecklistReply(request=request, checklist=None,
                              error=f"the API call failed: {info.error}", raw_text="",
                              stop_reason=None, usage=api.usage_of(None), call=info,
                              model_id=model_id)  # fmt: skip
    text = api.reply_text(response)
    checklist, error = parse_reply(text, response.stop_reason)
    return ChecklistReply(request=request, checklist=checklist, error=error, raw_text=text,
                          stop_reason=response.stop_reason, usage=api.usage_of(response),
                          call=info, model_id=model_id)  # fmt: skip


def parse_reply(text: str, stop_reason: str | None) -> tuple[Checklist | None, str | None]:
    if stop_reason in api.UNFINISHED:
        return None, api.UNFINISHED[stop_reason]
    try:
        return Checklist.model_validate_json(text), None
    except ValidationError as error:
        return None, describe(error)
