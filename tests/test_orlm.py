import pytest

from opt_agent.orlm import load_answers, normalize, verdict


@pytest.mark.parametrize(
    ("answer", "lp", "ip", "expected"),
    [
        ("3000.0", 3000, 3000, "matches both"),
        ("1160.0", 1140, 1160, "matches IP only"),
        ("1140", 1140, 1160, "matches LP only"),
        ("1140.05", 1140, 1160, "matches LP only"),  # within the 1e-4 relative tolerance
        ("648.0", 1200, 1200, "matches neither"),
        ("No Best Solution", None, None, "both find no optimum"),
        ("-99999", None, None, "both find no optimum"),
        ("-99999.0", 7.5, None, "only we find an optimum"),
        ("12.0", None, None, "only ORLM finds an optimum"),
    ],
)
def test_verdict(answer, lp, ip, expected):
    assert verdict(answer, lp, ip) == expected


def test_questions_are_matched_ignoring_case_and_spacing(tmp_path):
    path = tmp_path / "answers.json"
    path.write_text('{"en_question": "Two  Trucks\\nand a van", "en_answer": "5"}\n')
    assert load_answers(path) == {normalize("two trucks and a VAN"): "5"}
