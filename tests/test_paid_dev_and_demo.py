"""scripts/paid_dev_and_demo.py's selection of the fix-step example, with tests/fakes.FakeClient
in place of Claude (no API calls): a try shows the loop only if its first model fails and the
revision is verified and equal to the hand-checked answer. Also that its plan counts every
attempt. Part 1 (explanations on dev) replays from runs/dev-1, which is local only, so its
plan is checked by running it, not here."""

import importlib.util
import json
from pathlib import Path

import pytest
from fakes import FakeClient

from opt_agent.demo import examples
from opt_agent.self_correct import MAX_ATTEMPTS

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("paid", ROOT / "scripts" / "paid_dev_and_demo.py")
paid = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paid)
BAKERY = examples.FIX_STEP_CANDIDATES[0]


def bakery(flour: dict[str, float], rye_sales: float = 24) -> str:
    """The bakery's model as Claude might reply, with the flour row as given."""

    def row(name, terms, sense, rhs):
        return {"name": name, "terms": [{"var": v, "coef": c} for v, c in terms.items()],
                "sense": sense, "rhs": rhs}  # fmt: skip

    return json.dumps({
        "variables": [{"name": n, "lower": 0, "upper": None, "integer": True}
                      for n in ("sourdough", "rye")],
        "objective": {"sense": "max", "terms": [{"var": "sourdough", "coef": 3},
                                                {"var": "rye", "coef": 2.5}]},
        "constraints": [row("oven minutes", {"sourdough": 20, "rye": 15}, "<=", 480),
                        row("flour", flour, "<=", 30),
                        row("cafe contract", {"rye": 1}, ">=", 10),
                        row("rye sales", {"rye": 1}, "<=", rye_sales)],
    })  # fmt: skip


GRAMS = {"sourdough": 500, "rye": 400}  # grams against 30 kg: infeasible with 10 rye loaves
KILOGRAMS = {"sourdough": 0.5, "rye": 0.4}


@pytest.fixture(autouse=True)
def tries_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(paid, "FIX", tmp_path / "fix-step")


def test_a_failed_first_model_that_the_loop_fixes_shows_it():
    entry = paid.probe(BAKERY, 0, FakeClient(bakery(GRAMS), bakery(KILOGRAMS)))
    assert entry["attempts"] == ["infeasible", "optimal"]
    assert entry["verified"] and entry["matches"] and entry["shows_the_loop"]
    assert entry["objective"] == pytest.approx(BAKERY.reference_objective)


def test_a_right_first_model_shows_nothing():
    entry = paid.probe(BAKERY, 1, FakeClient(bakery(KILOGRAMS)))
    assert entry["attempts"] == ["optimal"] and not entry["shows_the_loop"]


def test_a_fix_that_misses_the_hand_checked_answer_isnt_chosen():
    entry = paid.probe(BAKERY, 2, FakeClient(bakery(GRAMS), bakery(KILOGRAMS, rye_sales=20)))
    assert entry["attempts"] == ["infeasible", "optimal"] and entry["verified"]
    assert not entry["matches"] and not entry["shows_the_loop"]


def test_the_plan_counts_every_attempt_of_every_try():
    calls, worst = paid.plan_fix_step()
    tries = len(examples.FIX_STEP_CANDIDATES) * len(paid.SAMPLES)
    assert calls == tries * MAX_ATTEMPTS + 3  # the chosen one's estimate, checklist, explanation
    assert worst > 0
