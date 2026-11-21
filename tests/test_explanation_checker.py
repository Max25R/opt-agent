"""The explanation checker's evaluation on dev (docs/analysis/explanation_checker.md): the
committed record is what the committed labels and run give, every label is filled in, the
doc shows that record, and every explanation replays from the run's committed cache with no
client. No API calls."""

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("checker_eval", ROOT / "scripts" /
                                              "explanation_checker.py")  # fmt: skip
checker_eval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker_eval)


def test_the_record_is_what_the_labels_and_the_run_give():
    """compute() also holds the recomputed flags equal to the run's own."""
    assert checker_eval.compute() == json.loads(checker_eval.OUT.read_text())


def test_every_number_and_explanation_is_labeled():
    labels = checker_eval.read("labels-*.csv")
    claims = checker_eval.read("claims-*.csv")
    assert len(labels) == json.loads(checker_eval.OUT.read_text())["numbers"]
    assert {r["label"] for r in labels} <= checker_eval.LABELS
    assert {c["false_claim"] for c in claims} <= {"yes", "no"}
    assert len(claims) == len(checker_eval.explained())
    for path in checker_eval.SHEETS.glob("batch-*.md"):  # the sheets never showed the flags
        assert "unsupported" not in path.read_text() and "flagged" not in path.read_text()


def test_the_doc_shows_the_record():
    doc = checker_eval.DOC.read_text()
    section = doc[doc.index(checker_eval.BEGIN) + len(checker_eval.BEGIN) : doc.index(
        checker_eval.END)]  # fmt: skip
    assert section.strip() == checker_eval.render(json.loads(checker_eval.OUT.read_text()))


def test_every_explanation_replays_from_the_committed_cache():
    from opt_agent import agent
    from opt_agent.api import Cache, ReplayOnlyClient
    from opt_agent.runs import Run

    texts, cache = checker_eval.texts(), Cache(checker_eval.RUN / "cache")
    for row in map(json.loads, checker_eval.ROWS.read_text().splitlines()):
        session = Run(cache=cache)
        # the run predates ADR-0009, so its requests carry no limits, and a replay sends those
        result = agent.run(texts[row["problem"]], ReplayOnlyClient(), "claude-haiku-5-5",
                           with_explanation=True, max_attempts=1, session=session,
                           explain_limits=False)  # fmt: skip
        assert result.verified == row["verified"], row["problem"]
        assert (result.explanation.text if result.explanation else None) == row["explanation"]


def test_label_files_keep_their_rows():
    """The sheet step writes the rows; labeling fills two columns and nothing else."""
    for path in [*checker_eval.SHEETS.glob("labels-*.csv"),
                 *checker_eval.AFTER_SHEETS.glob("labels-*.csv")]:  # fmt: skip
        with path.open(newline="") as f:
            assert next(csv.reader(f)) == ["problem", "index", "token", "label", "note"]


def test_the_after_sheets_are_the_scripts_own_and_show_what_the_first_ones_did(tmp_path):
    """review/explain_dev_limits/ (`sheet --after`): ADR-0009's regenerated explanations, on
    the same sheets as the first run's, so the same checker can label them. The facts line
    leaves out the new limits, as the first sheets had none; the 15 LP entries are the first
    sheets' own, word for word; and each row of the label files is still the script's."""
    checker_eval.write_sheets(checker_eval.AFTER_ROWS, tmp_path)
    committed = checker_eval.AFTER_SHEETS
    for k in range(1, checker_eval.BATCHES + 1):
        sheet = (committed / f"batch-{k}.md").read_text()
        assert sheet == (tmp_path / f"batch-{k}.md").read_text()
        assert "dropped_improves" not in sheet and "loosened_improves" not in sheet
        for name, keys in ((f"labels-{k}.csv", ("problem", "index", "token")),
                           (f"claims-{k}.csv", ("problem",))):  # fmt: skip
            with (committed / name).open(newline="") as a, (tmp_path / name).open(newline="") as b:
                rows = [[r[key] for key in keys] for r in csv.DictReader(a)]
                assert rows == [[r[key] for key in keys] for r in csv.DictReader(b)]

    def entries(directory) -> dict[str, str]:
        found = {}
        for path in sorted(directory.glob("batch-*.md")):
            for part in path.read_text().split("\n## ")[1:]:
                found[part.split("\n", 1)[0]] = part
        return found

    before, after = entries(checker_eval.SHEETS), entries(committed)
    assert before.keys() == after.keys() and len(after) == 88
    assert sum(before[p] == after[p] for p in after) == 15  # the LPs: their requests didn't change
