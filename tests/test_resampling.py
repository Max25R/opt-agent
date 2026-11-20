"""The resampling study's runner and freeze (docs/RESAMPLING_PREREGISTRATION.md, sections 3 and
6), with tests/fakes.FakeClient in place of Claude: every cell once, in order, resumable, with
errored cells re-run as Amendment 1 says; a run only on the frozen inputs; and the study's
requests are the follow-up's (from the files, where LLM4OR's data is here)."""

import json

import pytest
from fakes import FakeClient, status_error

from opt_agent import api, followup, freeze, resampling, resampling_freeze
from opt_agent.freeze import FreezeError


def model_reply(bound: float) -> str:
    """Claude's model for a toy problem: maximize x with x <= bound."""
    return json.dumps({
        "variables": [{"name": "x", "lower": 0, "upper": None, "integer": False}],
        "objective": {"sense": "max", "terms": [{"var": "x", "coef": 1}]},
        "constraints": [{"name": "cap", "terms": [{"var": "x", "coef": 1}], "sense": "<=",
                         "rhs": bound}],
    })  # fmt: skip


def baseline_reply(value: float) -> str:
    return json.dumps({"status": "optimal", "objective": value})


PROBLEMS = [followup.Problem(id=f"complexlp:{900 + i}", document=f"toy problem {i}", answer=4.0)
            for i in range(2)]  # fmt: skip


def replies_for_one_problem(bounds=(4, 4, 4, 4, 4), base=4.0) -> list[str]:
    """In CELLS order: single-shot samples 3 to 7, then the baseline's sample 3."""
    return [*(model_reply(b) for b in bounds), baseline_reply(base)]


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(api.time, "sleep", lambda s: None)


def test_the_cells_are_five_single_shot_samples_and_one_baseline():
    single = [("single-shot", s) for s in (3, 4, 5, 6, 7)]
    assert resampling.CELLS == (*single, ("baseline", 3))
    assert resampling.UNIT_SAMPLE == 3 and resampling.CAP_USD == 3.00


def test_every_cell_runs_once_in_order_and_a_rerun_calls_nothing(tmp_path):
    client = FakeClient(*replies_for_one_problem(), *replies_for_one_problem((4, 5, 4, 4, 4)))
    items = resampling.run(client, tmp_path, PROBLEMS, "test")
    assert client.replies == []  # exactly the twelve calls
    assert [(i.problem_id, i.condition, i.sample) for i in items] == [
        (p.id, c, s) for p in PROBLEMS for c, s in resampling.CELLS]  # fmt: skip
    assert all(i.outcome == "done" and i.split == resampling.SPLIT for i in items)
    assert [i.objective for i in items if i.problem_id == PROBLEMS[1].id][:2] == [4.0, 5.0]
    # Each sample is its own salted cache entry, so a rerun replays everything for free.
    assert resampling.run(FakeClient(), tmp_path, PROBLEMS, "test") == []
    assert json.loads((tmp_path / "manifest.json").read_text())["cells"] == [
        list(cell) for cell in resampling.CELLS]  # fmt: skip


def test_a_resume_with_other_problems_is_refused(tmp_path):
    resampling.run(FakeClient(*replies_for_one_problem(), *replies_for_one_problem()), tmp_path,
                   PROBLEMS, "test")  # fmt: skip
    with pytest.raises(ValueError, match="another run"):
        resampling.run(FakeClient(), tmp_path, PROBLEMS[:1], "test")


def test_an_errored_cell_is_rerun_until_it_has_failed_four_passes(tmp_path):
    one = PROBLEMS[:1]
    first = [*replies_for_one_problem()[:2], status_error(400), *replies_for_one_problem()[3:]]
    resampling.run(FakeClient(*first), tmp_path, one, "test")
    for _ in range(3):  # three resume passes, each retrying only the errored cell
        resampling.run(FakeClient(status_error(400)), tmp_path, one, "test")
    assert resampling.run(FakeClient(), tmp_path, one, "test") == []  # now final: no call
    entries = resampling.lines(tmp_path)[(one[0].id, "single-shot", 5)]
    assert [e["outcome"] for e in entries] == ["errored"] * 4


def test_settled_cells():
    assert resampling.settled([{"outcome": "done"}])
    assert not resampling.settled([{"outcome": "errored"}] * 3)
    assert resampling.settled([{"outcome": "errored"}] * 4)


def test_the_problems_are_read_only_on_the_frozen_inputs(tmp_path, monkeypatch):
    monkeypatch.setattr(resampling_freeze, "FREEZE_PATH", tmp_path / "missing.json")
    with pytest.raises(FreezeError, match="isn't frozen"):
        resampling.problems()


def test_a_fresh_approval_of_these_inputs_checks_and_any_change_refuses(tmp_path, monkeypatch):
    prints = resampling_freeze.fingerprint()
    named = [
        "docs/RESAMPLING_PREREGISTRATION.md",
        "src/opt_agent/resampling.py",
        "src/opt_agent/resampling_report.py",
        "requirements.lock",
        "model",
        "cells",
        "api.MAX_TOKENS",
        "formulate.SYSTEM_PROMPT",
        "baseline.SYSTEM_PROMPT",
    ]
    assert set(named) <= set(prints)
    approval = resampling_freeze.ResamplingApproval(
        approved_on="2026-11-19", commit=None, fingerprint=prints, approved_by="a test",
        analysis_sha256=prints["src/opt_agent/resampling_report.py"])  # fmt: skip
    path = tmp_path / "FREEZE.json"
    path.write_text(approval.model_dump_json())
    monkeypatch.setattr(resampling_freeze, "FREEZE_PATH", path)
    monkeypatch.setattr(freeze, "drifted_packages", lambda: {})
    monkeypatch.setattr(resampling_freeze, "drifted_packages", lambda: {})
    assert resampling_freeze.check() == freeze.digest(prints)
    changed = approval.model_copy(update={"fingerprint": prints | {"model": "another"}})
    path.write_text(changed.model_dump_json())
    with pytest.raises(FreezeError, match="model"):
        resampling_freeze.check()


def test_the_freeze_file_and_its_tag_go_together():
    """Before the freeze, neither exists; after it, the tag holds exactly the approval."""
    assert resampling_freeze.tag_exists() == resampling_freeze.FREEZE_PATH.exists()
    if resampling_freeze.FREEZE_PATH.exists():
        assert resampling_freeze.tag_problems() == []


@pytest.mark.skipif(not all(p.exists() for p in resampling_freeze.followup_freeze.data_files()),
                    reason="needs LLM4OR's data (python scripts/fetch_llm4or.py)")  # fmt: skip
def test_the_studys_requests_are_the_followups():
    """Section 3: the same model, prompts and max_tokens, by cache key, for all 121 problems."""
    assert resampling_freeze.requests_differ() == []
