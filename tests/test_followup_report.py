"""The follow-up's analysis on synthetic answers: every number checked against a hand count
or an independent computation. No API calls, no follow-up test data."""

import json

import numpy as np
import pytest

from opt_agent import followup, stats
from opt_agent import followup_report as fr
from opt_agent.evaluate import FOLLOWUP_CONDITIONS, Item

CONDITIONS = list(FOLLOWUP_CONDITIONS)
SAMPLES = [0, 1, 2]
KEY = 100.0


def item(pid, condition, sample, objective=KEY, status="optimal", **extra) -> Item:
    if objective is None and status == "optimal":
        status = None  # a loud failure
    return Item(problem_id=str(pid), split="complexlp-dev", condition=condition,
                outcome=extra.pop("outcome", "done"), sample=sample, model_id="m",
                settings_sha256="s", status=status, objective=objective, **extra)  # fmt: skip


def problems(n, key=KEY) -> dict[str, followup.Problem]:
    return {f"complexlp:{i}": followup.Problem(id=str(i), document="", answer=key)
            for i in range(n)}  # fmt: skip


def grid_items(right: dict[str, list[int]], n_problems: int) -> list[Item]:
    """right[condition][i]: how many of problem i's 3 samples are right (the rest answer 1)."""
    out = []
    for c in CONDITIONS:
        for i in range(n_problems):
            for s in SAMPLES:
                out.append(item(i, c, s, KEY if s < right[c][i] else 1.0))
    return out


def build(items, n, exposed=frozenset(), **kw):
    return fr.build(items, CONDITIONS, SAMPLES, problems(n), set(exposed), **kw)


ALL_RIGHT = dict.fromkeys(CONDITIONS, [3] * 6)


def test_a_problem_counts_only_when_every_condition_and_sample_is_done():
    items = grid_items(ALL_RIGHT, 6)
    items = [i for i in items if not (i.problem_id == "4" and i.sample == 2
                                      and i.condition == "baseline")]  # fmt: skip
    items.append(item(5, "single-shot", 1, outcome="errored"))  # a later errored line
    report = build(items, 6)
    assert report["complete_problems"] == 4
    assert report["incomplete_problems"] == ["complexlp:4", "complexlp:5"]
    assert report["rows"]["sensitivity (all)"]["problems"] == 4


def test_scores_and_majorities_are_hand_counts():
    right = {**ALL_RIGHT, "baseline": [3, 2, 1, 0, 3, 3]}
    report = build(grid_items(right, 6), 6)
    a = report["rows"]["sensitivity (all)"]["accuracy"]["baseline"]
    assert a["mean_score"] == pytest.approx((3 + 2 + 1 + 0 + 3 + 3) / 18)
    assert a["majority_right"] == 4  # 3, 2, 3, 3 of 3
    assert a["majority_wilson"] == list(stats.wilson(4, 6))


def test_a_contrast_matches_its_tests_computed_directly():
    counts = {f"p{i}": {"a": a, "b": b} for i, (a, b) in
              enumerate([(0, 3), (1, 3), (2, 2), (3, 1), (0, 2), (1, 1), (0, 3)])}  # fmt: skip
    c = fr.contrast(counts, "a", "b", 3)
    diffs = [3, 2, 0, -2, 2, 0, 3]
    assert c["sign_flip_p"] == stats.sign_flip_exact(diffs)
    assert c["score_difference"] == pytest.approx(sum(diffs) / 7 / 3)
    # majority (> 1.5 right): a = [F, F, T, T, F, F, F], b = [T, T, T, F, T, F, T]
    assert (c["majority_only_a"], c["majority_only_b"]) == (1, 4)
    assert c["mcnemar_p"] == stats.mcnemar_exact(1, 4)
    assert (c["problems_b_better"], c["problems_a_better"]) == (4, 1)


def test_holm_is_applied_over_h1_and_h2_for_each_test():
    right = {"baseline": [0] * 20, "single-shot": [3] * 20, "self-correction": [3] * 20,
             "checklist-revision": [3] * 19 + [2]}  # fmt: skip
    found = build(grid_items(right, 20), 20)["rows"]["sensitivity (all)"]["primary"]
    raw = {name: c["sign_flip_p"] for name, c in found.items()}
    assert {n: c["sign_flip_p_holm"] for n, c in found.items()} == stats.holm(raw)
    raw = {name: c["mcnemar_p"] for name, c in found.items()}
    assert {n: c["mcnemar_p_holm"] for n, c in found.items()} == stats.holm(raw)
    assert found["H2"]["verdict"] == "detected"  # 20 of 20 problems, all one way
    assert found["H1"]["verdict"] == "inconclusive"
    assert found["H1"]["no_difference_larger_than_pp"] == fr.bound_pp(found["H1"]["score_ci"])
    assert "no_difference_larger_than_pp" not in found["H2"]


def test_the_bound_is_the_smallest_whole_x_containing_the_interval():
    assert fr.bound_pp([-0.031, 0.02]) == 4
    assert fr.bound_pp([-0.03, 0.05]) == 5  # exactly 5 pp: inside +/-5
    assert fr.bound_pp([0.0, 0.0]) == 0


def test_the_bootstrap_is_seeded_and_brackets_the_mean():
    values = np.array([0, 1, 1, 0.5, 0, 1, 2 / 3, 1 / 3])
    first, again = fr.bootstrap_ci(values), fr.bootstrap_ci(values)
    assert first == again and first[0] < values.mean() < first[1]
    assert fr.bootstrap_ci(np.full(9, 0.25)) == [0.25, 0.25]


def test_the_primary_row_leaves_out_the_exposed_problems():
    right = {**ALL_RIGHT, "baseline": [0, 3, 3, 3, 3, 3]}
    report = build(grid_items(right, 6), 6, exposed={"complexlp:0", "industryor:9"})
    rows = report["rows"]
    assert rows["primary (unexposed)"]["accuracy"]["baseline"]["majority_right"] == 5
    assert rows["primary (unexposed)"]["problems"] == 5
    assert rows["sensitivity (all)"]["accuracy"]["baseline"]["majority_right"] == 5
    assert rows["sensitivity (all)"]["problems"] == 6
    assert report["exposed_left_out"] == ["complexlp:0"]


def test_the_exposed_labels_come_from_the_split_file():
    split = {
        "seen_before_the_split": {"complexlp": {"1": "x", "193": "y"}, "industryor": {"9": "z"}}
    }
    assert fr.exposed_labels(split) == {"complexlp:1", "complexlp:193", "industryor:9"}


def majority_items(answers: dict[str, list[float | None]]) -> list[Item]:
    """One problem: each condition's three answers."""
    return [item(0, c, s, a) for c, values in answers.items() for s, a in enumerate(values)]


def test_three_conditions_agreeing_on_a_wrong_value_trigger_a_dispute():
    answers = {
        "baseline": [212, 212, 199],
        "single-shot": [212, 212.0001, 5],
        "self-correction": [212, 9, 212],
        "checklist-revision": [7, 8, 9],
    }
    report = fr.build(majority_items(answers), CONDITIONS, SAMPLES,
                      problems(1, key=199), set())  # fmt: skip
    [d] = report["disputes"]
    assert d["problem"] == "complexlp:0" and d["key"] == 199 and d["answer"][1] == 212
    assert d["conditions"] == ["baseline", "self-correction", "single-shot"]


@pytest.mark.parametrize("answers", [
    # only two conditions agree on 212
    {"baseline": [212] * 3, "single-shot": [212] * 3, "self-correction": [1, 2, 3],
     "checklist-revision": [4, 5, 6]},
    # three agree, but on the key
    {"baseline": [199] * 3, "single-shot": [199] * 3, "self-correction": [199] * 3,
     "checklist-revision": [4, 5, 6]},
    # 212 in every condition, but once each: no majority anywhere
    {c: [212, 1, None] for c in CONDITIONS},
    # loud failures agree with each other, but they aren't an answer
    {c: [None, None, 3] for c in CONDITIONS},
])  # fmt: skip
def test_no_dispute_otherwise(answers):
    report = fr.build(majority_items(answers), CONDITIONS, SAMPLES, problems(1, key=199), set())
    assert report["disputes"] == []


def test_agreement_uses_the_scoring_tolerance():
    assert fr.same_answer(("optimal", 100.0), ("optimal", 100.005))  # 5e-5 relative
    assert not fr.same_answer(("optimal", 100.0), ("optimal", 100.02))
    assert fr.same_answer(("infeasible", None), ("infeasible", None))
    assert not fr.same_answer(("infeasible", None), None)


def test_corrected_keys_are_a_separate_row_for_every_condition():
    answers = {c: [212] * 3 for c in CONDITIONS}
    report = fr.build(majority_items(answers), CONDITIONS, SAMPLES, problems(1, key=199), set(),
                      corrected_keys={"complexlp:0": 212.0})  # fmt: skip
    raw = report["rows"]["primary (unexposed)"]["accuracy"]
    fixed = report["rows"]["corrected keys (unexposed)"]["accuracy"]
    assert all(
        raw[c]["majority_right"] == 0 and fixed[c]["majority_right"] == 1 for c in CONDITIONS
    )


def test_failures_split_loud_and_silent():
    answers = {**{c: [KEY] * 3 for c in CONDITIONS}, "single-shot": [KEY, None, 3.0]}
    report = fr.build(majority_items(answers), CONDITIONS, SAMPLES, problems(1), set())
    assert report["failures"]["single-shot"] == {"loud": 1, "silent": 1}


def test_revisions_count_moves_from_the_answer_they_started_from():
    base = [item(0, c, s) for c in CONDITIONS[:3] for s in SAMPLES]
    mine = [
        item(0, "checklist-revision", 0, KEY, revised=True, revision_kept=True,
             original_status="optimal", original_objective=5.0,
             checklist_flags=[{"kind": "missing", "detail": ""}]),
        item(0, "checklist-revision", 1, 5.0, revised=True, revision_kept=True,
             original_status="optimal", original_objective=KEY,
             checklist_flags=[{"kind": "extra", "detail": ""}, {"kind": "missing", "detail": ""}]),
        item(0, "checklist-revision", 2, KEY, revised=True, revision_kept=False,
             original_status="optimal", original_objective=KEY,
             checklist_flags=[{"kind": "extra", "detail": ""}]),
    ]  # fmt: skip
    r = fr.build(base + mine, CONDITIONS, SAMPLES, problems(1), set())["checklist_revision"]
    assert (r["answers"], r["revised"], r["kept"], r["discarded"]) == (3, 3, 2, 1)
    assert (r["wrong_to_right"], r["right_to_wrong"]) == (1, 1)
    assert r["flags_by_kind"] == {"extra": 2, "missing": 2}


def test_drops_are_tabulated_against_correctness():
    items = [item(0, c, s, KEY if s else 1.0, dropped=["spare"] if s == 0 else [])
             for c in CONDITIONS for s in SAMPLES]  # fmt: skip
    d = fr.build(items, CONDITIONS, SAMPLES, problems(1), set())["unused_variable_drops"]
    # solver conditions only: 3 conditions x sample 0 dropped and wrong, x samples 1-2 right
    assert d["with_drop"] == {"right": 0, "wrong": 3}
    assert d["without_drop"] == {"right": 6, "wrong": 0}
    assert d["label"] == "exploratory" and d["fisher_p"] < 0.05


def test_sample_agreement_is_the_share_of_agreeing_pairs():
    answers = {**{c: [KEY] * 3 for c in CONDITIONS}, "baseline": [KEY, KEY, 3.0]}
    report = fr.build(majority_items(answers), CONDITIONS, SAMPLES, problems(1), set())
    assert report["sample_agreement"]["baseline"] == pytest.approx(1 / 3)
    assert report["sample_agreement"]["single-shot"] == 1.0


def test_same_inputs_same_report():
    right = {c: list(np.random.default_rng(7).integers(0, 4, 30)) for c in CONDITIONS}
    items = grid_items(right, 30)
    first = json.dumps(build(items, 30), sort_keys=True)
    assert first == json.dumps(build(list(reversed(items)), 30), sort_keys=True)


def test_a_run_of_one_condition_reports_without_contrasts():
    items = [item(0, "checklist-revision", s) for s in SAMPLES]
    report = fr.build(items, ["checklist-revision"], SAMPLES, problems(1), set())
    row = report["rows"]["primary (unexposed)"]
    assert row["primary"] == {} and row["exploratory"] == {}
    assert row["accuracy"]["checklist-revision"]["majority_right"] == 1


def test_samples_come_from_the_manifest():
    assert fr.samples_of({"settings": {"samples": "0,1,2"}}) == [0, 1, 2]
    assert fr.samples_of({"settings": {"sample": "2"}}) == [2]
    assert fr.samples_of({"settings": {}}) == [0]


@pytest.mark.skipif(not followup.COMPLEXLP.exists(), reason="needs LLM4OR's data")
def test_a_run_directory_reports_end_to_end(tmp_path, capsys):
    from fakes import GAS_CHECKLIST_REPLY, GAS_REPLY, FakeClient

    from opt_agent import evaluate

    [dev] = [p for p in followup.load("complexlp-dev") if p.id == "19"]
    client = FakeClient(GAS_REPLY, GAS_CHECKLIST_REPLY)  # mocked replies to a real dev problem
    evaluate.evaluate([dev], ("checklist-revision",), client, tmp_path, "complexlp-dev")
    fr.main([str(tmp_path)])
    report = json.loads((tmp_path / "followup_report.json").read_text())
    assert report["complete_problems"] == 1 and report["samples"] == [0]
    assert report["conditions"] == ["checklist-revision"]
    assert "1 complete problems" in capsys.readouterr().out


def test_one_sample_gives_no_agreement_and_no_nan():
    """Found on the dev smoke run (one sample): the agreement was NaN, which isn't JSON. Empty
    subsets give None the same way."""
    grid = {"a": {"single-shot": [item(1, "single-shot", 0)]}}
    assert fr.sample_agreement(grid, "single-shot") is None
    assert fr.bootstrap_ci(np.array([])) is None and fr.bound_pp(None) is None
    row = fr.analysis_row({}, ["baseline", "single-shot"], 3)
    json.dumps(row, allow_nan=False)  # raises on NaN
