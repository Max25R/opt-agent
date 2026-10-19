"""A stand-in for anthropic.Anthropic, so tests never call the real API.

Every problem here is from NL4Opt's dev split. Test-split problems stay out of anything an
agent's prompt or behavior was tuned on (see data/nl4opt/exclusions.json).
"""

import json
from types import SimpleNamespace

import anthropic
from anthropic.types import Message


class FakeClient:
    """Answers each messages.create() call with the next canned reply and records the request.

    A reply is the text, (text, stop_reason), or an anthropic.APIError to raise.
    """

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests: list[dict] = []
        self.options: list[dict] = []
        self.messages = self  # so that client.messages.create(...) works

    def with_options(self, **options):
        self.options.append(options)
        return self

    def create(self, **request):
        self.requests.append(request)
        if not self.replies:
            raise AssertionError("the code made more API calls than this test expected")
        reply = self.replies.pop(0)
        if isinstance(reply, BaseException):
            raise reply
        text, stop_reason = reply if isinstance(reply, tuple) else (reply, "end_turn")
        return Message.model_validate(
            {
                "id": f"msg_fake_{len(self.requests)}",
                "type": "message",
                "role": "assistant",
                "model": request["model"],
                # Haiku 5.5 thinks first; by default the thinking block's text is omitted.
                "content": [
                    {"type": "thinking", "thinking": "", "signature": "fake"},
                    {"type": "text", "text": text},
                ],
                "stop_reason": stop_reason,
                "stop_sequence": None,
                "usage": {"input_tokens": 1200, "output_tokens": 300},
            }
        )


def status_error(status: int, headers: dict | None = None) -> anthropic.APIStatusError:
    """What the SDK raises for an HTTP error, e.g. 529 (overloaded) or 400 (bad request)."""
    response = SimpleNamespace(status_code=status, headers=headers or {}, request=None)
    return anthropic.APIStatusError(f"HTTP {status}", response=response, body=None)


def connection_error() -> anthropic.APIConnectionError:
    return anthropic.APIConnectionError(request=None)


# NL4Opt dev problem 439170086. The integer optimum is 83 pipelines and 168 trains (251 in
# all); it's unique, and it moves exactly the 1,000,000 units required. The LP optimum is
# 250, so integrality matters here.
GAS_PROBLEM = (
    "A gas company can transport gas using a pipeline or by train. A pipeline can carry 8000 "
    "units of gas and a train can carry 2000 units of gas every day. Due to recent "
    "environmental changes, the number of trains used must be at least twice as many as the "
    "number of pipelines. If at least 1000000 units of gas needs to be transported every day, "
    "minimize the total number of pipelines and trains needed."
)

# What Claude might return for it.
GAS_MODEL = {
    "variables": [
        {"name": "pipelines", "lower": 0, "upper": None, "integer": True},
        {"name": "trains", "lower": 0, "upper": None, "integer": True},
    ],
    "objective": {
        "sense": "min",
        "terms": [{"var": "pipelines", "coef": 1}, {"var": "trains", "coef": 1}],
    },
    "constraints": [
        {
            "name": "daily gas",
            "terms": [{"var": "pipelines", "coef": 8000}, {"var": "trains", "coef": 2000}],
            "sense": ">=",
            "rhs": 1000000,
        },
        {
            "name": "trains at least twice pipelines",
            "terms": [{"var": "trains", "coef": 1}, {"var": "pipelines", "coef": -2}],
            "sense": ">=",
            "rhs": 0,
        },
    ],
}
GAS_REPLY = json.dumps(GAS_MODEL)

GOOD_EXPLANATION = (
    "Use 83 pipelines and 168 trains, 251 in all. Together they carry exactly the 1,000,000 "
    "units of gas needed each day, and that requirement is what sets the total. The rule "
    "that trains be at least twice the pipelines has 2 trains to spare."
)
# "249" is computed (500 trains alone, minus 251), not a solver fact: the checker must flag it.
BAD_EXPLANATION = "Use 83 pipelines and 168 trains: 249 fewer than using trains alone."


def model(constraints, sense="min", objective=None, integer=False):
    """A one-variable model as a reply: x >= 0, minimize (or maximize) x."""
    return json.dumps(
        {
            "variables": [{"name": "x", "integer": integer}],
            "objective": {"sense": sense, "terms": objective or [{"var": "x", "coef": 1}]},
            "constraints": [
                {"name": name, "terms": [{"var": "x", "coef": 1}], "sense": op, "rhs": rhs}
                for name, op, rhs in constraints
            ],
        }
    )


INFEASIBLE_REPLY = model([("at least 5", ">=", 5), ("at most 3", "<=", 3)])
