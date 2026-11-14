"""The follow-up's run protocol (pre-registration, section 6): problems in a pre-registered
hash order, and every sample in every condition of a problem before the next problem, all in
one run directory under one cap. Examples use the gas problem's text. Never calls the API."""

import hashlib
import json

import pytest
from fakes import GAS_CHECKLIST_REPLY, GAS_PROBLEM, GAS_REPLY, FakeClient

from opt_agent import evaluate, followup
from opt_agent.evaluate import done_pairs, worst_case_plan

CONDITIONS = ("single-shot", "checklist-revision")
PROBLEMS = [followup.Problem(id=i, document=GAS_PROBLEM, answer=251) for i in ("19", "20", "30")]


def order_hash(label: str) -> str:
    return hashlib.sha256(f"order:20261109:{label}".encode()).hexdigest()


def test_the_order_is_the_sha256_of_the_label():
    ordered = followup.in_run_order("complexlp-dev", PROBLEMS)
    expected = sorted(PROBLEMS, key=lambda p: order_hash(f"complexlp:{p.id}"))
    assert [p.id for p in ordered] == [p.id for p in expected]
    assert followup.label("industryor-test", "7") == "industryor:7"


def test_the_order_ignores_the_input_order():
    once = followup.in_run_order("complexlp-dev", PROBLEMS)
    again = followup.in_run_order("complexlp-dev", list(reversed(PROBLEMS)))
    assert [p.id for p in once] == [p.id for p in again]


@pytest.mark.skipif(not followup.COMPLEXLP.exists(), reason="needs LLM4OR's data")
def test_the_dev_order_is_a_permutation_of_the_dev_split():
    dev = followup.load("complexlp-dev")
    ordered = followup.in_run_order("complexlp-dev", dev)
    assert sorted(p.id for p in ordered) == sorted(p.id for p in dev) and ordered != dev


def replies(problems: int, samples: int) -> list[str]:
    # per problem and sample: single-shot's formulation, then condition 4's checklist
    return [GAS_REPLY, GAS_CHECKLIST_REPLY] * problems * samples


def run(out, records=PROBLEMS, samples=(0, 1)):
    client = FakeClient(*replies(len(records), len(samples)))
    return evaluate.evaluate(records, CONDITIONS, client, out, "complexlp-dev", sample=samples)


def test_problems_run_in_hash_order_with_every_sample_and_condition_together(tmp_path):
    items = run(tmp_path)
    order = [p.id for p in followup.in_run_order("complexlp-dev", PROBLEMS)]
    expected = [(p, s, c) for p in order for s in (0, 1) for c in CONDITIONS]
    assert [(i.problem_id, i.sample, i.condition) for i in items] == expected
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["problem_ids"] == order and manifest["settings"]["samples"] == "0,1"


def test_every_sample_asks_again_but_shares_its_first_reply_across_conditions(tmp_path):
    items = run(tmp_path, records=PROBLEMS[:1])
    # sample 0 and 1 each pay their formulation and checklist; condition 4 replays the first
    assert [i.cached_calls for i in items] == [0, 1, 0, 1]
    runs = [json.loads(x) for x in (tmp_path / "attempts.jsonl").read_text().splitlines()]
    assert len({x["run_id"] for x in runs}) == 1  # one pass, one log


def test_a_resume_skips_done_samples_only(tmp_path):
    run(tmp_path, records=PROBLEMS[:1], samples=(0, 1))
    done = done_pairs(tmp_path / "results.jsonl", "claude-haiku-5-5")
    assert done == {("19", c, s) for c in CONDITIONS for s in (0, 1)}
    assert run(tmp_path, records=PROBLEMS[:1], samples=(0, 1)) == []  # nothing pending
    with pytest.raises(ValueError, match="settings"):
        run(tmp_path, records=PROBLEMS[:1], samples=(0, 1, 2))  # another experiment


def test_the_plan_counts_every_sample():
    model = "claude-haiku-5-5"
    one, _ = worst_case_plan(PROBLEMS, CONDITIONS, set(), model)
    three, _ = worst_case_plan(PROBLEMS, CONDITIONS, set(), model, samples=(0, 1, 2))
    assert three == 3 * one


def test_nl4opt_splits_keep_file_order(tmp_path):
    from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records

    dev = [r for r in load_records(GROUND_TRUTH_DIR / "dev.json") if r.id == "439170086"]
    client = FakeClient(GAS_REPLY)
    [item] = evaluate.evaluate(dev, ("single-shot",), client, tmp_path)
    assert item.sample == 0
    assert "samples" not in json.loads((tmp_path / "manifest.json").read_text())["settings"]
