"""The external cross-check (pre-registration, Amendment 2): matching by text, and each
verdict, on dev problems with hand-made benchmark answers. Needs no download and never
calls the API."""

import csv
import json

import pytest

from opt_agent import external_check, orlm, packets
from opt_agent.external_check import Match, match, verdict
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records, readings

DEV = {r.id: r for r in load_records(GROUND_TRUTH_DIR / "dev.json")}
GAS = DEV["439170086"]  # integer label: IP 251, LP 250
LOTION = DEV["-1028228232"]  # infeasible as written


def answers(*pairs: tuple[str, str]) -> dict[str, str]:
    return {orlm.normalize(text): answer for text, answer in pairs}


def test_problems_match_by_text_or_by_an_edited_text():
    edited = GAS.document.replace("at least twice", "at least three times")
    other = "A farmer grows wheat and corn on 100 acres to maximize profit."
    found, unmatched = match([GAS, LOTION], answers((LOTION.document.upper(), "No Best Solution"),
                                                    (edited, "300.0"), (other, "5.0")))  # fmt: skip
    assert found == [
        Match(problem_id=LOTION.id, answer="No Best Solution"),
        Match(problem_id=GAS.id, answer="300.0", edits=["'twice' -> 'three times'"]),
    ]
    assert unmatched == [orlm.normalize(other)]


@pytest.mark.parametrize(
    "record, answer, expected",
    [
        (GAS, "251.0", "agrees"),
        (GAS, "251.01", "agrees"),  # within 1e-4: published values are rounded
        (GAS, "250", "other integrality"),  # the LP optimum on an integer-labeled problem
        (GAS, "260", "disagrees"),
        (GAS, "No Best Solution", "disagrees"),
        (LOTION, "No Best Solution", "agrees"),
        (LOTION, "5", "disagrees"),
    ],
)
def test_each_verdict(record, answer, expected):
    assert verdict(record, answer) == expected


def test_another_accepted_reading_is_told_apart():
    """Dev -1384117219: "twice as many" read as "=" (the ratio-wording rule) gives 230,
    as annotated 500."""
    r = DEV["-1384117219"]
    assert [(reading, s.objective) for reading, s in readings(r)] == [
        ("annotated", 500), ("equality", 230)]  # fmt: skip
    assert verdict(r, "230.0") == "agrees with another reading"
    assert verdict(r, "500.0") == "agrees"


def test_an_answer_that_is_neither_a_number_nor_no_optimum_is_refused():
    with pytest.raises(ValueError):
        verdict(GAS, "the optimal value is 251")


def test_the_list_shows_disagreements_and_what_it_cannot_check():
    records = [GAS, LOTION]
    text = external_check.render(records, [Match(problem_id=GAS.id, answer="250.0")], [])
    assert "## Other integrality" in text and f"| `{GAS.id}` |" in text
    assert "| other integrality | 1 | 0 |" in text and "| not in the benchmark | 1 | 1 |" in text
    uncovered = text.split("## Reviewed, but not in the benchmark (1)")[1]
    assert f"| `{LOTION.id}` | text-has-no-optimum | yes |" in uncovered


def test_the_owner_decides_label_questions_edits_and_uncovered_reviews(tmp_path):
    edited = Match(problem_id=GAS.id, answer="251.0", edits=["'twice' -> 'three times'"])
    decide = external_check.to_decide([GAS, LOTION], [edited])
    assert decide == {"disagrees": [], "other integrality": [], "edited text": [GAS.id],
                      "not cross-checked": [LOTION.id]}  # fmt: skip
    assert external_check.to_decide([GAS], [Match(problem_id=GAS.id, answer="250")])[
        "other integrality"] == [GAS.id]  # fmt: skip
    sheet = tmp_path / "decisions.csv"
    external_check.decision_sheet(decide, sheet)
    rows = sheet.read_text().replace(f"{LOTION.id},not cross-checked,,",
                                     f"{LOTION.id},not cross-checked,confirmed,")  # fmt: skip
    sheet.write_text(rows)
    external_check.decision_sheet(decide, sheet)  # regenerating keeps the decision
    decisions = {r["problem_id"]: r["decision"] for r in external_check.read_decisions(sheet)}
    assert decisions == {GAS.id: "", LOTION.id: "confirmed"}
    sheet.write_text(
        sheet.read_text().replace(f"{GAS.id},edited text,,", f"{GAS.id},edited text,confirmed,")
    )
    with pytest.raises(ValueError, match="none of keep, change"):
        external_check.read_decisions(sheet)


BENCHMARK = external_check.DATA_DIR / external_check.ORLM_BENCHMARK.path


@pytest.mark.skipif(not BENCHMARK.exists(), reason="the benchmark isn't downloaded (CI)")
def test_the_committed_list_and_sheet_are_up_to_date():
    records = load_records(GROUND_TRUTH_DIR / "test.json")
    matches, unmatched = match(records, orlm.load_answers(BENCHMARK))
    committed = external_check.EXTERNAL_CHECK_PATH.read_text()
    assert committed == external_check.render(records, matches, unmatched)
    rows = external_check.read_decisions(external_check.DECISIONS_PATH)
    listed = external_check._pairs(external_check.to_decide(records, matches))
    assert listed <= {(r["problem_id"], r["why"]) for r in rows}
    # A row the list no longer names is a settled decision, kept as the record.
    assert all(r["decision"] for r in rows if (r["problem_id"], r["why"]) not in listed)


def test_an_either_label_has_no_other_integrality():
    either = GAS.model_copy(update={"integrality": GAS.integrality.model_copy(
        update={"kind": "either", "source": "judge"})})  # fmt: skip
    assert verdict(either, "250") == "agrees" and verdict(either, "251") == "agrees"
    assert verdict(either, "260") == "disagrees"


# ---- the judges' verdicts on the reviews it leaves (Amendment 2, part 6) ----------------

TEST = load_records(GROUND_TRUTH_DIR / "test.json")


def test_the_review_judges_get_the_uncovered_reviews_then_the_hard_cases():
    judged = external_check.judged_reviews(TEST)
    uncovered = [row["problem_id"] for row in external_check.read_decisions(
        external_check.DECISIONS_PATH) if row["why"] == external_check.UNCOVERED]  # fmt: skip
    assert [r.id for r in judged] == uncovered + external_check.HARD_CASES
    assert len(uncovered) == 24 and all(r.review for r in judged[:24])


def test_the_review_prompt_names_neither_the_system_nor_the_benchmark():
    judged = external_check.judged_reviews(TEST)
    prompt = external_check.review_prompt(judged)
    assert prompt.count("\n## ") == 26 and "`number,problem_id,judgment,reason`" in prompt
    assert "claude" not in prompt.lower() and "benchmark" not in prompt.lower()
    assert "orlm" not in prompt.lower()  # redacted from one reason (REDACTED)
    assert all(r.document in prompt for r in judged)
    assert external_check.NO_REVIEW in prompt  # 1283305022 has no review


def test_the_committed_review_packet_is_up_to_date():
    judged = external_check.judged_reviews(TEST)
    folder = external_check.REVIEW_JUDGE_DIR
    assert (folder / "LLM_PROMPT.md").read_text() == external_check.review_prompt(judged)
    for name in ("judge.csv", "second_judge.csv"):  # judgments may be filled in by now
        rows = [row[:3] for row in csv.reader((folder / name).open())]
        assert rows == [["number", "problem_id", "review"]] + [
            [str(n), r.id, r.review.verdict if r.review else "none"]
            for n, r in enumerate(judged, 1)]  # fmt: skip


def test_a_review_is_confirmed_only_if_both_judges_agree():
    judge = {"a": "agree", "b": "agree", "c": "unsure", "d": "disagree"}
    second = {"a": "agree", "b": "unsure", "c": "agree", "d": "agree"}
    assert external_check.review_outcomes(judge, second) == {
        "a": "confirmed", "b": "disputed", "c": "disputed", "d": "disputed"}  # fmt: skip


def test_judgments_merge_and_must_be_one_of_three(tmp_path):
    judged = external_check.judged_reviews(TEST)[:2]
    sheet = tmp_path / "judge.csv"
    external_check.review_sheet(judged, sheet)
    reply = tmp_path / "reply.csv"
    first, second = judged
    reply.write_text(f'number,problem_id,judgment,reason\n1,{first.id},agree,"ok"\n'
                     f"2,{second.id},maybe,\n")  # fmt: skip
    packets.merge_reply(sheet, reply, ["judgment", "reason"], "judge")
    with pytest.raises(ValueError, match="'maybe' is none of agree, disagree, unsure"):
        external_check.read_judgments(sheet)


def test_a_hard_case_can_be_excluded_but_a_label_question_cant(tmp_path):
    sheet = tmp_path / "decisions.csv"
    sheet.write_text("problem_id,why,decision,note\n1283305022,edited text,exclude,\n"
                     "-1715698555,disagrees,exclude,\n")  # fmt: skip
    assert [r["decision"] for r in external_check.read_decisions(sheet)] == ["exclude"] * 2
    sheet.write_text("problem_id,why,decision,note\n-38093970,other integrality,exclude,\n")
    with pytest.raises(ValueError, match="none of keep, change"):
        external_check.read_decisions(sheet)


def test_a_redaction_leaves_reviews_json_alone_and_must_still_match():
    r = next(r for r in TEST if r.id in external_check.REDACTED)
    assert external_check.REDACTED[r.id] in r.review.reason  # reviews.json keeps it
    assert external_check.REDACTED[r.id] not in external_check._shown_reason(r)
    changed = r.model_copy(update={"review": r.review.model_copy(update={"reason": "new"})})
    with pytest.raises(ValueError, match="update REDACTED"):
        external_check._shown_reason(changed)


def review_sheets(tmp_path, monkeypatch, first: dict[str, str], second: dict[str, str]):
    """Both review judges' sheets in tmp_path, from {problem id: judgment}."""
    monkeypatch.setattr(external_check, "REVIEW_JUDGE_DIR", tmp_path)
    judged = external_check.judged_reviews(TEST)
    for name, judgments in (("judge.csv", first), ("second_judge.csv", second)):
        external_check.review_sheet(judged, tmp_path / name)
        reply = tmp_path / f"{name}.reply"
        reply.write_text("number,problem_id,judgment,reason\n" + "".join(
            f"{n},{r.id},{judgments.get(r.id, 'agree')},\n"
            for n, r in enumerate(judged, 1)))  # fmt: skip
        packets.merge_reply(tmp_path / name, reply, ["judgment", "reason"], "judge")
    return [r.id for r in judged]


def test_the_judges_decide_reviews_and_hard_cases_by_the_rules(tmp_path, monkeypatch):
    """The edited hard case gets an unsure from one judge: excluded. The other has two
    agrees: kept. Every review both agree with is confirmed."""
    ids = review_sheets(tmp_path, monkeypatch, {"1283305022": "unsure"}, {})
    uncovered, (edited, ambiguous) = ids[:24], ids[24:]
    decided = external_check.judged_decisions()
    assert decided[edited][0] == "exclude" and "judge of record: unsure" in decided[edited][1]
    assert decided[ambiguous] == ("keep", "rule (part 5): both judges agree")
    assert all(decided[i][0] == "confirmed" for i in uncovered)


def test_one_judges_doubt_disputes_a_review(tmp_path, monkeypatch):
    first = external_check.judged_reviews(TEST)[0].id
    review_sheets(tmp_path, monkeypatch, {}, {first: "unsure"})
    decision, note = external_check.judged_decisions()[first]
    assert decision == "disputed" and "second judge: unsure" in note


def test_applying_the_decisions_writes_each_into_its_hand_input(tmp_path, monkeypatch):
    for name in ("REVIEWS_PATH", "EXCLUSIONS_PATH", "INTEGRALITY_PATH"):
        copy = tmp_path / name
        copy.write_text(getattr(external_check, name).read_text())
        monkeypatch.setattr(external_check, name, copy)
    uncovered = next(r.id for r in external_check.judged_reviews(TEST))
    sheet = tmp_path / "decisions.csv"
    sheet.write_text("problem_id,why,decision,note\n"
                     f"{uncovered},not cross-checked,disputed,\n"
                     "102495722,edited text,exclude,the judges differ\n"
                     "-38093970,other integrality,change,\n"
                     "-443833341,other integrality,keep,\n")  # fmt: skip
    assert external_check.apply_decisions(sheet) == {"reviews": 1, "exclusions": 1, "labels": 1}
    reviews = {r["id"]: r for r in json.loads((tmp_path / "REVIEWS_PATH").read_text())["reviews"]
               if r["split"] == "test"}  # fmt: skip
    assert reviews[uncovered]["judged"] == "disputed"
    excluded = json.loads((tmp_path / "EXCLUSIONS_PATH").read_text())["exclusions"]
    assert any(e["id"] == "102495722" and "the judges differ" in e["reason"] for e in excluded)
    labels = {r["id"]: r for r in json.loads((tmp_path / "INTEGRALITY_PATH").read_text())["labels"]
              if r["split"] == "test"}  # fmt: skip
    assert (labels["-38093970"]["kind"], labels["-38093970"]["source"]) == ("either", "owner")
    sheet.write_text("problem_id,why,decision,note\n-1715698555,disagrees,change,\n")
    with pytest.raises(ValueError, match="no rule changes a disagrees"):
        external_check.apply_decisions(sheet)


def test_a_regenerated_sheet_keeps_settled_rows_and_appends_new_ones(tmp_path):
    sheet = tmp_path / "decisions.csv"
    sheet.write_text("problem_id,why,decision,note\n"
                     "a,other integrality,change,rule\nb,disagrees,,\n")  # fmt: skip
    external_check.decision_sheet({"disagrees": [], "edited text": ["c"]}, sheet)
    rows = [(r["problem_id"], r["decision"]) for r in external_check.read_decisions(sheet)]
    assert rows == [("a", "change"), ("c", "")]  # b was undecided and is no longer listed
