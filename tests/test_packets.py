import csv
import re

import pytest

from opt_agent import packets
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records
from opt_agent.packets import (
    BLIND_DIR,
    REVIEWS_DIR,
    SAYS_LP,
    SAYS_LP_PATH,
    agreement,
    blind_sample,
    integrality_packet,
    label_sheet,
    load_sureness,
    read_labels,
    read_says_lp,
    review_order,
    review_packet,
    says_lp_packet,
    sensitive_problems,
)
from opt_agent.stats import wilson

TEST = load_records(GROUND_TRUTH_DIR / "test.json")
SAMPLE = blind_sample(TEST)


def test_the_sample_is_40_of_the_131_sensitive_problems_and_reproducible():
    pool = sensitive_problems(TEST)
    assert len(pool) == 131 and len(SAMPLE) == 40 == len({r.id for r in SAMPLE})
    assert {r.id for r in SAMPLE} <= {r.id for r in pool}
    assert [r.id for r in blind_sample(list(reversed(TEST)))] == [r.id for r in SAMPLE]


def test_the_blind_packet_shows_no_label():
    text = integrality_packet(SAMPLE, 131)
    for r in SAMPLE:
        assert r.document in text
        if r.integrality.note:  # hand labels have none; the rule's say e.g. "counts whole things"
            assert r.integrality.note not in text
    assert "claude" not in text.lower() and "Integrality label" not in text


def test_marks_round_trip(tmp_path):
    sheet = tmp_path / "labels.csv"
    label_sheet(SAMPLE[:2], sheet)
    rows = list(csv.DictReader(sheet.open()))
    assert len(rows) == sum(len(r.model.variables) for r in SAMPLE[:2])
    for row in rows:
        row["label"] = "Integer"  # case doesn't matter
    with sheet.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    labels = read_labels(sheet)
    assert set(labels) == {r.id for r in SAMPLE[:2]}
    assert all(kind == "integer" for marks in labels.values() for kind in marks.values())


def test_a_blank_mark_is_an_error(tmp_path):
    sheet = tmp_path / "labels.csv"
    label_sheet(SAMPLE[:1], sheet)
    with pytest.raises(ValueError, match="neither integer nor continuous"):
        read_labels(sheet)


def test_agreement_with_a_wilson_interval():
    """Mark everything as we did, then flip one problem and make another mixed."""
    owner = {r.id: {v.name: r.integrality.kind for v in r.model.variables} for r in SAMPLE}
    flipped, mixed = SAMPLE[0], SAMPLE[1]
    other = {"integer": "continuous", "continuous": "integer"}
    owner[flipped.id] = {v.name: other[flipped.integrality.kind] for v in flipped.model.variables}
    first, *rest = (v.name for v in mixed.model.variables)
    owner[mixed.id] = {first: "integer", **dict.fromkeys(rest, "continuous")}
    a = agreement(owner, TEST)
    assert (a.agree, a.problems) == (38, 40)
    assert a.interval == wilson(38, 40)
    assert a.mixed == [mixed.id]
    assert {pid for pid, _, _ in a.disagreements} == {flipped.id, mixed.id}


def test_sureness_names_only_real_test_reviews():
    sureness = load_sureness(REVIEWS_DIR / "sureness.json")
    reviewed = {r.id for r in TEST if r.review}
    assert set(sureness) <= reviewed
    assert {level for level, _ in sureness.values()} <= {"low", "medium"}


def test_reviews_come_least_sure_first():
    rows = review_order(TEST, load_sureness(REVIEWS_DIR / "sureness.json"))
    levels = [level for _, level, _ in rows]
    assert len(rows) == 62
    assert levels == sorted(levels, key=packets.SURENESS_ORDER.get)
    assert levels.count("low") == 8 and levels.count("medium") == 7


def test_the_review_packet_warns_about_the_overlap():
    rows = review_order(TEST, load_sureness(REVIEWS_DIR / "sureness.json"))
    text = review_packet(rows, {r.id for r in SAMPLE})
    assert "Do the blind integrality packet first" in text and "5 of these problems" in text
    assert all(r.review.reason in text for r, _, _ in rows)


def test_the_committed_packets_are_up_to_date():
    """Regenerate both packets and compare. The mark columns may be filled in by now, so
    the sheets are compared on everything else."""
    rows = review_order(TEST, load_sureness(REVIEWS_DIR / "sureness.json"))
    assert (REVIEWS_DIR / "PACKET.md").read_text() == review_packet(rows, {r.id for r in SAMPLE})
    assert (BLIND_DIR / "PACKET.md").read_text() == integrality_packet(SAMPLE, 131)
    sheet = [row[:3] for row in csv.reader((BLIND_DIR / "labels.csv").open())]
    expected = [["number", "problem_id", "variable"]] + [
        [str(n), r.id, v.name] for n, r in enumerate(SAMPLE, 1) for v in r.model.variables
    ]
    assert sheet == expected


def test_the_says_lp_problems_are_scorable_sensitive_and_say_lp():
    by_id = {r.id: r for r in TEST}
    sensitive = {r.id for r in sensitive_problems(TEST)}
    for problem_id in SAYS_LP:
        assert problem_id in sensitive
        assert "LP" in by_id[problem_id].document or "linear program" in by_id[problem_id].document


def test_the_says_lp_problems_are_not_in_the_blind_statistic():
    assert not set(SAYS_LP) & {r.id for r in SAMPLE}
    owner = {r.id: {v.name: r.integrality.kind for v in r.model.variables} for r in SAMPLE}
    lp = next(r for r in TEST if r.id == SAYS_LP[0])
    owner[lp.id] = {v.name: "continuous" for v in lp.model.variables}  # would disagree
    a = agreement(owner, TEST)
    assert (a.agree, a.problems) == (40, 40)  # skipped, not counted as a disagreement


def test_the_says_lp_file_shows_no_label_and_reads_back(tmp_path):
    text = says_lp_packet(TEST)
    cells = [line.split("|")[2].strip() for line in text.splitlines() if line.startswith("| `")]
    assert len(cells) == 8 and set(cells) == {"?"}  # every label blank, none of ours shown
    filled = tmp_path / "says_lp.md"
    filled.write_text(text.replace("| ? |", "| integer |"))
    labels = read_says_lp(filled)
    assert list(labels) == SAYS_LP
    assert all(kind == "integer" for marks in labels.values() for kind in marks.values())


def test_an_unlabeled_says_lp_variable_is_an_error():
    with pytest.raises(ValueError, match="neither integer nor continuous"):
        read_says_lp(SAYS_LP_PATH)  # the committed file is still blank


def test_the_committed_says_lp_file_is_up_to_date():
    """Compared with the blanks filled back in, so the test survives the owner's labels."""
    committed = re.sub(
        r"\| (integer|continuous) \|$", "| ? |", SAYS_LP_PATH.read_text(), flags=re.M
    )
    assert committed == says_lp_packet(TEST)


# ---- 4. the judges' integrality labels (Amendment 2) -----------------------------------


def test_the_judges_get_the_blind_sample_then_the_says_lp_problems():
    problems = packets.judged_problems(TEST)
    assert [r.id for _, r in problems] == [r.id for r in SAMPLE] + SAYS_LP
    assert {which for which, _ in problems} == {"blind sample", "says LP"}


def test_the_judge_prompt_shows_no_label_and_names_no_one():
    problems = packets.judged_problems(TEST)
    text = packets.judge_prompt(problems)
    assert text.count("\n## ") == 44 and "`number,problem_id,label,note`" in text
    for _, r in problems:
        assert r.document in text
        if r.integrality.note:
            assert r.integrality.note not in text
    assert "claude" not in text.lower() and "says LP" not in text and "blind" not in text


def test_the_committed_judge_packet_is_up_to_date():
    problems = packets.judged_problems(TEST)
    prompt = (packets.JUDGE_DIR / "LLM_PROMPT.md").read_text()
    assert prompt == packets.judge_prompt(problems)
    for name in packets.JUDGE_SHEETS.values():  # the labels may be filled in by now
        sheet = [row[:3] for row in csv.reader((packets.JUDGE_DIR / name).open())]
        assert sheet == [["number", "problem_id", "set"]] + [
            [str(n), r.id, which] for n, (which, r) in enumerate(problems, 1)]  # fmt: skip


def test_a_judges_labels_merge_and_read_back(tmp_path):
    problems = packets.judged_problems(TEST)[:2]
    sheet = tmp_path / "judge.csv"
    packets.judge_sheet(problems, sheet)
    (_, first), (_, second) = problems
    reply = tmp_path / "reply.csv"
    reply.write_text(f'number,problem_id,label,note\n1,{first.id},either,"both"\n'
                     f"2,{second.id},integer,\n")  # fmt: skip
    assert packets.merge_reply(sheet, reply, ["label", "note"], "Some model") == 2
    assert packets.read_judge_labels(sheet) == {first.id: "either", second.id: "integer"}
    assert packets.graders(sheet) == ["Some model"]
    packets.judge_sheet(problems, sheet)  # regenerating keeps them
    assert packets.read_judge_labels(sheet) == {first.id: "either", second.id: "integer"}


def test_a_judges_reply_with_a_wrong_problem_id_or_label_is_refused(tmp_path):
    problems = packets.judged_problems(TEST)[:2]
    sheet = tmp_path / "judge.csv"
    packets.judge_sheet(problems, sheet)
    (_, first), (_, second) = problems
    reply = tmp_path / "reply.csv"
    reply.write_text(f"number,problem_id,label,note\n1,{second.id},integer,\n"
                     f"2,{first.id},integer,\n")  # fmt: skip
    with pytest.raises(ValueError, match="problem_id"):
        packets.merge_reply(sheet, reply, ["label", "note"], "judge")
    reply.write_text(f"number,problem_id,label,note\n1,{first.id},mixed,\n"
                     f"2,{second.id},integer,\n")  # fmt: skip
    packets.merge_reply(sheet, reply, ["label", "note"], "judge")
    with pytest.raises(ValueError, match="'mixed' is none of"):
        packets.read_judge_labels(sheet)


def test_the_judges_combined_label_is_theirs_where_they_agree_else_either():
    judge = {"a": "integer", "b": "continuous", "c": "either", "d": "integer"}
    second = {"a": "integer", "b": "integer", "c": "either", "d": "either"}
    assert packets.combined_labels(judge, second) == {
        "a": "integer", "b": "either", "c": "either", "d": "either"}  # fmt: skip
