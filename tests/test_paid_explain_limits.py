"""scripts/paid_explain_limits.py's dry run (ADR-0009): on three dev problems from the
explanation checker's committed run (an LP, the rickshaw IP, one never verified), only the
integer program's explanation is a new call; the formulations and the LP's explanation replay.
No API calls: the plan replays with a client that refuses every request."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "paid_explain_limits.py"
spec = importlib.util.spec_from_file_location("paid_explain_limits", SCRIPT)
paid = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paid)

LP, IP, UNVERIFIED = "2117951416", "-640645082", "-1188104412"  # from runs/explain-dev


@pytest.fixture
def three(monkeypatch):
    chosen = [r for r in paid.dev_problems() if r.id in {LP, IP, UNVERIFIED}]
    assert len(chosen) == 3
    monkeypatch.setattr(paid, "dev_problems", lambda: chosen)


@pytest.mark.usefixtures("three")
def test_only_the_integer_programs_explanation_is_a_new_call():
    counts = paid.plan()
    assert {k: counts[k] for k in ("problems", "verified", "integer_programs", "new_calls")} == {
        "problems": 3, "verified": 2, "integer_programs": 1, "new_calls": 1}  # fmt: skip
    assert 0 < counts["worst"] < 0.02  # one explanation request, all of max_tokens


@pytest.mark.usefixtures("three")
def test_the_plan_prints_the_calls_the_worst_case_and_the_cap(capsys):
    paid.main(["--plan"])
    out = capsys.readouterr().out
    assert "1 new explanation calls" in out and "cap $0.25" in out


def test_the_expected_cost_comes_from_the_first_runs_explanations():
    assert 0 < paid.mean_explanation_usd() < 0.002
