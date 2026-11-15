"""scripts/reproduce.py's comparisons and scripts/fetch_llm4or.py's checks, on made-up files.
(The rebuild itself is tests/test_followup_results.py's, and CI's reproduce job runs all of
it.) No API calls."""

import importlib.util
import json
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _script(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


reproduce = _script("reproduce")
fetch = _script("fetch_llm4or")


def write_items(path: Path, items: list[dict]) -> Path:
    path.write_text("".join(json.dumps({"kind": "item"} | i) + "\n" for i in items))
    return path


def item(**fields) -> dict:
    made_up = {"problem_id": "1", "condition": "single-shot", "status": "optimal",
               "objective": 5.0, "latency_s": 1.0, "paid_usd": 0.01, "cached_calls": 0}  # fmt: skip
    return made_up | fields


def test_a_replayed_answer_that_differs_is_named(tmp_path):
    committed = write_items(tmp_path / "a.jsonl", [item()])
    replayed = write_items(tmp_path / "b.jsonl", [item(objective=6.0)])
    found = reproduce.item_differences(committed, replayed, "runs/x")
    assert found == ["runs/x: ('1', 'single-shot', 0) objective: committed 5.0, replayed 6.0"]


def test_time_paid_and_cached_fields_arent_compared(tmp_path):
    committed = write_items(tmp_path / "a.jsonl", [item()])
    replayed = write_items(tmp_path / "b.jsonl",
                           [item(latency_s=0.2, paid_usd=0.0, cached_calls=3)])  # fmt: skip
    assert reproduce.item_differences(committed, replayed, "runs/x") == []


def test_a_missing_pair_and_a_resumed_pair(tmp_path):
    committed = write_items(tmp_path / "a.jsonl", [
        item(status=None, objective=None),  # an errored pass, then the resume's answer:
        item(), item(problem_id="2"),        # the last line of a pair is the one compared
    ])  # fmt: skip
    replayed = write_items(tmp_path / "b.jsonl", [item()])
    found = reproduce.item_differences(committed, replayed, "runs/x")
    assert found == ["runs/x: pair ('2', 'single-shot', 0) is only in the committed run"]


def test_the_fetch_checks_the_hashes_the_studies_recorded():
    amendment5 = _script("amendment5")
    assert fetch.NL4OPT_SHA256 == amendment5.SOURCE["nl4opt_sha256"]
    assert fetch.COMMIT == amendment5.SOURCE["commit"]


@pytest.mark.skipif(not (fetch.TARGET / "NL4Opt").is_dir(), reason="LLM4OR data not here")
def test_the_local_copy_is_intact_and_a_changed_file_is_caught(tmp_path):
    assert fetch.problems(fetch.TARGET) == []
    copy = tmp_path / "llm4or-clean"
    shutil.copytree(fetch.TARGET, copy)
    first = sorted((copy / "NL4Opt").iterdir())[0] / "sample.json"
    first.write_text(first.read_text() + " ")
    (copy / "IndustryOR.jsonl").unlink()
    assert fetch.problems(copy) == ["IndustryOR.jsonl is missing",
                                    "NL4Opt/ isn't the recorded copy"]  # fmt: skip


def test_reproduce_refuses_without_the_data(monkeypatch, tmp_path):
    from opt_agent import followup_freeze

    monkeypatch.setattr(followup_freeze, "data_files", lambda: [tmp_path / "missing.jsonl"])
    with pytest.raises(reproduce.FrozenError, match="fetch_llm4or"):
        reproduce.require_data()
