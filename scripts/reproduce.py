"""Rebuild every reported number from the committed runs, with each study's frozen code and
no API key, and compare the results with the committed files byte for byte.

- **The follow-up** (tag followup-freeze): the frozen analysis, followup_report.py, scores
  runs/followup-test, and scripts/followup_results.py (written after the freeze, against the
  same package) turns that report into results/followup.json and docs/followup/RESULTS.md.
  Needs the LLM4OR data, which holds the keys (docs/EXTERNAL_DATA.md).

Each study runs in its tag's own tree (opt_agent.frozen), so nothing HEAD changes can move a
number, and nothing here writes into this checkout. Exits 1 on any difference (printing the
start of a diff), or if something can't be rebuilt; 0 when everything matches.

Run:  python scripts/reproduce.py
"""

import argparse
import difflib
import sys
import tempfile
from pathlib import Path

from opt_agent import followup_freeze
from opt_agent.frozen import FrozenError, Tree

ROOT = Path(__file__).resolve().parents[1]
FOLLOWUP_RUN = "runs/followup-test"
RUN_FILES = ("manifest.json", "results.jsonl", "attempts.jsonl", "spend.jsonl")  # no cache
LLM4OR = "data/external/llm4or-clean"
FOLLOWUP_OUTPUTS = (f"{FOLLOWUP_RUN}/followup_report.json", "results/followup.json",
                    "docs/followup/RESULTS.md")  # fmt: skip
DIFF_LINES = 40  # of each difference, printed


def rebuild_followup(workdir: Path) -> dict[str, bytes]:
    """The follow-up's three output files, rebuilt in followup-freeze's tree, by path."""
    if not all(p.exists() for p in followup_freeze.data_files()):
        raise FrozenError(f"the follow-up needs the LLM4OR data in {LLM4OR} "
                          "(docs/EXTERNAL_DATA.md): it holds the keys")  # fmt: skip
    tree = Tree.extract(followup_freeze.FREEZE_TAG, workdir / "followup")
    tree.copy(*(f"{FOLLOWUP_RUN}/{name}" for name in RUN_FILES), LLM4OR,
              "scripts/followup_results.py")  # fmt: skip
    tree.python("-m", "opt_agent.followup_report", FOLLOWUP_RUN)
    tree.python("scripts/followup_results.py")
    return {rel: tree.read(rel) for rel in FOLLOWUP_OUTPUTS}


def differences(rebuilt: dict[str, bytes], root: Path = ROOT) -> list[str]:
    """Each rebuilt file that isn't byte for byte the committed one, with the start of a diff."""
    found = []
    for rel, content in rebuilt.items():
        committed = (root / rel).read_bytes() if (root / rel).exists() else None
        if content == committed:
            continue
        diff = difflib.unified_diff(
            (committed or b"").decode().splitlines(), content.decode().splitlines(),
            f"{rel} (committed)", f"{rel} (rebuilt)", lineterm="",
        )  # fmt: skip
        found.append("\n".join([f"DIFFERS: {rel}", *list(diff)[:DIFF_LINES]]))
    return found


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Rebuild the reported numbers; no API key.")
    parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="reproduce-") as workdir:
        try:
            rebuilt = rebuild_followup(Path(workdir))
        except FrozenError as error:
            sys.exit(f"CAN'T REBUILD: {error}")
    found = differences(rebuilt)
    for rel in rebuilt:
        print(f"{'DIFFERS' if any(f.startswith(f'DIFFERS: {rel}') for f in found) else 'same'}"
              f"  {rel}")  # fmt: skip
    if found:
        print("\n\n".join(found))
        sys.exit(1)
    print(f"All {len(rebuilt)} files rebuild byte for byte.")


if __name__ == "__main__":
    main()
