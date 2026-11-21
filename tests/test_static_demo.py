"""scripts/static_demo.py: the demo's static site (GitHub Pages) holds the demo app's own
responses, replayed from the committed replies with no client, and the page switches to
static mode only in the build. No browser here: CI's static-demo job checks the built site
in headless Chromium (`--check`)."""

import importlib.util
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from opt_agent.demo import examples
from opt_agent.demo.app import PAGE, Settings, create_app

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("static_demo", ROOT / "scripts" / "static_demo.py")
static_demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(static_demo)


@pytest.fixture(scope="module")
def site(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("pages") / "site"
    static_demo.build(out)
    return out


def test_the_site_is_the_page_and_the_apps_own_responses(site):
    names = sorted(str(p.relative_to(site)) for p in site.rglob("*") if p.is_file())
    assert names == ["examples.json", "health.json", "index.html"] + [
        f"solve/{e.id}.json" for e in sorted(examples.EXAMPLES, key=lambda e: e.id)
    ]
    web = TestClient(create_app(Settings(mode="examples")))
    assert (site / "health.json").read_bytes() == web.get("/health").content
    assert (site / "examples.json").read_bytes() == web.get("/examples").content
    for e in examples.EXAMPLES:
        answer = web.post("/solve", json={"problem": e.text}).content
        assert (site / "solve" / f"{e.id}.json").read_bytes() == answer


def test_every_example_on_the_site_is_verified_matches_and_paid_nothing(site):
    """Each example matches its hand-checked answer, except the one chosen to show the
    disagreement badge's warning, which is flagged and wrong, as chosen."""
    assert json.loads((site / "health.json").read_text())["examples_cached"] == 5
    for e in examples.EXAMPLES:
        r = json.loads((site / "solve" / f"{e.id}.json").read_text())
        assert r["verification"]["verified"], e.id
        assert r["matches_reference"] is (e.chosen is None), e.id
        assert r["disagreement"]["samples_disagree"] is (e.chosen is not None), e.id
        assert r["calls"] == r["cached_calls"] and r["paid_usd"] == 0, e.id


def test_only_the_build_switches_the_page_to_static(site):
    served = TestClient(create_app(Settings(mode="examples"))).get("/").text
    assert 'data-site="server"' in served and 'data-site="static"' not in served
    built = (site / "index.html").read_text()
    assert 'data-site="static"' in built and 'data-site="server"' not in built
    sha = "0123456789abcdef0123456789abcdef01234567"
    page = PAGE.read_text(encoding="utf-8")
    assert f'data-site="static" data-commit="{sha}"' in static_demo.static_page(page, sha)
    assert "data-commit" not in static_demo.static_page(page, None)  # uncommitted changes
    for broken in (page.replace('data-site="server"', ""), page + 'data-site="server"'):
        with pytest.raises(ValueError, match="exactly once"):
            static_demo.static_page(broken, sha)


def test_the_static_page_fetches_relative_paths():
    """On GitHub Pages the site lives under /opt-agent/, so an absolute path would miss it.
    (That it asks for nothing else, and never posts, is the browser check's.)"""
    script = PAGE.read_text(encoding="utf-8").split("<script>")[1]
    assert "fetch(STATIC ? `${name}.json` : `/${name}`)" in script
    assert "getJSON(`solve/${example.id}`)" in script


def test_a_build_replaces_an_earlier_build_and_nothing_else(tmp_path):
    out = tmp_path / "site"
    static_demo.build(out)
    (out / "stale.json").write_text("{}")
    static_demo.build(out)
    assert not (out / "stale.json").exists()
    other = tmp_path / "notes"
    other.mkdir()
    (other / "keep.txt").write_text("not a site")
    with pytest.raises(SystemExit, match="isn't a built site"):
        static_demo.build(other)
    assert (other / "keep.txt").read_text() == "not a site"
