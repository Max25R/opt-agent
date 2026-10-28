"""A dollar cap on live API calls, kept from the token counts the API returns.

Wrap the client once, and every call made through it is guarded, with no change anywhere
else in the pipeline:

    client = BudgetedClient(anthropic.Anthropic(api_key=...), Budget(1.00, ledger_path))

- **Before** each call, the budget reserves the call's worst case (pricing.worst_case_usd:
  every byte of the request as an input token, and all of max_tokens as output). If that
  could take the spend past the cap, it raises BudgetExceeded instead of calling. So the
  cap is never crossed, however long Claude's reply turns out to be.
- **After** each call, the actual cost (pricing.cost_usd of response.usage) goes into the
  ledger, a JSONL file. The ledger outlives the process: a run resumed next month counts
  what it already spent against the same cap.

Replies replayed from the response cache never reach the client (api.call answers them),
so they cost nothing and aren't recorded. A call that raises an API error is assumed to
cost nothing too, since the API doesn't bill error responses; the account's own spend
limit (api.SpendLimitReached) is the backstop if that assumption ever fails.
"""

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import anthropic
from anthropic.types import Message

from opt_agent.api import RunStopped, request_sha256, usage_of
from opt_agent.pricing import cost_usd, worst_case_usd


class BudgetExceeded(RunStopped):
    """The next call could take the spend past the cap."""


@dataclass
class Budget:
    cap_usd: float
    ledger: Path | None = None  # None: count in memory only
    spent_usd: float = field(init=False, default=0.0)
    calls: int = field(init=False, default=0)  # paid calls, including earlier runs'

    def __post_init__(self):
        if self.ledger is not None and self.ledger.exists():
            entries = [json.loads(line) for line in self.ledger.read_text().splitlines()]
            self.spent_usd = sum(e["cost_usd"] for e in entries)
            self.calls = len(entries)

    @property
    def remaining_usd(self) -> float:
        return self.cap_usd - self.spent_usd

    def reserve(self, request: dict) -> None:
        worst = worst_case_usd(request)
        if self.spent_usd + worst > self.cap_usd:
            raise BudgetExceeded(
                f"the next call could cost up to ${worst:.4f}, and only "
                f"${self.remaining_usd:.4f} of the ${self.cap_usd:.2f} cap is left "
                f"(${self.spent_usd:.4f} spent on {self.calls} calls)"
            )

    def record(self, request: dict, response: Message) -> float:
        usage = usage_of(response)
        cost = cost_usd(usage, request["model"])
        self.spent_usd += cost
        self.calls += 1
        if self.ledger is not None:
            entry = {
                "time": datetime.now(UTC).isoformat(timespec="seconds"),
                "request_sha256": request_sha256(request),  # the cache key
                "model": request["model"],
                "usage": usage.model_dump(),
                "cost_usd": cost,
            }
            self.ledger.parent.mkdir(parents=True, exist_ok=True)
            with self.ledger.open("a") as f:
                f.write(json.dumps(entry) + "\n")
        return cost


class BudgetedClient:
    """Stands in for anthropic.Anthropic wherever the pipeline takes a `client`."""

    def __init__(self, client: anthropic.Anthropic, budget: Budget):
        self._client = client
        self.budget = budget
        self.messages = self  # so that client.messages.create(...) works

    def with_options(self, **options) -> "BudgetedClient":
        return BudgetedClient(self._client.with_options(**options), self.budget)

    def create(self, **request) -> Message:
        self.budget.reserve(request)
        response = self._client.messages.create(**request)
        self.budget.record(request, response)
        return response
