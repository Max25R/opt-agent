"""The follow-up freeze (docs/FOLLOWUP_PREREGISTRATION.md, section 3): the follow-up test
split is read, and run, only on exactly the inputs the owner approved.

It works like M6's (freeze.py), and reuses its pieces, with the follow-up's list:
- every source file in src/opt_agent/ and requirements.lock (installed packages must match
  it). The analysis that scores the run, followup_report.py, is also written into the
  approval by name with its own SHA-256, as section 3 asks;
- the pre-registration itself, the encoding check's judge prompt (docs/followup/
  judge_prompt.md), data/followup/split.json, and both LLM4OR data files
  (git-ignored, so they're checked by hash: section 2's);
- by name, what Claude sees and how it's sampled: the model, the pinned settings, every
  prompt and schema, the checklist feedback's wording, the seeds and the sample indexes;
- section 2's id-list hashes, recomputed from split.json.

`python -m opt_agent.followup_freeze` lists what's left and whether the inputs match.
`python -m opt_agent.followup_freeze approve` is THE OWNER'S STEP, never Claude's: it refuses
until that list is empty, the tree is committed and the packages are the locked ones, then
writes docs/followup/FREEZE.json. followup.load_sealed() calls check() before it reads a test
problem, so nothing reads the sealed split until the approval exists and still matches.
"""

import argparse
import hashlib
import sys
from datetime import date
from pathlib import Path

from opt_agent import (
    api,
    baseline,
    checklist,
    explain,
    feedback,
    followup,
    followup_report,
    formulate,
)
from opt_agent.freeze import (
    LOCK_PATH,
    SOURCE_DIR,
    Approval,
    FreezeError,
    _canonical,
    _relative,
    _sha256,
    differences,
    digest,
    drifted_packages,
)
from opt_agent.runs import REPO_ROOT, git

FREEZE_PATH = REPO_ROOT / "docs" / "followup" / "FREEZE.json"
PREREGISTRATION_PATH = REPO_ROOT / "docs" / "FOLLOWUP_PREREGISTRATION.md"
ANALYSIS_PATH = SOURCE_DIR / "followup_report.py"
JUDGE_PROMPT_PATH = REPO_ROOT / "docs" / "followup" / "judge_prompt.md"  # 5b's encoding check
SAMPLES = (0, 1, 2)  # section 3

# Section 2's hashes, as the draft writes them. unfinished() recomputes each from the files.
SPLIT_SHA256 = "c37ecc0e93f16d0e496e5c2b95d8d8f4c477d92220205e63d73e5cbe4e0a3203"
DATA_SHA256 = {
    "Mamo_complex_lp_clean.jsonl":
        "28e10dff1146ff635673293b5730abb3d7efa2f7bbe91de60fe67b729dfe7a0d",
    "IndustryOR.jsonl": "d7c2c05377ade5bc6a401ebf3075f0e00fa91068439761e5b46fa3045ffc19b5",
}  # fmt: skip
IDS_SHA256 = "d17b55ffbdd078cfb3c44825e7f7ae08c4e68c42ce3de089f09a43afcdbcbfec"  # all 128
UNEXPOSED_SHA256 = "5ba1e23a8a4964fa5a7fc649260df00fe30ca3eae8d3c7809523dabf26698ed2"  # 121


class FollowupApproval(Approval):
    analysis_sha256: str  # followup_report.py, by name (section 3); also in the fingerprint


# ---- the fingerprint --------------------------------------------------------------------


def data_files() -> list[Path]:
    return [followup.DATA / name for name in DATA_SHA256]


def fingerprint() -> dict[str, str]:
    """Name -> SHA-256: repo-relative paths for files, dotted names for values. A missing data
    file is hashed as "missing", so the difference names it."""
    files = [PREREGISTRATION_PATH, followup.SPLIT_PATH, LOCK_PATH, JUDGE_PROMPT_PATH,
             *sorted(SOURCE_DIR.rglob("*.py"))]  # fmt: skip
    prints = {_relative(p): _sha256(p.read_bytes()) for p in files}
    prints |= {_relative(p): _sha256(p.read_bytes()) if p.exists() else "missing"
               for p in data_files()}  # fmt: skip
    prints |= {name: _sha256(_canonical(value)) for name, value in frozen_values().items()}
    return dict(sorted(prints.items()))


def frozen_values() -> dict[str, object]:
    """What section 3 lists by name. Each is also inside a source file's hash; naming them
    says which one changed."""
    return {
        "model": formulate.DEFAULT_MODEL,
        "api.MAX_TOKENS": api.MAX_TOKENS,
        "api.THINKING": api.THINKING,
        "api.EFFORT": api.EFFORT,
        "temperature": "not sent (the API default, 1)",
        "formulate.SYSTEM_PROMPT": formulate.SYSTEM_PROMPT,
        "formulate.LP_SCHEMA": formulate.LP_SCHEMA,
        "baseline.SYSTEM_PROMPT": baseline.SYSTEM_PROMPT,
        "baseline.ANSWER_SCHEMA": baseline.ANSWER_SCHEMA,
        "checklist.SYSTEM_PROMPT": checklist.SYSTEM_PROMPT,
        "checklist.CHECKLIST_SCHEMA": checklist.CHECKLIST_SCHEMA,
        "explain.SYSTEM_PROMPT": explain.SYSTEM_PROMPT,
        "feedback.CHECKLIST_INTRO": feedback.CHECKLIST_INTRO,
        "feedback.CHECKLIST_OUTRO": feedback.CHECKLIST_OUTRO,
        "seed.split": followup.read_split()["seed"],
        "seed.order": followup.ORDER_SEED,
        "seed.bootstrap": followup_report.BOOTSTRAP_SEED,
        "samples": list(SAMPLES),
        "ids.all": id_list_sha256(),
        "ids.unexposed": id_list_sha256(unexposed_only=True),
    }


def sealed_labels(split: dict | None = None) -> list[str]:
    """The 128 follow-up test problems as section 2 writes them, sorted by benchmark then
    number. Ids only: nothing here reads a problem."""
    split = split or followup.read_split()
    return [f"{benchmark}:{pid}" for benchmark in ("complexlp", "industryor")
            for pid in sorted(int(i) for i in split[benchmark]["test"])]  # fmt: skip


def id_list_sha256(unexposed_only: bool = False) -> str:
    """Section 2's id-list hash: one label per line, with a final newline."""
    labels = sealed_labels()
    if unexposed_only:
        exposed = followup_report.exposed_labels()
        labels = [label for label in labels if label not in exposed]
    return hashlib.sha256("".join(f"{label}\n" for label in labels).encode()).hexdigest()


# ---- before the approval ----------------------------------------------------------------


def unfinished() -> list[str]:
    """What's left before the owner may approve, checked from the files; empty when nothing
    is. Section 2's hashes must hold, since the test run reads exactly those files."""
    todo = []
    text = PREREGISTRATION_PATH.read_text()
    if "**Status: DRAFT" in text:
        todo.append(f"{_relative(PREREGISTRATION_PATH)} is still a draft: the owner approves "
                    "it first")  # fmt: skip
    if _sha256(followup.SPLIT_PATH.read_bytes()) != SPLIT_SHA256:
        todo.append("data/followup/split.json isn't the split section 2 names")
    for path, sha in zip(data_files(), DATA_SHA256.values(), strict=True):
        if not path.exists():
            todo.append(f"{_relative(path)} is missing (python -m opt_agent.data; "
                        "docs/EXTERNAL_DATA.md)")  # fmt: skip
        elif _sha256(path.read_bytes()) != sha:
            todo.append(f"{_relative(path)} isn't the file section 2 names")
    if id_list_sha256() != IDS_SHA256:
        todo.append("the 128 test ids in split.json don't give section 2's id-list hash")
    if id_list_sha256(unexposed_only=True) != UNEXPOSED_SHA256:
        todo.append("the 121 unexposed ids don't give section 2's id-list hash")
    named = [SPLIT_SHA256, IDS_SHA256, UNEXPOSED_SHA256, *DATA_SHA256.values()]
    if missing := [sha[:12] for sha in named if sha not in text]:
        todo.append(f"the pre-registration doesn't state these section 2 hashes: {missing}")
    return todo


def approve(today: str | None = None) -> FollowupApproval:
    """THE OWNER'S STEP. Writes docs/followup/FREEZE.json with the current fingerprint."""
    todo = unfinished()
    if git("status", "--porcelain"):
        todo.append("the working tree has uncommitted changes: commit first, so the approved "
                    "inputs are the ones in git")  # fmt: skip
    if drifted := drifted_packages():
        todo.append(f"installed packages differ from requirements.lock: {sorted(drifted)}")
    if todo:
        raise FreezeError("not ready to freeze the follow-up:\n  " + "\n  ".join(todo))
    prints = fingerprint()
    approval = FollowupApproval(
        approved_on=today or date.today().isoformat(), commit=git("rev-parse", "HEAD"),
        fingerprint=prints, analysis_sha256=prints[_relative(ANALYSIS_PATH)],
    )  # fmt: skip
    FREEZE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FREEZE_PATH.write_text(approval.model_dump_json(indent=1) + "\n")
    return approval


# ---- checking ---------------------------------------------------------------------------


def approved() -> FollowupApproval | None:
    if not FREEZE_PATH.exists():
        return None
    return FollowupApproval.model_validate_json(FREEZE_PATH.read_text())


def check() -> str:
    """The approved fingerprint's digest, if the current inputs are exactly the approved ones
    and the installed packages are the locked ones. Otherwise FreezeError, naming every
    difference (names only, never contents)."""
    approval = approved()
    if approval is None:
        raise FreezeError(
            "the follow-up isn't frozen yet: the owner approves with `python -m "
            "opt_agent.followup_freeze approve`, after the steps it lists"
        )
    problems = differences(approval.fingerprint, fingerprint())
    if approval.fingerprint.get(_relative(ANALYSIS_PATH)) != approval.analysis_sha256:
        problems.append(f"{FREEZE_PATH.name}: analysis_sha256 isn't the fingerprint's")
    problems += [f"{name}: installed {installed}, locked {locked}"
                 for name, (locked, installed) in drifted_packages().items()]  # fmt: skip
    if problems:
        raise FreezeError(
            f"the inputs differ from the follow-up's approval of {approval.approved_on}:\n  "
            + "\n  ".join(problems)
        )
    return digest(approval.fingerprint)


# ---- command line -----------------------------------------------------------------------


def status() -> str:
    todo = unfinished()
    lines = ["Left to do before the follow-up freeze:" if todo
             else "Nothing left to do before the follow-up freeze."]  # fmt: skip
    lines += [f"- {item}" for item in todo]
    approval = approved()
    if approval is None:
        lines.append("Not approved yet (no docs/followup/FREEZE.json): the test split stays "
                     "sealed.")  # fmt: skip
        return "\n".join(lines)
    try:
        check()
    except FreezeError as error:
        lines.append(f"FROZEN INPUTS CHANGED, so the test split stays sealed: {error}")
    else:
        lines.append(f"Frozen on {approval.approved_on}, and the inputs match: the test split "
                     "may be read and run.")  # fmt: skip
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The follow-up pre-registration's freeze.")
    parser.add_argument("action", nargs="?", choices=["status", "approve"], default="status")
    args = parser.parse_args(argv)
    if args.action == "status":
        print(status())
        return
    try:
        approval = approve()
    except FreezeError as error:
        sys.exit(str(error))
    print(
        f"Wrote {_relative(FREEZE_PATH)} ({len(approval.fingerprint)} hashes, commit "
        f"{approval.commit}; analysis {approval.analysis_sha256[:12]}). Commit and tag it."
    )


if __name__ == "__main__":
    main()
