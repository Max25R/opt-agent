"""The response cache's key (audit, finding 6): it names what Claude was asked (model,
system prompt, messages, sampling settings), not the structured-output schema the SDK
builds, so an SDK upgrade can't miss every cached reply. And every reply cached under the
old key, which hashed the whole request, must still be found. Never calls the API."""

import json
from pathlib import Path

import pytest
from fakes import GAS_PROBLEM, GAS_REPLY, FakeClient

from opt_agent import api, baseline, formulate
from opt_agent.api import Cache, cache_key, request_sha256

ROOT = Path(__file__).resolve().parents[1]
MODEL = "claude-haiku-5-5"


class NoCalls:
    """A client that fails the test if anything reaches the API."""

    def with_options(self, **options):
        raise AssertionError("a request missed the cache")


def upgraded_sdk(schema: dict) -> dict:
    """The same schema as another SDK version might write it: an extra keyword."""
    return {**schema, "$comment": "written by a newer anthropic.transform_schema"}


def test_an_sdk_change_to_the_schema_doesnt_change_the_key(monkeypatch):
    before = formulate.build_request(GAS_PROBLEM, MODEL)
    monkeypatch.setattr(formulate, "LP_SCHEMA", upgraded_sdk(formulate.LP_SCHEMA))
    after = formulate.build_request(GAS_PROBLEM, MODEL)
    assert request_sha256(before) != request_sha256(after)  # the request did change
    assert cache_key(before) == cache_key(after)


@pytest.mark.parametrize(
    "edit",
    [
        lambda r: r | {"model": "claude-sonnet-5-5"},
        lambda r: r | {"system": r["system"] + " Be brief."},
        lambda r: r | {"messages": [{"role": "user", "content": "Another problem."}]},
        lambda r: r | {"max_tokens": 8_000},
        lambda r: r | {"thinking": {"type": "disabled"}},
        lambda r: r | {"output_config": {**r["output_config"], "effort": "high"}},
        lambda r: r | {"temperature": 0.5},
    ],
    ids=["model", "system", "messages", "max_tokens", "thinking", "effort", "temperature"],
)
def test_anything_that_changes_what_claude_is_asked_changes_the_key(edit):
    request = formulate.build_request(GAS_PROBLEM, MODEL)
    assert cache_key(edit(request)) != cache_key(request)


def test_the_baseline_and_formulation_requests_never_share_a_key():
    """They differ only in system prompt and schema; the system prompt keeps them apart."""
    assert cache_key(baseline.build_request(GAS_PROBLEM, MODEL)) != cache_key(
        formulate.build_request(GAS_PROBLEM, MODEL)
    )


def test_a_reply_cached_before_an_sdk_upgrade_replays_after_it(tmp_path, monkeypatch):
    cache = Cache(tmp_path)
    request = formulate.build_request(GAS_PROBLEM, MODEL)
    api.call(FakeClient(GAS_REPLY), request, cache)
    monkeypatch.setattr(formulate, "LP_SCHEMA", upgraded_sdk(formulate.LP_SCHEMA))
    response, info = api.call(NoCalls(), formulate.build_request(GAS_PROBLEM, MODEL), cache)
    assert info.cached and api.reply_text(response) == GAS_REPLY


def test_a_reply_stored_under_the_old_key_is_found(tmp_path):
    """M6's caches name each file by the SHA-256 of the whole request."""
    request = formulate.build_request(GAS_PROBLEM, MODEL)
    api.call(FakeClient(GAS_REPLY), request, Cache(tmp_path / "new"))
    (stored,) = (tmp_path / "new").glob("*.json")
    old = tmp_path / "old"
    old.mkdir()
    (old / f"{request_sha256(request)}.json").write_text(stored.read_text())
    response, info = api.call(NoCalls(), request, Cache(old))
    assert info.cached and api.reply_text(response) == GAS_REPLY


M6_RUNS = [ROOT / "runs" / "test", ROOT / "runs" / "test-perturbed"]


@pytest.mark.skipif(not all(r.exists() for r in M6_RUNS), reason="needs the committed runs")
@pytest.mark.parametrize("run", M6_RUNS, ids=lambda r: r.name)
def test_every_reply_the_m6_runs_logged_is_found_under_the_new_key(run):
    cache = Cache(run / "cache")
    logged = [json.loads(line) for line in (run / "attempts.jsonl").read_text().splitlines()]
    requests = [e["request"] for e in logged if e["kind"] in ("baseline", "attempt")]
    assert requests and all(cache.get(cache_key(r)) is not None for r in requests)
    stored = [json.loads(p.read_text())["request"] for p in (run / "cache").glob("*.json")]
    assert len({cache_key(r) for r in stored}) == len(stored)  # no two share a key
