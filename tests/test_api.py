import json

import pytest
from fakes import GAS_PROBLEM, GAS_REPLY, INFEASIBLE_REPLY, FakeClient, connection_error, model
from fakes import status_error as error

from opt_agent import api
from opt_agent.api import Cache, call, request_sha256
from opt_agent.formulate import DEFAULT_MODEL, build_request
from opt_agent.runs import Run
from opt_agent.self_correct import solve_with_revisions

REQUEST = build_request(GAS_PROBLEM, DEFAULT_MODEL)


@pytest.fixture
def waits(monkeypatch) -> list[float]:
    """Record the waits between tries instead of sleeping through them."""
    slept: list[float] = []
    monkeypatch.setattr(api.time, "sleep", slept.append)
    return slept


@pytest.mark.parametrize(
    "failure",
    [connection_error(), error(408), error(409), error(429), error(500), error(529)],
    ids=["connection", "408", "409", "429", "500", "529"],
)
def test_what_the_sdk_retries_is_retried(failure, waits):
    response, info = call(FakeClient(failure, GAS_REPLY), REQUEST)
    assert response is not None and info.error is None
    assert info.tries == 2 and waits == [0.5]


@pytest.mark.parametrize("status", [400, 401, 403, 404, 413, 422])
def test_a_request_that_cant_succeed_is_not_retried(status, waits):
    response, info = call(FakeClient(error(status)), REQUEST)
    assert response is None and info.tries == 1 and waits == []
    assert info.error.startswith(f"APIStatusError ({status})")


def test_the_server_can_say_whether_to_retry(waits):
    assert (
        call(FakeClient(error(400, {"x-should-retry": "true"}), GAS_REPLY), REQUEST)[1].tries == 2
    )
    assert call(FakeClient(error(529, {"x-should-retry": "false"})), REQUEST)[1].tries == 1


def test_backoff_doubles_unless_the_server_names_a_wait(waits):
    client = FakeClient(error(529), error(529), error(429, {"retry-after": "12"}), GAS_REPLY)
    response, info = call(client, REQUEST)
    assert waits == [0.5, 1.0, 12.0]
    assert info.tries == 4
    assert info.retry_s >= sum(waits)  # the waits plus the failed tries themselves
    assert info.latency_s < 1  # only the try that worked


def test_after_the_last_try_the_error_is_returned_not_raised(waits):
    client = FakeClient(*[error(529)] * api.MAX_TRIES)
    response, info = call(client, REQUEST)
    assert response is None and info.tries == api.MAX_TRIES == len(client.requests)
    assert info.error == "APIStatusError (529): HTTP 529"


def test_the_sdk_does_not_retry_on_its_own():
    client = FakeClient(GAS_REPLY)
    call(client, REQUEST)
    assert client.options == [{"max_retries": 0}]


def test_a_cached_response_is_replayed_without_a_call(tmp_path):
    cache = Cache(tmp_path)
    first, info = call(FakeClient(GAS_REPLY), REQUEST, cache)
    again, replayed = call(FakeClient(), REQUEST, cache)  # would fail on any API call
    assert again == first
    assert replayed.cached and not info.cached
    assert replayed.latency_s == info.latency_s  # the original call's time, not the replay's
    stored = json.loads((tmp_path / f"{request_sha256(REQUEST)}.json").read_text())
    assert stored["request"] == REQUEST  # the cache can be read without this code


def test_a_failed_call_is_not_cached(tmp_path, waits):
    cache = Cache(tmp_path)
    call(FakeClient(error(400)), REQUEST, cache)
    assert list(tmp_path.iterdir()) == []
    response, info = call(FakeClient(GAS_REPLY), REQUEST, cache)  # a re-run tries again
    assert response is not None and not info.cached


def test_a_crashed_run_resumes_from_the_cache(tmp_path, waits):
    """The first run gets attempt 1 and then fails. Re-run with the same cache, it pays only
    for the call that failed: attempt 1's request is identical, so it's replayed."""
    cache = Cache(tmp_path / "cache")
    fixed = model([("at least 5", ">=", 5)])
    crashed = solve_with_revisions(
        "p", FakeClient(INFEASIBLE_REPLY, error(400)), session=Run(cache=cache)
    )
    assert crashed.stopped == "api error"

    client = FakeClient(fixed)  # only one reply: attempt 1 must come from the cache
    resumed = solve_with_revisions("p", client, session=Run(cache=cache))
    assert resumed.stopped == "optimal"
    assert [a.formulation.call.cached for a in resumed.attempts] == [True, False]
    assert len(client.requests) == 1


def test_a_finished_run_replays_without_any_call(tmp_path):
    cache = Cache(tmp_path)
    fixed = model([("at least 5", ">=", 5)])
    first = solve_with_revisions("p", FakeClient(INFEASIBLE_REPLY, fixed), session=Run(cache=cache))
    replay = solve_with_revisions("p", FakeClient(), session=Run(cache=cache))
    assert [a.formulation.raw_text for a in replay.attempts] == [
        a.formulation.raw_text for a in first.attempts
    ]
    assert replay.stopped == first.stopped == "optimal"
