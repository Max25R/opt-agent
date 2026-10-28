"""The budget guard and the prices it uses. Never calls the API: FakeClient reports 1,200
input and 300 output tokens for every reply."""

import json

import pytest
from fakes import GAS_PROBLEM, GAS_REPLY, FakeClient, api_error_body, status_error
from pytest import approx

from opt_agent import api, pricing
from opt_agent.api import Cache, SpendLimitReached, TokenUsage
from opt_agent.budget import Budget, BudgetedClient, BudgetExceeded
from opt_agent.formulate import DEFAULT_MODEL, build_request, formulate

FAKE_CALL_USD = (1200 * 0.10 + 300 * 0.50) / 1e6  # Haiku 5.5's prices, by hand
REQUEST = build_request(GAS_PROBLEM, DEFAULT_MODEL)


@pytest.fixture
def waits(monkeypatch) -> list[float]:
    slept: list[float] = []
    monkeypatch.setattr(api.time, "sleep", slept.append)
    return slept


def ledger_lines(path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


# ---- prices ------------------------------------------------------------------------------


def test_each_kind_of_token_costs_the_listed_price():
    def usd(**tokens) -> float:
        return pricing.cost_usd(TokenUsage(**tokens), DEFAULT_MODEL)

    k = 100_000  # the most a prompt can have at the normal price
    assert usd(input_tokens=k) == approx(0.10 * k / 1e6)
    assert usd(output_tokens=1_000_000) == approx(0.50)  # output doesn't count as prompt
    assert usd(cache_read_input_tokens=k) == approx(0.01 * k / 1e6)
    assert usd(cache_creation_input_tokens=k) == approx(0.20 * k / 1e6)


def test_a_prompt_over_100k_tokens_pays_the_long_prompt_price_for_every_token():
    short = TokenUsage(input_tokens=100_000, output_tokens=1_000)
    long = TokenUsage(input_tokens=100_001, output_tokens=1_000)
    assert pricing.cost_usd(short, DEFAULT_MODEL) == approx((100_000 * 0.10 + 1_000 * 0.50) / 1e6)
    assert pricing.cost_usd(long, DEFAULT_MODEL) == approx((100_001 * 0.50 + 1_000 * 2.50) / 1e6)
    # Cache reads count toward the prompt's length.
    mixed = TokenUsage(input_tokens=50_000, cache_read_input_tokens=60_000)
    assert pricing.cost_usd(mixed, DEFAULT_MODEL) == approx((50_000 * 0.50 + 60_000 * 0.05) / 1e6)


def test_a_model_without_a_price_is_an_error_not_a_guess():
    with pytest.raises(KeyError, match="no price"):
        pricing.cost_usd(TokenUsage(input_tokens=1), "claude-opus-5-5")


def test_the_worst_case_covers_a_reply_that_uses_every_output_token():
    full_reply = TokenUsage(input_tokens=len(json.dumps(REQUEST)), output_tokens=api.MAX_TOKENS)
    assert pricing.worst_case_usd(REQUEST) > pricing.cost_usd(full_reply, DEFAULT_MODEL)
    assert pricing.worst_case_usd(REQUEST) < 0.01  # about 16,000 output tokens' worth


# ---- the guard ---------------------------------------------------------------------------


def test_each_paid_call_is_recorded_at_its_token_cost(tmp_path):
    ledger = tmp_path / "spend.jsonl"
    budget = Budget(1.00, ledger)
    f = formulate(GAS_PROBLEM, BudgetedClient(FakeClient(GAS_REPLY), budget))
    assert f.error is None
    assert budget.spent_usd == approx(FAKE_CALL_USD) and budget.calls == 1
    [entry] = ledger_lines(ledger)
    assert entry["request_sha256"] == f.call.request_sha256  # ties the spend to the cache
    assert entry["cost_usd"] == approx(FAKE_CALL_USD)
    assert entry["usage"]["output_tokens"] == 300


def test_a_call_that_could_cross_the_cap_is_never_sent():
    fake = FakeClient(GAS_REPLY)
    budget = Budget(pricing.worst_case_usd(REQUEST) * 0.99)
    with pytest.raises(BudgetExceeded, match="could cost up to"):
        formulate(GAS_PROBLEM, BudgetedClient(fake, budget))  # not turned into a failed call
    assert fake.requests == [] and budget.spent_usd == 0


def test_the_ledger_carries_the_spend_into_a_resumed_run(tmp_path):
    ledger = tmp_path / "spend.jsonl"
    worst = pricing.worst_case_usd(REQUEST)
    first = Budget(worst + FAKE_CALL_USD / 2, ledger)  # room for one call, not two
    formulate(GAS_PROBLEM, BudgetedClient(FakeClient(GAS_REPLY), first))
    resumed = Budget(worst + FAKE_CALL_USD / 2, ledger)  # e.g. next month, a new process
    assert resumed.spent_usd == approx(FAKE_CALL_USD) and resumed.calls == 1
    with pytest.raises(BudgetExceeded):
        formulate(GAS_PROBLEM, BudgetedClient(FakeClient(GAS_REPLY), resumed))


def test_a_replayed_reply_costs_nothing(tmp_path):
    budget, cache = Budget(1.00, tmp_path / "spend.jsonl"), Cache(tmp_path / "cache")
    formulate(GAS_PROBLEM, BudgetedClient(FakeClient(GAS_REPLY), budget), cache=cache)
    again = formulate(GAS_PROBLEM, BudgetedClient(FakeClient(), budget), cache=cache)
    assert again.call.cached and budget.calls == 1


def test_failed_tries_are_not_charged(tmp_path, waits):
    budget = Budget(1.00, tmp_path / "spend.jsonl")
    client = BudgetedClient(FakeClient(status_error(529), GAS_REPLY), budget)
    f = formulate(GAS_PROBLEM, client)
    assert f.call.tries == 2 and budget.calls == 1


def test_the_sdk_retries_stay_off_through_the_wrapper():
    fake = FakeClient(GAS_REPLY)
    formulate(GAS_PROBLEM, BudgetedClient(fake, Budget(1.00)))
    assert fake.options == [{"max_retries": 0}]


# ---- the account's own spend limits -------------------------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        status_error(
            429,
            body=api_error_body(
                "You have reached your API usage limits: ...", "enforced_spend_limit_reached"
            ),
        ),  # fmt: skip
        status_error(
            400,
            body=api_error_body(
                "You have reached your specified API usage limits. You will regain access on ..."
            ),
        ),  # fmt: skip
    ],
    ids=["tier cap (429)", "owner's limit (400)"],
)
def test_a_spend_limit_stops_the_run_instead_of_being_retried(error, waits):
    fake = FakeClient(error, GAS_REPLY)
    with pytest.raises(SpendLimitReached):
        api.call(fake, REQUEST)
    assert len(fake.requests) == 1 and waits == []


def test_an_ordinary_rate_limit_is_still_retried(waits):
    rate_limited = status_error(429, {"retry-after": "3"}, api_error_body("rate limited"))
    response, info = api.call(FakeClient(rate_limited, GAS_REPLY), REQUEST)
    assert response is not None and info.tries == 2 and waits == [3.0]
