"""A stand-in for anthropic.Anthropic, so tests never call the real API."""

import json
from types import SimpleNamespace


class FakeClient:
    """Answers each messages.create() call with the next canned reply and records the request.

    A reply is the text, or (text, stop_reason).
    """

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests: list[dict] = []
        self.messages = self  # so that client.messages.create(...) works

    def create(self, **request):
        self.requests.append(request)
        reply = self.replies.pop(0)
        text, stop_reason = reply if isinstance(reply, tuple) else (reply, "end_turn")
        return SimpleNamespace(
            # Current models think first; by default the thinking block's text is empty.
            content=[
                SimpleNamespace(type="thinking", thinking=""),
                SimpleNamespace(type="text", text=text),
            ],
            stop_reason=stop_reason,
            usage=SimpleNamespace(
                input_tokens=1200,
                output_tokens=300,
                cache_read_input_tokens=None,
                cache_creation_input_tokens=None,
            ),
        )


# What Claude might return for the fishery problem (tests/problems.py). Optimum: 10 truck
# trips and no sled dog trips, 3000 fish; the budget binds.
FISHERY_MODEL = {
    "variables": [
        {"name": "sled dog trips", "lower": 0, "upper": None, "integer": True},
        {"name": "truck trips", "lower": 0, "upper": None, "integer": True},
    ],
    "objective": {
        "sense": "max",
        "terms": [{"var": "sled dog trips", "coef": 100}, {"var": "truck trips", "coef": 300}],
    },
    "constraints": [
        {
            "name": "budget",
            "terms": [{"var": "sled dog trips", "coef": 50}, {"var": "truck trips", "coef": 100}],
            "sense": "<=",
            "rhs": 1000,
        },
        {
            "name": "fewer sled dog trips",
            "terms": [{"var": "sled dog trips", "coef": 1}, {"var": "truck trips", "coef": -1}],
            "sense": "<=",
            "rhs": 0,
        },
    ],
}
FISHERY_REPLY = json.dumps(FISHERY_MODEL)

GOOD_EXPLANATION = (
    "Send 10 truck trips and no sled dog trips to move 3,000 fish. The $1,000 budget is "
    "fully used, and that is what limits the catch. The rule that sled dog trips stay below "
    "truck trips has 10 trips of room to spare."
)
# "$200" is computed, not a solver fact: the checker must flag it.
BAD_EXPLANATION = "Send 10 truck trips to move 3,000 fish, saving $200 over sled dogs."
