"""The external cross-check (pre-registration, Amendment 2): matching by text, and each
verdict, on dev problems with hand-made benchmark answers. Needs no download and never
calls the API."""

import pytest

from opt_agent import external_check, orlm
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
