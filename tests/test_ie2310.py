"""The IE 2310 kit (docs/ie2310/, scripts/ie2310.py): its numbers table is current with the
results files, and its figures are there. (Every number in its summary is checked in
test_readme_numbers.py.) No API calls; no matplotlib needed."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ie2310", ROOT / "scripts" / "ie2310.py")
ie2310 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ie2310)


def test_the_numbers_table_is_current():
    rows = ie2310.rows()
    assert (ie2310.OUT / "numbers.md").read_text() == ie2310.table_md(rows), (
        "docs/ie2310/numbers.md is stale: python scripts/ie2310.py"
    )
    assert (ie2310.OUT / "numbers.csv").read_text() == ie2310.table_csv(rows)


def test_every_row_names_its_source():
    for row in ie2310.rows():
        assert row["value"] and row["source"].startswith(("eval.json:", "followup.json:",
                                                         "derived:"))  # fmt: skip


def test_the_figures_are_there():
    for name in ("accuracy", "failures", "cost"):
        path = ie2310.OUT / "figures" / f"{name}.png"
        assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} isn't a PNG"
