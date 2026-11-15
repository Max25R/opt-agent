"""Fetch LLM4OR's cleaned benchmarks into data/external/llm4or-clean/ (git-ignored), exactly
as docs/EXTERNAL_DATA.md records them, so scripts/reproduce.py can rebuild the follow-up and
Amendment 5 (CI runs this first). The data states no license, so it's fetched, never
committed.

- Only `static/clean_benchmarks/` at the pinned commit, through a sparse, blob-less clone in
  a temporary directory outside the repository.
- Only what the project uses: IndustryOR.jsonl, Mamo/Mamo_complex_lp_clean.jsonl, and each
  NL4Opt problem's description.txt and sample.json (never code_example.py: foreign code is
  never run here; never .DS_Store).
- Every file checked before it's kept: the two JSONL files against the hashes the follow-up
  froze (followup_freeze.DATA_SHA256), NL4Opt against the hash of its sorted file listing,
  as scripts/amendment5.py checks it. Anything else is deleted and the script fails.
- A copy that's already here and intact is kept as it is.

Run:  python scripts/fetch_llm4or.py [--target DIR]
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from opt_agent.followup_freeze import DATA_SHA256

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "data" / "external" / "llm4or-clean"
REPOSITORY = "https://github.com/LLM4OR/LLM4OR.git"
COMMIT = "75962df5ddf531906fda76f8708c658114e63c0e"  # docs/EXTERNAL_DATA.md
FOLDER = "static/clean_benchmarks"
SOURCES = {"IndustryOR.jsonl": "IndustryOR.jsonl",
           "Mamo_complex_lp_clean.jsonl": "Mamo/Mamo_complex_lp_clean.jsonl"}  # fmt: skip
NL4OPT_SHA256 = "ce544464946e83514bd73b2e82e9f3cb50d7d64076fc1c81e9e176d09e5e88c8"  # amendment5
NL4OPT_FILES = ("description.txt", "sample.json")


def nl4opt_sha256(target: Path) -> str:
    """The hash scripts/amendment5.py checks: of `<sha256>  NL4Opt/<problem>/<file>` lines,
    sorted by path, one per file."""
    files = sorted(p for p in (target / "NL4Opt").rglob("*") if p.is_file())
    listing = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  "
                      f"{p.relative_to(target).as_posix()}\n" for p in files)  # fmt: skip
    return hashlib.sha256(listing.encode()).hexdigest()


def problems(target: Path) -> list[str]:
    """What isn't the recorded copy; empty when everything is."""
    found = []
    for name in SOURCES:
        path = target / name
        if not path.exists():
            found.append(f"{name} is missing")
        elif hashlib.sha256(path.read_bytes()).hexdigest() != DATA_SHA256[name]:
            found.append(f"{name} isn't the recorded file")
    if not (target / "NL4Opt").is_dir():
        found.append("NL4Opt/ is missing")
    elif nl4opt_sha256(target) != NL4OPT_SHA256:
        found.append("NL4Opt/ isn't the recorded copy")
    return found


def git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, capture_output=True, text=True)


def fetch(target: Path = TARGET) -> None:
    if not problems(target):
        print(f"already here and intact: {target}")
        return
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "llm4or"
        git("init", "-q", str(clone))
        git("-C", str(clone), "remote", "add", "origin", REPOSITORY)
        git("-C", str(clone), "sparse-checkout", "set", "--no-cone", FOLDER)
        git("-C", str(clone), "fetch", "-q", "--depth", "1", "--filter=blob:none", "origin",
            COMMIT)  # fmt: skip
        git("-C", str(clone), "checkout", "-q", "FETCH_HEAD")
        source = clone / FOLDER
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        for name, there in SOURCES.items():
            shutil.copy2(source / there, target / name)
        for problem in sorted((source / "NL4Opt").iterdir()):
            if problem.is_dir():
                (target / "NL4Opt" / problem.name).mkdir(parents=True)
                for name in NL4OPT_FILES:
                    shutil.copy2(problem / name, target / "NL4Opt" / problem.name / name)
    if found := problems(target):
        shutil.rmtree(target)
        sys.exit(f"LLM4OR's data doesn't match docs/EXTERNAL_DATA.md, so it was deleted: {found}")
    print(f"fetched and checked: {target}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Fetch LLM4OR's cleaned benchmarks.")
    parser.add_argument("--target", type=Path, default=TARGET)
    fetch(parser.parse_args(argv).target)


if __name__ == "__main__":
    main()
