"""docs/analysis/dispute_spotcheck.md (scripts/dispute_spotcheck.py): the seeded draw of the
follow-up's disputed problems, and the committed doc as the script writes it."""

import importlib.util
from pathlib import Path

import pytest

from opt_agent import followup

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "dispute_spotcheck", ROOT / "scripts" / "dispute_spotcheck.py"
)
spotcheck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(spotcheck)


def test_the_doc_lists_the_seeds_draw_and_every_disputed_problem_has_a_reason():
    pool = spotcheck.disputed()
    drawn = spotcheck.draw(pool)
    assert len(set(drawn)) == spotcheck.SIZE and set(drawn) <= set(pool)
    assert set(spotcheck.REASONS) == set(pool)  # one for each, not only the drawn ones
    rows = [line for line in spotcheck.DOC.read_text().splitlines() if line.startswith("| ")]
    assert [row.split("`")[1] for row in rows[1:]] == drawn  # after the header, in draw order


@pytest.mark.skipif(
    not (followup.COMPLEXLP.exists() and followup.INDUSTRYOR.exists()),
    reason="needs LLM4OR's data for the keys (python scripts/fetch_llm4or.py)",
)
def test_the_committed_doc_is_the_scripts_output():
    """Everything but the verdicts a person writes in, which the script keeps."""
    doc = spotcheck.DOC.read_text()
    assert spotcheck.render(spotcheck.verdicts(doc)) == doc


def test_writing_the_doc_again_keeps_a_persons_verdicts():
    row = "| 3 | `industryor:17` | 43700 | 43200 (9 answers, 4 models) | a reason | key wrong |"
    assert spotcheck.verdicts(row) == {"industryor:17": "key wrong"}
    assert spotcheck.verdicts(row.replace("key wrong |", "|")) == {"industryor:17": ""}
