"""docs/DESIGN.md's code tour ("Read the code in 10 minutes") points at files that exist, and
each file it numbers opens with a docstring that says what it does and why (more than a
one-line label), so a rename or an emptied docstring can't leave the tour stale."""

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "docs" / "DESIGN.md"
HEADING = "## Read the code in 10 minutes"  # the README links to its anchor


def tour() -> str:
    text = DESIGN.read_text()
    start = text.index(f"\n{HEADING}\n")
    return text[start : text.index("\n## ", start + 1)]


def test_the_tour_numbers_six_files_each_with_a_real_docstring():
    numbered = re.findall(r"^\d\. \[`([\w.]+)`\]\(\.\./([^)]+)\)", tour(), re.MULTILINE)
    assert len(numbered) == 6
    for name, target in numbered:
        path = ROOT / target
        assert path.name == name and path.is_file(), target
        docstring = ast.get_docstring(ast.parse(path.read_text())) or ""
        assert len(docstring.splitlines()) >= 3, f"{target}: say what it does and why"


def test_every_file_the_tour_links_exists():
    targets = re.findall(r"\]\(\.\./([^)#]+)\)", tour())
    assert len(targets) >= 9
    assert [t for t in targets if not (ROOT / t).is_file()] == []
