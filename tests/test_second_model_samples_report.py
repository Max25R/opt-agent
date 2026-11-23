"""The second-model samples study's analysis (docs/second_model/SAMPLES_PREREGISTRATION.md,
section 4), on fake answers: three single-shot samples per model (Sonnet's sample 0 from its
own record, 1 and 2 from the run; Haiku's 0 to 2 from its record); anything but a right done
answer is wrong; S2 is the follow-up's contrast, the sign-flip test on per-problem scores, with
its four verdicts; majority of three with exact McNemar; silent failures added up over the
samples; and a report json can write. Then scripts/reproduce.py's step for this study, on a
fake run of samples 1 and 2 on all 121 problems, where LLM4OR's data and the committed freeze
are."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from fakes import FakeClient

from opt_agent import followup, followup_freeze, freeze, second_model_samples, stats
from opt_agent import second_model_samples_report as report
from opt_agent.evaluate import Item
from opt_agent.followup_report import bootstrap_ci, bound_pp

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("reproduce", ROOT / "scripts" / "reproduce.py")
reproduce = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reproduce)


def item(problem: str, objective: float | None = 4.0, *, sample: int = 1,
         outcome: str = "done", status: str | None = "optimal", condition: str = "single-shot",
         model: str = "claude-sonnet-5-5", cost: float = 0.02, latency: float = 5.0,
         reason: str | None = None) -> Item:  # fmt: skip
    return Item(problem_id=problem, split="second-model-samples", condition=condition,
                outcome=outcome, sample=sample, model_id=model, settings_sha256="s",
                status=None if objective is None and status == "optimal" else status,
                objective=objective, cost_usd=cost, latency_s=latency, reason=reason)  # fmt: skip


def haiku(problem: str, objective: float | None = 4.0, sample: int = 0, **more) -> Item:
    return item(problem, objective, sample=sample, model="claude-haiku-5-5", **more)


def problem(pid: str, key: float = 4.0) -> followup.Problem:
    return followup.Problem(id=pid, document="toy", answer=key)


def write(path: Path, items: list[Item], lines: list[dict] = ()) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = [*(i.model_dump(mode="json") for i in items), *lines]
    path.write_text("".join(json.dumps(x) + "\n" for x in entries))


def build(tmp_path: Path, problems, sonnet: list[Item], haikus: list[Item]) -> dict:
    """Sonnet's sample-0 items go to its own record, the rest to the run; Haiku's to its."""
    write(tmp_path / "sonnet-0.jsonl", [i for i in sonnet if i.sample == 0])
    write(tmp_path / "run" / "results.jsonl", [i for i in sonnet if i.sample != 0])
    write(tmp_path / "haiku.jsonl", haikus)
    return report.build(tmp_path / "run", problems, tmp_path / "sonnet-0.jsonl",
                        tmp_path / "haiku.jsonl")  # fmt: skip


def scored(sonnet_right: list[int], haiku_right: list[int]) -> tuple[list, list, list]:
    """Problems with the given number of samples right (of 3) for each model: a sample is
    right (4.0 against a key of 4.0) or wrong (5.0)."""
    problems = [problem(f"p{i}") for i in range(len(sonnet_right))]
    sonnet = [item(p.id, 4.0 if s < k else 5.0, sample=s)
              for p, k in zip(problems, sonnet_right, strict=True) for s in (0, 1, 2)]  # fmt: skip
    haikus = [haiku(p.id, 4.0 if s < k else 5.0, sample=s)
              for p, k in zip(problems, haiku_right, strict=True) for s in (0, 1, 2)]  # fmt: skip
    return problems, sonnet, haikus


# ---- the answers --------------------------------------------------------------------------


def test_each_models_score_counts_its_three_single_shot_samples(tmp_path):
    problems = [problem("p0")]
    sonnet = [item("p0", 4.0, sample=0), item("p0", 4.0, sample=1), item("p0", 5.0, sample=2)]
    haikus = [
        haiku("p0", 4.0, sample=0),
        haiku("p0", 5.0, sample=1),
        haiku("p0", 5.0, sample=2),
        haiku("p0", 4.0, sample=1, condition="baseline"),
    ]  # another condition: not used
    data = build(tmp_path, problems, sonnet, haikus)
    assert data["scores"] == [{"problem": "p0", "sonnet_right": 2, "haiku_right": 1}]
    assert data["right_by_sample"] == {"sonnet": [1, 1, 0], "haiku": [1, 0, 0]}
    assert (data["s2"]["sonnet_right"], data["s2"]["haiku_right"]) == (2, 1)


def test_sonnets_sample_0_comes_from_its_own_record_never_the_run(tmp_path):
    """A sample-0 line in this study's run (there shouldn't be one) isn't read."""
    problems = [problem("p0")]
    write(tmp_path / "sonnet-0.jsonl", [item("p0", 5.0, sample=0)])
    write(tmp_path / "run" / "results.jsonl",
          [item("p0", 4.0, sample=0), item("p0", sample=1), item("p0", sample=2)])  # fmt: skip
    write(tmp_path / "haiku.jsonl", [haiku("p0", sample=s) for s in (0, 1, 2)])
    data = report.build(tmp_path / "run", problems, tmp_path / "sonnet-0.jsonl",
                        tmp_path / "haiku.jsonl")  # fmt: skip
    assert data["right_by_sample"]["sonnet"] == [0, 1, 1]


def test_anything_but_a_right_done_answer_is_wrong(tmp_path):
    problems = [problem(f"p{i}") for i in range(4)]
    sonnet = [*(item(p.id, sample=0) for p in problems),
              item("p0", None, sample=1, status=None, reason="unusable"),  # no answer
              item("p1", sample=1, outcome="errored", status=None, objective=None),
              item("p2", 4.0, sample=1, status="infeasible"),  # a confirmed wrong verdict
              # p3's sample 1 is missing
              *(item(p.id, sample=2) for p in problems)]  # fmt: skip
    haikus = [haiku(p.id, sample=s) for p in problems for s in (0, 1, 2)]
    data = build(tmp_path, problems, sonnet, haikus)
    assert data["right_by_sample"]["sonnet"] == [4, 0, 4]
    assert data["complete"] is False and data["s2"]["verdict"] == "incomplete"


# ---- S2: the follow-up's contrast ---------------------------------------------------------


def test_s2_is_the_follow_ups_sign_flip_test_on_per_problem_scores(tmp_path):
    sonnet_right, haiku_right = [3, 3, 2, 0, 1, 3, 2], [2, 3, 3, 1, 1, 0, 2]
    problems, sonnet, haikus = scored(sonnet_right, haiku_right)
    s2 = build(tmp_path, problems, sonnet, haikus)["s2"]
    diffs = np.array(sonnet_right) - np.array(haiku_right)
    assert s2["p_value"] == pytest.approx(stats.sign_flip_exact(list(diffs)))
    assert s2["difference"] == pytest.approx(diffs.mean() / 3)
    assert s2["difference_ci95"] == pytest.approx(bootstrap_ci(diffs / 3))
    assert s2["within_pp"] == bound_pp(bootstrap_ci(diffs / 3))
    assert (s2["problems_sonnet_higher"], s2["problems_haiku_higher"], s2["problems_tied"]) == (
        2, 2, 3)  # fmt: skip
    assert (s2["sonnet_right"], s2["haiku_right"], s2["answers_each"]) == (14, 12, 21)
    assert s2["sonnet_mean_score"] == pytest.approx(14 / 21)
    assert s2["haiku_mean_score_ci95"] == pytest.approx(bootstrap_ci(np.array(haiku_right) / 3))


@pytest.mark.parametrize(
    ("sonnet_right", "haiku_right", "expected"),
    [
        ([3] * 8, [0] * 8, "supported"),  # every problem better for Sonnet: p = 2 / 2^8
        ([0] * 8, [3] * 8, "not supported"),
        ([3, 0, 3, 0], [0, 3, 0, 3], "inconclusive"),
        ([2] * 5, [2] * 5, "inconclusive"),  # no difference at all: p = 1
    ],
)
def test_the_verdicts(tmp_path, sonnet_right, haiku_right, expected):
    problems, sonnet, haikus = scored(sonnet_right, haiku_right)
    s2 = build(tmp_path, problems, sonnet, haikus)["s2"]
    assert s2["verdict"] == expected and s2["alpha"] == 0.05
    assert (s2["p_value"] < 0.05) == (expected in ("supported", "not supported"))


def test_the_verdict_rule_by_itself():
    assert report.verdict(0.1, 0.01, complete=True) == "supported"
    assert report.verdict(-0.1, 0.01, complete=True) == "not supported"
    assert report.verdict(0.3, 0.05, complete=True) == "inconclusive"  # p equal to alpha
    assert report.verdict(0.3, 0.001, complete=False) == "incomplete"
    assert set(report.VERDICTS) == {"supported", "not supported", "inconclusive", "incomplete"}


def test_an_unsettled_call_leaves_the_run_incomplete_but_reports_the_effect(tmp_path):
    problems, sonnet, haikus = scored([3] * 8, [0] * 8)
    sonnet = [i for i in sonnet if (i.problem_id, i.sample) != ("p7", 2)]
    data = build(tmp_path, problems, sonnet, haikus)
    assert (data["complete"], data["settled"], data["calls"]) == (False, 15, 16)
    assert data["s2"]["verdict"] == "incomplete" and data["s2"]["p_value"] < 0.05


def test_an_errored_call_settles_after_four_passes_and_counts_as_wrong(tmp_path):
    problems, sonnet, haikus = scored([3], [3])
    sonnet = [i for i in sonnet if i.sample != 2]
    errored = item("p0", None, sample=2, outcome="errored", status=None, reason="overloaded")
    data = build(tmp_path, problems, [*sonnet, *[errored] * 4], haikus)
    assert data["complete"] is True and data["errored"] == 1
    assert data["scores"][0]["sonnet_right"] == 2


# ---- secondary ----------------------------------------------------------------------------


def test_majority_of_three_and_its_exact_mcnemar(tmp_path):
    sonnet_right, haiku_right = [2, 3, 1, 0, 2, 3], [1, 3, 2, 2, 0, 1]
    problems, sonnet, haikus = scored(sonnet_right, haiku_right)
    m = build(tmp_path, problems, sonnet, haikus)["majority"]
    # majority: Sonnet right on p0, p1, p4, p5; Haiku on p1, p2, p3
    assert (m["sonnet_right"], m["haiku_right"]) == (4, 3)
    assert (m["only_sonnet_right"], m["only_haiku_right"]) == (3, 2)
    assert m["p_value"] == pytest.approx(stats.mcnemar_exact(3, 2))
    assert m["difference"] == pytest.approx(1 / 6)
    assert m["sonnet_accuracy"]["wilson95"] == pytest.approx(list(stats.wilson(4, 6)))


def test_silent_failures_add_up_over_the_three_samples(tmp_path):
    problems = [problem("p0"), problem("p1")]
    sonnet = [item("p0", 5.0, sample=0), item("p1", sample=0),  # one silent failure
              item("p0", 5.0, sample=1), item("p1", None, sample=1, status=None,
                                                 reason="the reply was cut off at its "
                                                        "max_tokens limit"),
              item("p0", sample=2), item("p1", 4.0, sample=2, status="unbounded")]  # fmt: skip
    haikus = [haiku(p.id, sample=s) for p in problems for s in (0, 1, 2)]
    f = build(tmp_path, problems, sonnet, haikus)["failures"]
    s = f["sonnet"]
    assert (s["answers"], s["verified"], s["silent"]["k"]) == (6, 4, 2)
    assert s["silent_by_sample"] == [1, 1, 0]
    assert s["silent_of_verified"]["n"] == 4 and s["silent"]["n"] == 6
    assert (s["wrong_verdicts"], s["loud"], s["cut_off"], s["errored_or_missing"]) == (1, 1, 1, 0)
    assert f["haiku"]["silent"]["k"] == 0 and f["haiku"]["verified"] == 6


def test_the_new_samples_cost_is_reported_per_sample(tmp_path):
    problems, sonnet, haikus = scored([3, 2], [3, 3])
    spend = build(tmp_path, problems, sonnet, haikus)["spend"]
    assert set(spend) == {"sonnet_sample_1", "sonnet_sample_2"}
    assert spend["sonnet_sample_1"]["cost_usd"] == pytest.approx(0.04)
    assert spend["sonnet_sample_2"]["right"] == 1


# ---- the report ---------------------------------------------------------------------------


def test_the_report_is_plain_json(tmp_path):
    problems, sonnet, haikus = scored([3, 2, 1, 0, 3], [2, 2, 2, 2, 2])
    data = build(tmp_path, problems, sonnet, haikus)
    assert json.loads(report.dumps(data)) == data


def test_the_command_writes_the_results_file(tmp_path, monkeypatch):
    problems, sonnet, haikus = scored([3, 2], [1, 3])
    expected = build(tmp_path, problems, sonnet, haikus)  # writes the three records too
    real = report.build
    monkeypatch.setattr(report, "build", lambda run_dir, found: real(
        run_dir, found, tmp_path / "sonnet-0.jsonl", tmp_path / "haiku.jsonl"))  # fmt: skip
    monkeypatch.setattr(second_model_samples, "inputs", lambda tag=True: (problems, "test"))
    monkeypatch.setattr(report, "RESULTS", tmp_path / "out" / "second_model_samples.json")
    report.main([str(tmp_path / "run")])
    written = json.loads((tmp_path / "out" / "second_model_samples.json").read_text())
    assert written == expected and written["s2"]["sonnet_right"] == 5


# ---- scripts/reproduce.py's step for this study ---------------------------------------------


def test_reproduce_has_nothing_to_rebuild_before_the_run(tmp_path):
    found = reproduce.second_model_samples(tmp_path, replay=True, run=tmp_path / "no-run")
    assert found == ({}, [])


def test_reproduce_rebuilds_a_fake_run_in_the_frozen_tree(tmp_path):
    """The whole path the owner's run will take, on a fake run of samples 1 and 2 on all 121
    problems (FakeClient, no API): scripts/reproduce.py extracts the study's tree (its tag's,
    or HEAD's before the tag exists), replays the run there from its cache through
    scripts/replay_run.py, and the frozen analysis's report there is this one, byte for
    byte."""
    from opt_agent import second_model_samples_freeze as gate
    from opt_agent.runs import git

    if not all(p.exists() for p in followup_freeze.data_files()):
        pytest.skip("needs LLM4OR's data (python scripts/fetch_llm4or.py)")
    ref = gate.FREEZE_TAG if gate.tag_exists() else "HEAD"
    committed = git("show", f"{ref}:docs/second_model/SAMPLES_FREEZE.json")
    if committed is None:
        pytest.skip("needs the freeze committed (docs/second_model/SAMPLES_FREEZE.json)")
    approval = gate.SamplesApproval.model_validate_json(committed)
    records = gate.problems()
    model = json.dumps({
        "variables": [{"name": "x", "lower": 0, "upper": None, "integer": False}],
        "objective": {"sense": "max", "terms": [{"var": "x", "coef": 1}]},
        "constraints": [{"name": "cap", "terms": [{"var": "x", "coef": 1}], "sense": "<=",
                         "rhs": 4}],
    })  # fmt: skip
    run, digest = tmp_path / "second-model-samples", freeze.digest(approval.fingerprint)
    second_model_samples.run(FakeClient(*[model] * 2 * len(records)), run, records, digest)
    files, differences = reproduce.second_model_samples(tmp_path / "work", replay=True, run=run,
                                                        tag=ref)  # fmt: skip
    assert differences == []
    expected = report.dumps(report.build(run, records))
    assert files == {"results/second_model_samples.json": expected.encode()}
    assert json.loads(expected)["complete"] is True
