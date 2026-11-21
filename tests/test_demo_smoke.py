"""scripts/demo_smoke.py, the check CI's demo-image job runs against the Docker image: here
against the app in-process (examples mode), so a change to the examples can't pass the test
suite and fail only in CI. No API calls."""

import importlib.util
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from opt_agent.demo.app import Settings, create_app

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("demo_smoke", ROOT / "scripts" / "demo_smoke.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


@pytest.fixture
def app_in_process(monkeypatch):
    web = TestClient(create_app(Settings(mode="examples")))
    monkeypatch.setattr(smoke, "get", lambda url: web.get(url.removeprefix("http://demo")).json())
    monkeypatch.setattr(smoke, "post", lambda url, body: web.post(
        url.removeprefix("http://demo"), json=body).json())  # fmt: skip


@pytest.mark.usefixtures("app_in_process")
def test_the_smoke_test_passes_on_the_examples_ci_checks(capsys):
    smoke.main(["http://demo", "--example", "paint", "--example", "freight"])
    out = capsys.readouterr().out
    assert "paint: verified" in out and "freight: verified" in out and "flagged, as chosen" in out
    assert out.rstrip().endswith("demo smoke test passed")
