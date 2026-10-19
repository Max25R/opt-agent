import csv

import pytest

from opt_agent import packets
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records
from opt_agent.packets import (
    BLIND_DIR,
    REVIEWS_DIR,
    agreement,
    blind_sample,
    integrality_packet,
    label_sheet,
    load_sureness,
    read_labels,
    review_order,
    review_packet,
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
