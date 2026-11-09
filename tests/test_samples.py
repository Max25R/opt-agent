"""Repeated samples (k per pair): the cache's key carries a sample index, so samples 1, 2, ...
are new calls, while sample 0 is exactly the key every existing cache uses. Never calls the
API."""

import json
from pathlib import Path

import pytest
from fakes import GAS_PROBLEM, GAS_REPLY, FakeClient

from opt_agent import api, evaluate, formulate
from opt_agent.api import Cache, cache_key

ROOT = Path(__file__).resolve().parents[1]
REQUEST = formulate.build_request(GAS_PROBLEM, "claude-haiku-5-5")
OTHER = GAS_REPLY.replace('"rhs": 0', '"rhs": 1')  # another reply, to tell samples apart


def test_sample_0_is_the_existing_key():
    assert cache_key(REQUEST, sample=0) == cache_key(REQUEST)


def test_every_later_sample_has_a_key_of_its_own():
    keys = [cache_key(REQUEST, sample=n) for n in range(4)]
    assert len(set(keys)) == 4


DEV_CACHE = ROOT / "runs" / "dev-checklist" / "cache"


@pytest.mark.skipif(not DEV_CACHE.exists(), reason="needs the committed dev run")
def test_every_file_the_dev_run_wrote_is_named_by_the_sample_0_key():
    """Written after the M7 cache key, so its names pin that key: sample 0 must not move."""
    files = sorted(DEV_CACHE.glob("*.json"))
    assert files and all(
        f.stem == cache_key(json.loads(f.read_text())["request"], sample=0) for f in files
    )


def test_a_later_sample_is_a_new_call_and_doesnt_overwrite_sample_0(tmp_path):
    first, _ = api.call(FakeClient(GAS_REPLY), REQUEST, Cache(tmp_path))
    second, info = api.call(FakeClient(OTHER), REQUEST, Cache(tmp_path, sample=1))
    assert not info.cached and api.reply_text(second) == OTHER  # a new call
    again, replayed = api.call(FakeClient(), REQUEST, Cache(tmp_path))  # sample 0 again
    assert replayed.cached and api.reply_text(again) == GAS_REPLY
    again1, replayed1 = api.call(FakeClient(), REQUEST, Cache(tmp_path, sample=1))
    assert replayed1.cached and api.reply_text(again1) == OTHER


def test_the_old_file_index_keeps_samples_apart(tmp_path):
    """A file found by the index (named by another key) is served only to its own sample."""
    api.call(FakeClient(OTHER), REQUEST, Cache(tmp_path, sample=1))
    (stored,) = tmp_path.glob("*.json")
    stored.rename(tmp_path / "renamed.json")  # as if under some older key
    response, info = api.call(FakeClient(GAS_REPLY), REQUEST, Cache(tmp_path))
    assert not info.cached and api.reply_text(response) == GAS_REPLY  # sample 0 isn't sample 1
    replayed, again = api.call(FakeClient(), REQUEST, Cache(tmp_path, sample=1))
    assert again.cached and api.reply_text(replayed) == OTHER


def test_a_run_directory_is_one_sample_and_the_manifest_says_which(tmp_path, monkeypatch):
    monkeypatch.setattr(api.time, "sleep", lambda s: None)
    from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records

    gas = next(r for r in load_records(GROUND_TRUTH_DIR / "dev.json") if r.id == "439170086")
    evaluate.evaluate([gas], ("single-shot",), FakeClient(GAS_REPLY), tmp_path / "s0")
    evaluate.evaluate([gas], ("single-shot",), FakeClient(OTHER), tmp_path / "s2", sample=2)
    settings = [json.loads((tmp_path / d / "manifest.json").read_text())["settings"]
                for d in ("s0", "s2")]  # fmt: skip
    assert "sample" not in settings[0] and settings[1]["sample"] == "2"
    [item] = evaluate.latest_items(tmp_path / "s2" / "results.jsonl")
    assert item.sample == 2
