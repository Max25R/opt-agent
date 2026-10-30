"""What an API call costs, computed from the token counts the API returns.

Prices are USD per million tokens on the Claude API (first party, default global routing),
copied from PRICING_URL on PRICES_CHECKED. A model that isn't listed has no price, so
cost_usd raises rather than guess: a budget or a report built on a made-up price would be
worse than none. Re-check the page before a paid run and update both constants.
"""

from pydantic import BaseModel

from opt_agent.api import TokenUsage, canonical_json

PRICING_URL = "https://platform.claude.com/docs/en/about-claude/pricing"
PRICES_CHECKED = "2026-10-29"


class Prices(BaseModel):
    """USD per million tokens."""

    input: float
    output: float  # thinking tokens are billed as output tokens
    # The 1-hour rate, the higher of the two. We never ask for caching, so this is always
    # 0 tokens today; if that changes, a budget should overcount rather than undercount.
    cache_write: float
    cache_read: float


# Haiku 5.5 is priced by prompt length: a request whose prompt (input, cache reads and
# cache writes together) is over 100,000 tokens pays the second row for every token.
LONG_PROMPT_TOKENS = 100_000
PRICES: dict[str, tuple[Prices, Prices]] = {
    "claude-haiku-5-5": (
        Prices(input=0.10, output=0.50, cache_write=0.20, cache_read=0.01),
        Prices(input=0.50, output=2.50, cache_write=1.00, cache_read=0.05),
    ),
}

# The API adds its own instructions for structured output and thinking, which are billed
# as input but aren't in the request. A safety margin for worst_case_usd, not a measured
# number: the smoke test compares the bound with the input tokens actually billed.
HIDDEN_PROMPT_TOKENS = 2_000


def prices_for(model_id: str, prompt_tokens: int) -> Prices:
    if model_id not in PRICES:
        raise KeyError(f"no price for {model_id!r}: add it to pricing.PRICES from {PRICING_URL}")
    normal, long = PRICES[model_id]
    return long if prompt_tokens > LONG_PROMPT_TOKENS else normal


def cost_usd(usage: TokenUsage, model_id: str) -> float:
    prompt = usage.input_tokens + usage.cache_read_input_tokens + usage.cache_creation_input_tokens
    p = prices_for(model_id, prompt)
    return (
        usage.input_tokens * p.input
        + usage.output_tokens * p.output
        + usage.cache_creation_input_tokens * p.cache_write
        + usage.cache_read_input_tokens * p.cache_read
    ) / 1e6


def worst_case_usd(request: dict) -> float:
    """An upper bound on what sending `request` can cost: every byte of the request counted
    as an input token (a token is never shorter than a byte), plus the hidden prompt, and a
    reply that uses all of max_tokens."""
    size = len(canonical_json(request).encode())
    usage = TokenUsage(
        input_tokens=size + HIDDEN_PROMPT_TOKENS, output_tokens=request["max_tokens"]
    )
    return cost_usd(usage, request["model"])
