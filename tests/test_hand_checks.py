"""The owner's hand checks of a run (pre-registration 5a): the blind-grading packet, the
error-taxonomy packet, and what the report makes of their sheets. Runs are built with
FakeClient; the expected rows are worked out by hand in the comments. Never calls the API."""

import csv
import json

import pytest
from fakes import GAS_MODEL, INFEASIBLE_REPLY, FakeClient, model
from pytest import approx

from opt_agent import api, blind_grading, evaluate, packets, report, run_results, taxonomy
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.evaluate import CONDITIONS
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records
from opt_agent.schema import LPModel

DEV = {r.id: r for r in load_records(GROUND_TRUTH_DIR / "dev.json")}
GAS = DEV["439170086"]  # integer optimum 251 (LP 250)
LOTION = DEV["-1028228232"]  # infeasible as written
CONTINUOUS_GAS = json.dumps({**GAS_MODEL, "variables": [
    {**v, "integer": False} for v in GAS_MODEL["variables"]]})  # fmt: skip
DROPPED = model([("at least 5", ">=", 5)])  # the infeasible model with "at most 3" deleted


def says(status: str, objective: float | None = None) -> str:
    return json.dumps({"status": status, "objective": objective})


def run(out, *replies, records=(GAS,), conditions=CONDITIONS):
    client = BudgetedClient(FakeClient(*replies), Budget(1.00, out / "spend.jsonl"))
    evaluate.evaluate(list(records), conditions, client, out, "dev")
    return out


@pytest.fixture(autouse=True)
def packets_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(api.time, "sleep", lambda s: None)
    monkeypatch.setattr(taxonomy, "TAXONOMY_DIR", tmp_path / "review" / "taxonomy")
    monkeypatch.setattr(blind_grading, "BLIND_GRADING_DIR", tmp_path / "review" / "blind")


@pytest.fixture
def mixed_run(tmp_path):
    """Gas: the baseline says 251 (right); single-shot makes the trips continuous, 250
    (wrong, silent), and self-correction replays it. Lotion: the baseline and single-shot
    say infeasible (right); self-correction revises, drops a constraint, and claims an
    optimum (wrong, silent, flagged)."""
    return run(tmp_path / "runs" / "mixed", says("optimal", 251), CONTINUOUS_GAS,
               says("infeasible"), INFEASIBLE_REPLY, DROPPED, records=[GAS, LOTION])  # fmt: skip


def as_model(reply: str) -> LPModel:
    return LPModel.model_validate_json(reply)


def fill(path, column, values):
    rows = list(csv.DictReader(path.open(newline="")))
    for row, value in zip(rows, values, strict=True):
        row[column] = value
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


# ---- reading a run back ----------------------------------------------------------------


def test_the_final_model_is_the_last_usable_one_in_its_pass(mixed_run):
    run_id = json.loads((mixed_run / "attempts.jsonl").read_text().splitlines()[0])["run_id"]
    models = run_results.final_models(mixed_run)
    assert models[(LOTION.id, "single-shot", run_id)] == as_model(INFEASIBLE_REPLY)
    assert models[(LOTION.id, "self-correction", run_id)] == as_model(DROPPED)  # attempt 2
    assert models[(GAS.id, "self-correction", run_id)] == as_model(CONTINUOUS_GAS)
    assert not any(condition == "baseline" for _, condition, _ in models)


def test_a_key_names_the_problem_and_the_model():
    gas = as_model(CONTINUOUS_GAS)
    assert run_results.model_key(GAS.id, gas) == run_results.model_key(GAS.id, gas.model_copy())
    assert run_results.model_key(GAS.id, gas) != run_results.model_key(LOTION.id, gas)
    assert run_results.answer_key(GAS.id, "optimal", 250.0) != run_results.model_key(GAS.id, gas)


# ---- the error taxonomy ----------------------------------------------------------------


def test_each_distinct_silent_failure_is_one_row(mixed_run):
    """Gas: single-shot and self-correction gave the same continuous model, one row.
    Lotion: self-correction's revision, flagged. Both baselines were right."""
    gas, lotion = taxonomy.failures(run_results.load(mixed_run))
    assert (gas.problem_id, gas.conditions) == (GAS.id, ["single-shot", "self-correction"])
    assert (gas.status, gas.model) == ("optimal", as_model(CONTINUOUS_GAS))
    assert gas.objective == approx(250)  # CBC's 8 significant digits
    assert (lotion.problem_id, lotion.conditions) == (LOTION.id, ["self-correction"])
    assert lotion.model == as_model(DROPPED) and lotion.flags


def test_the_facts_come_from_the_scores(mixed_run):
    rows = taxonomy.failures(run_results.load(mixed_run))
    gas, lotion = (taxonomy.facts(f, DEV[f.problem_id], rows) for f in rows)
    assert gas == ["Correct if integrality weren't graded (the lenient score, 3f)."]
    assert len(lotion) == 1 and lotion[0].startswith("Revision flags: ")


def test_a_wrong_baseline_answer_points_to_a_model_with_the_same_answer(tmp_path):
    out = run(tmp_path / "runs" / "same", says("optimal", 250), CONTINUOUS_GAS,
              conditions=("baseline", "single-shot"))  # fmt: skip
    rows = taxonomy.failures(run_results.load(out))
    baseline, single = rows
    assert baseline.model is None and baseline.key == run_results.answer_key(GAS.id, "optimal", 250)
    assert "The same answer as row 2's model." in taxonomy.facts(baseline, GAS, rows)
    assert "The same answer" not in " ".join(taxonomy.facts(single, GAS, rows))


def test_the_taxonomy_packet_and_its_sheet(mixed_run):
    out, n = taxonomy.write_packet(mixed_run)
    text = (out / "PACKET.md").read_text()
    assert n == 2 and "## 2. `-1028228232`: self-correction" in text
    assert all(f"| `{name}` |" in text for name in taxonomy.CATEGORIES)
    assert "**Answered:** optimal 250" in text and "**Accepted:** optimal 251 (annotated)" in text
    rows = list(csv.DictReader((out / "labels.csv").open()))
    assert [r["conditions"] for r in rows] == ["single-shot self-correction", "self-correction"]


def test_a_regenerated_taxonomy_packet_keeps_the_labels(mixed_run):
    taxonomy.write_packet(mixed_run)
    sheet = taxonomy.sheet_path("mixed")
    fill(sheet, "category", ["integrality", "missing-constraint"])
    taxonomy.write_packet(mixed_run)
    assert set(taxonomy.read_labels(sheet).values()) == {"integrality", "missing-constraint"}


def test_only_listed_categories_are_accepted(mixed_run):
    taxonomy.write_packet(mixed_run)
    fill(taxonomy.sheet_path("mixed"), "category", ["integrality", "sloppiness"])
    with pytest.raises(ValueError, match="'sloppiness' isn't a category"):
        taxonomy.read_labels(taxonomy.sheet_path("mixed"))


def test_the_taxonomy_counts_per_condition(mixed_run):
    run = run_results.load(mixed_run)
    assert "pending" in taxonomy.summary(run)
    taxonomy.write_packet(mixed_run)
    fill(taxonomy.sheet_path("mixed"), "category", ["integrality", ""])
    partial = taxonomy.summary(run)
    assert not partial["complete"]
    assert partial["by condition"] == {"baseline": {}, "single-shot": {"integrality": 1},
        "self-correction": {"integrality": 1, "unlabeled": 1}}  # fmt: skip
    fill(taxonomy.sheet_path("mixed"), "category", ["integrality", "missing-constraint"])
    assert taxonomy.summary(run)["complete"]


# ---- blind grading ---------------------------------------------------------------------


def test_the_pool_is_every_distinct_confirmed_model(mixed_run):
    """Gas: one continuous model (both conditions), wrong. Lotion: single-shot's
    infeasible model, right, and self-correction's revision, wrong. No baseline."""
    pool = blind_grading.pool(run_results.load(mixed_run))
    found = {(f.problem_id, f.model.model_dump_json(), f.scored_right) for f in pool}
    assert found == {
        (GAS.id, as_model(CONTINUOUS_GAS).model_dump_json(), False),
        (LOTION.id, as_model(INFEASIBLE_REPLY).model_dump_json(), True),
        (LOTION.id, as_model(DROPPED).model_dump_json(), False),
    }
    assert [f.key for f in pool] == sorted(f.key for f in pool)


def test_the_sample_is_stratified_and_seeded(mixed_run):
    pool = blind_grading.pool(run_results.load(mixed_run))
    small = blind_grading.draw(pool, size=2)  # at most 1 of the 2 wrong ones, then 1 right
    assert sorted(f.scored_right for f in small) == [False, True]
    assert blind_grading.draw(pool, size=2) == small
    assert len(blind_grading.draw(pool)) == 3  # 40 asked for, 3 in the pool


def test_the_blind_packet_shows_no_answer_score_condition_or_id(mixed_run):
    out, n = blind_grading.write_packet(mixed_run)
    text = (out / "PACKET.md").read_text()
    assert n == 3 and text.count("To grade:") == 3
    for hidden in ("250", "251", "infeasible", "single-shot", "self-correction", "wrong.",
                   GAS.id, LOTION.id):  # fmt: skip
        assert hidden not in text.split("## 1.")[1], hidden
    assert list(csv.DictReader((out / "grades.csv").open()))[0].keys() == {
        "number", "key", "grade", "note", "grader"}  # fmt: skip


def test_grades_are_compared_with_scores_per_stratum(mixed_run):
    run = run_results.load(mixed_run)
    by_key = {f.key: f for f in blind_grading.pool(run)}
    gas = run_results.model_key(GAS.id, as_model(CONTINUOUS_GAS))
    kept = run_results.model_key(LOTION.id, as_model(INFEASIBLE_REPLY))
    dropped = run_results.model_key(LOTION.id, as_model(DROPPED))
    assert {gas, kept, dropped} == set(by_key)
    # The grader calls the continuous gas model right (the score says wrong), agrees on the
    # other two... except that they're unsure about the dropped constraint.
    grades = {gas: ("right", "trips could be fractional"), kept: ("right", ""),
              dropped: ("unsure", "")}  # fmt: skip
    a = blind_grading.agreement(list(by_key.values()), grades)
    assert a["strata"]["scored right"] == {"graded right": 1, "graded wrong": 0, "unsure": 0,
        "agree": 1, "n": 1, "wilson95": [approx(0.2065, abs=1e-4), 1.0]}  # fmt: skip
    wrong = a["strata"]["scored wrong"]
    assert (wrong["agree"], wrong["n"], wrong["unsure"]) == (0, 1, 1)
    assert a["disagreements"] == [
        {
            "problem_id": GAS.id,
            "key": gas,
            "graded": "right",
            "note": "trips could be fractional",
            "scored": "wrong",
        }
    ]
    with pytest.raises(ValueError, match="aren't in this run's pool"):
        blind_grading.agreement(list(by_key.values()), {**grades, "nope": ("right", "")})


def test_blind_grades_are_pending_until_every_row_is_graded(mixed_run):
    run = run_results.load(mixed_run)
    assert "no packet yet" in blind_grading.summary(run)["pending"]
    blind_grading.write_packet(mixed_run)
    fill(blind_grading.sheet_path("mixed"), "grade", ["right", "", "wrong"])
    assert "isn't filled in yet" in blind_grading.summary(run)["pending"]
    fill(blind_grading.sheet_path("mixed"), "grade", ["right", "maybe", "wrong"])
    assert "'maybe' is none of" in blind_grading.summary(run)["pending"]


def test_a_regenerated_blind_packet_keeps_the_grades(mixed_run):
    blind_grading.write_packet(mixed_run)
    fill(blind_grading.sheet_path("mixed"), "grade", ["right", "wrong", "unsure"])
    before = blind_grading.read_grades(blind_grading.sheet_path("mixed"))
    blind_grading.write_packet(mixed_run)
    assert blind_grading.read_grades(blind_grading.sheet_path("mixed")) == before


# ---- in the report ---------------------------------------------------------------------


def test_the_report_carries_the_hand_checks_and_hashes_their_sheets(mixed_run):
    pending = report.build(mixed_run)
    assert all("pending" in check for check in pending["hand_checks"].values())
    assert pending["provenance"]["hand_check_sheets_sha256"] == {}
    blind_grading.write_packet(mixed_run)
    fill(blind_grading.sheet_path("mixed"), "grade", ["right", "right", "right"])
    taxonomy.write_packet(mixed_run)
    fill(taxonomy.sheet_path("mixed"), "category", ["integrality", "missing-constraint"])
    r = report.build(mixed_run)
    assert r["hand_checks"]["taxonomy"]["complete"]
    assert r["hand_checks"]["blind grading"]["strata"]["scored wrong"]["graded right"] == 2
    assert set(r["provenance"]["hand_check_sheets_sha256"]) == {
        "blind/mixed/grades.csv", "taxonomy/mixed/labels.csv"}  # fmt: skip


# ---- an LLM judge's reply ----------------------------------------------------------------


def reply(tmp_path, text: str):
    path = tmp_path / "reply.csv"
    path.write_text(text)
    return path


def test_a_judges_reply_merges_by_number_and_names_the_judge(mixed_run, tmp_path):
    blind_grading.write_packet(mixed_run)
    sheet = blind_grading.sheet_path("mixed")
    answer = reply(tmp_path, 'number,grade,note\n3,wrong,\n1,right,"fine"\n2,unsure,\n')
    assert packets.merge_reply(sheet, answer, ["grade", "note"], "Some model, LLM judge") == 3
    rows = list(csv.DictReader(sheet.open()))
    assert [(r["number"], r["grade"]) for r in rows] == [("1", "right"), ("2", "unsure"),
                                                         ("3", "wrong")]  # fmt: skip
    assert blind_grading.summary(run_results.load(mixed_run))["graders"] == [
        "Some model, LLM judge"]  # fmt: skip


@pytest.mark.parametrize("text, problem", [
    ("number,grade,note\n1,right,\n2,right,\n", "not each of"),  # a row skipped
    ("number,grade,note\n1,right,\n2,right,\n2,wrong,\n3,right,\n", "not each of"),  # doubled
    ("number,key,grade,note\n1,abc,right,\n2,abc,right,\n3,abc,right,\n", "key 'abc'"),
])  # fmt: skip
def test_a_reply_that_skips_doubles_or_shifts_a_row_is_refused(mixed_run, tmp_path, text,
                                                               problem):  # fmt: skip
    blind_grading.write_packet(mixed_run)
    with pytest.raises(ValueError, match=problem):
        packets.merge_reply(blind_grading.sheet_path("mixed"), reply(tmp_path, text),
                            ["grade", "note"], "judge")  # fmt: skip


def test_the_llm_prompt_names_neither_the_system_nor_the_labels_author(mixed_run):
    out, _ = taxonomy.write_packet(mixed_run)
    prompt = (out / "LLM_PROMPT.md").read_text()
    assert "Claude" not in prompt and "(claude)" not in prompt and "(rule)" not in prompt
    assert "`number,key,category,note`" in prompt and "The system's model:" in prompt
    for f in taxonomy.failures(run_results.load(mixed_run)):
        assert f"(key `{f.key}`)" in prompt


def test_the_blind_packet_says_when_a_label_is_either():
    label = GAS.integrality.model_copy(update={"kind": "either", "source": "judge"})
    assert "`either`" in " ".join(
        blind_grading._either(GAS.model_copy(update={"integrality": label}))
    )
    assert blind_grading._either(GAS) == []
