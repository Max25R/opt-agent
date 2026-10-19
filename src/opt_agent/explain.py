"""Explain an optimal solution in plain English, using only the solver's own numbers.

Claude writes the explanation, but only from a fixed set of solver facts: the values, the
objective, which constraints bind, the slack in the rest, and shadow prices. Afterwards
every number in the text is checked against those facts and the inputs: one that isn't a
correct rounding of any of them (an invented saving, a difference Claude computed) is
flagged, not hidden. So is an explanation that was refused, cut off, empty, or never
arrived (`problem`).

This checks where each number comes from, not whether the sentence using it is true:
"10 trips move 1,000 fish" passes whenever 10 and 1,000 are both facts or inputs.
"""

import json
import re

import anthropic
from pydantic import BaseModel

from opt_agent import api
from opt_agent.api import CallInfo, TokenUsage
from opt_agent.formulate import DEFAULT_MODEL
from opt_agent.schema import LPModel
from opt_agent.solver import Solution, Status
from opt_agent.verify import tolerance_for

SYSTEM_PROMPT = """\
Explain the result of an optimization model to someone who isn't an expert, in 3 to 5 \
sentences: what to do, what it achieves, and what limits it.

Use only the facts you're given: the decision values, the objective value, which \
constraints are binding (fully used), the slack in the others, and shadow prices if \
given (how much the objective changes per extra unit of a constraint's limit). Don't \
compute new numbers. Every number you write must appear in the facts, the model, or the \
problem, at most rounded."""


class Facts(BaseModel):
    """Everything the explanation may say, straight from the solver."""

    objective: float
    values: dict[str, float]
    binding: list[str]  # constraints the optimum pushes against
    slack: dict[str, float]  # unused room in each constraint
    shadow_prices: dict[str, float] | None  # change in objective per unit of rhs; LPs only


class Explanation(BaseModel):
    text: str  # as received, even if incomplete
    unsupported_numbers: list[str]  # numbers in the text that no fact or input backs up
    problem: str | None = None  # why it's missing or incomplete; None if it's whole
    request: dict  # the full request sent (build_request)
    stop_reason: str | None
    usage: TokenUsage
    call: CallInfo


def solver_facts(model: LPModel, solution: Solution) -> Facts:
    if solution.status is not Status.OPTIMAL:
        raise ValueError(f"only an optimal solution can be explained, not {solution.status}")
    binding = [
        c.name
        for c in model.constraints
        if abs(solution.slacks[c.name]) <= tolerance_for(c.terms, solution.values)
    ]
    return Facts(
        objective=_clean(solution.objective),
        values={k: _clean(v) for k, v in solution.values.items()},
        binding=binding,
        slack={k: _clean(v) for k, v in solution.slacks.items()},
        shadow_prices=solution.duals and {k: _clean(v) for k, v in solution.duals.items()},
    )


def _clean(x: float) -> float:
    """Drop the solver's round-off (CBC reports ~8 digits) and turn -0.0 into 0.0."""
    return round(x, 6) + 0.0


def build_request(problem: str, model: LPModel, facts: Facts, model_id: str) -> dict:
    """The whole request, exactly as sent, hashed, cached, and logged."""
    payload = json.dumps(
        {"model": model.model_dump(mode="json"), "facts": facts.model_dump(mode="json")}, indent=1
    )
    return {
        "model": model_id,
        "max_tokens": api.MAX_TOKENS,
        "system": SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": f"Problem:\n{problem}\n\nModel and facts:\n{payload}"}
        ],
        "thinking": api.THINKING,
        "output_config": {"effort": api.EFFORT},
    }


def explain(
    problem: str,
    model: LPModel,
    facts: Facts,
    client: anthropic.Anthropic,
    model_id: str = DEFAULT_MODEL,
    cache: api.Cache | None = None,
) -> Explanation:
    request = build_request(problem, model, facts, model_id)
    response, info = api.call(client, request, cache)
    text = api.reply_text(response).strip() if response else ""
    stop_reason = response.stop_reason if response else None
    return Explanation(
        text=text,
        unsupported_numbers=unsupported_numbers(text, allowed_numbers(problem, model, facts)),
        problem=_what_went_wrong(text, stop_reason, info),
        request=request,
        stop_reason=stop_reason,
        usage=api.usage_of(response),
        call=info,
    )


def _what_went_wrong(text: str, stop_reason: str | None, info: CallInfo) -> str | None:
    if info.error is not None:
        return f"the API call failed: {info.error}"
    if stop_reason in api.UNFINISHED:
        return api.UNFINISHED[stop_reason]
    return None if text else "the reply had no text"


# ---- checking the numbers --------------------------------------------------------------

# "36", "1,160", "$2,333.33", "30%", "-0.5". Not digits inside names like "c0_budget".
_NUMBER = re.compile(r"(?<![\w.])-?\$?\d[\d,]*(?:\.\d+)?%?")


def allowed_numbers(problem: str, model: LPModel, facts: Facts) -> list[float]:
    """Every number the explanation may use: from the facts, the model, and the problem."""
    numbers = [facts.objective, *facts.values.values(), *facts.slack.values()]
    numbers += list((facts.shadow_prices or {}).values())
    for expression in [model.objective.terms, *(c.terms for c in model.constraints)]:
        numbers += [t.coef for t in expression]
    numbers += [c.rhs for c in model.constraints]
    numbers += [b for v in model.variables for b in (v.lower, v.upper) if b is not None]
    numbers += [value for token in _NUMBER.findall(problem) for value, _ in _readings(token)]
    return [abs(n) for n in numbers]


def unsupported_numbers(text: str, allowed: list[float]) -> list[str]:
    """Numbers in `text` that aren't a correct rounding of any allowed number."""
    return [
        token
        for token in _NUMBER.findall(text)
        if not any(
            _rounds_to(exact, value, places)
            for value, places in _readings(token)
            for exact in allowed
        )
    ]


def _readings(token: str) -> list[tuple[float, int]]:
    """(value, decimal places shown) for each way to read a token: "30%" is 30 or 0.30."""
    digits = token.strip("$%").replace(",", "").replace("$", "")
    value = abs(float(digits))
    places = len(digits.split(".")[1]) if "." in digits else 0
    if token.endswith("%"):
        return [(value, places), (value / 100, places + 2)]
    return [(value, places)]


def _rounds_to(exact: float, written: float, places: int) -> bool:
    """Is `written`, shown with `places` decimals, a correct rounding of `exact`?"""
    return abs(exact - written) <= 0.5 * 10.0**-places + 1e-9
