"""The blinded taxonomy prompt (scripts/blind_taxonomy.py, Amendment 3): it hides what it
should, it's reproducible, and a reply merges back onto the right problems. No API calls."""

import csv
import importlib.util
from pathlib import Path

import pytest

from opt_agent import taxonomy
from opt_agent.run_results import load

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "test"
SCRIPT = ROOT / "scripts" / "blind_taxonomy.py"
spec = importlib.util.spec_from_file_location("blind_taxonomy", SCRIPT)
blind = importlib.util.module_from_spec(spec)
spec.loader.exec_module(blind)

pytestmark = pytest.mark.skipif(not RUN.exists(), reason="needs the committed test run")


@pytest.fixture
def packet(tmp_path, monkeypatch):
    """The prompt and mapping, written to a temporary review folder."""
    monkeypatch.setattr(taxonomy, "TAXONOMY_DIR", tmp_path)
    folder, n = blind.write(RUN)
    rows = list(csv.DictReader((folder / blind.MAPPING).open()))
    return folder, (folder / blind.PROMPT).read_text(), rows


def test_the_prompt_hides_ids_conditions_keys_and_reviews(packet):
    _, text, rows = packet
    run = load(RUN)
    for row in rows:
        assert row["problem_id"] not in text
        assert row["key"] not in text
        review = run.by_id[row["problem_id"]].review
        if review:
            assert review.reason not in text
    for condition in ("baseline", "single-shot", "self-correction"):
        assert condition not in text
    assert [line for line in text.splitlines() if line.startswith("## ")] == [
        f"## Row {n}" for n in range(1, len(rows) + 1)
    ]


def test_every_failure_has_one_row_and_the_order_is_reproducible(packet):
    _, text, rows = packet
    failures = taxonomy.failures(load(RUN))
    assert sorted(r["key"] for r in rows) == sorted(f.key for f in failures)
    assert text == blind.prompt(load(RUN), blind.shuffled(load(RUN)))


def test_a_reply_merges_onto_the_right_problems(packet, tmp_path):
    folder, _, rows = packet
    taxonomy.label_sheet(taxonomy.failures(load(RUN)), folder / "labels.csv")
    reply = tmp_path / "reply.csv"
    categories = list(taxonomy.CATEGORIES)
    wanted = {r["key"]: categories[int(r["row"]) % len(categories)] for r in rows}
    with reply.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["row", "category", "note"])
        for r in reversed(rows):  # any order
            writer.writerow([r["row"], wanted[r["key"]], "a note"])
    assert blind.merge(RUN, "second", reply, "a judge") == len(rows)
    merged = {r["key"]: r for r in csv.DictReader((folder / "second_judge.csv").open())}
    assert {k: r["category"] for k, r in merged.items()} == wanted
    assert {r["grader"] for r in merged.values()} == {"a judge"}


def test_the_prompt_asks_for_the_header_on_a_line_of_its_own(packet):
    _, text, _ = packet
    assert "\nrow,category,note\n" in text


def test_a_reply_without_the_header_skipping_a_row_or_inventing_a_category_is_refused(
    packet, tmp_path
):
    folder, _, rows = packet
    reply = tmp_path / "reply.csv"
    reply.write_text("".join(f"{r['row']},other,x\n" for r in rows))
    with pytest.raises(ValueError, match="first line must be exactly"):
        blind.translate(reply, folder / blind.MAPPING)
    reply.write_text("row,category,note\n" + "".join(f"{r['row']},other,x\n" for r in rows[1:]))
    with pytest.raises(ValueError, match="not each of"):
        blind.translate(reply, folder / blind.MAPPING)
    reply.write_text("row,category,note\n" + "".join(f"{r['row']},typo,x\n" for r in rows))
    with pytest.raises(ValueError, match="isn't a category"):
        blind.translate(reply, folder / blind.MAPPING)
