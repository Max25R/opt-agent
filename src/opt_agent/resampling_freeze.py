"""The resampling study's freeze (docs/RESAMPLING_PREREGISTRATION.md, section 6): its
problems are read, and its run made, only on exactly the inputs approved.

It works like the follow-up's (followup_freeze.py) and reuses freeze.py's pieces:
- every source file in src/opt_agent/ (the runner, resampling.py, and the analysis,
  resampling_report.py, among them, the analysis also by name with its own SHA-256) and
  requirements.lock (installed packages must match it);
- the pre-registration, data/followup/split.json and both LLM4OR data files (git-ignored, so
  checked by hash: the follow-up's section 2);
- by name, what Claude sees and how it's sampled: the model, max_tokens, thinking, effort, the
  formulation and baseline prompts and schemas, the cells (conditions and samples), the run
  order's seed, the scoring tolerance and the unexposed id list.

Before the approval, unfinished() also checks section 3's promise from the files: for every
one of the 121 problems, this study's formulation and baseline requests have the same cache
key as the follow-up's sample-0 requests (api.KEYED_FIELDS: model, system prompt, messages,
max_tokens, thinking, effort).

`python -m opt_agent.resampling_freeze` lists what's left and whether the inputs match.
`python -m opt_agent.resampling_freeze approve --by "..."` writes docs/resampling/FREEZE.json.
It's the owner's step; for this study the owner approved the pre-registration in chat on
2026-11-19 and asked Claude to run it (the approval records who and how). resampling.problems
calls check() before it reads a problem.
"""

import argparse
import sys
from datetime import date

from opt_agent import (
    api,
    baseline,
    followup,
    followup_freeze,
    followup_report,
    formulate,
    resampling,
)
from opt_agent.api import Cache
from opt_agent.freeze import (
    LOCK_PATH,
    SOURCE_DIR,
    Approval,
    FreezeError,
    _canonical,
    _relative,
    _sha256,
    approval_at_tag,
    differences,
    digest,
    drifted_packages,
)
from opt_agent.runs import REPO_ROOT, git

FREEZE_PATH = REPO_ROOT / "docs" / "resampling" / "FREEZE.json"
FREEZE_TAG = "resampling-freeze"
PREREGISTRATION_PATH = REPO_ROOT / "docs" / "RESAMPLING_PREREGISTRATION.md"
ANALYSIS_PATH = SOURCE_DIR / "resampling_report.py"
FOLLOWUP_CACHE = REPO_ROOT / "runs" / "followup-test" / "cache"


class ResamplingApproval(Approval):
    analysis_sha256: str  # resampling_report.py, by name; also in the fingerprint
    approved_by: str  # who approved, and how


# ---- the fingerprint --------------------------------------------------------------------


def fingerprint() -> dict[str, str]:
    """Name -> SHA-256: repo-relative paths for files, dotted names for values. A missing data
    file is hashed as "missing", so the difference names it."""
    files = [PREREGISTRATION_PATH, followup.SPLIT_PATH, LOCK_PATH,
             *sorted(SOURCE_DIR.rglob("*.py"))]  # fmt: skip
    prints = {_relative(p): _sha256(p.read_bytes()) for p in files}
    prints |= {_relative(p): _sha256(p.read_bytes()) if p.exists() else "missing"
               for p in followup_freeze.data_files()}  # fmt: skip
    prints |= {name: _sha256(_canonical(value)) for name, value in frozen_values().items()}
    return dict(sorted(prints.items()))


def frozen_values() -> dict[str, object]:
    """What sections 2 to 4 name. Each is also inside a source file's hash; naming them says
    which one changed."""
    return {
        "model": resampling.MODEL,
        "api.MAX_TOKENS": api.MAX_TOKENS,
        "api.THINKING": api.THINKING,
        "api.EFFORT": api.EFFORT,
        "temperature": "not sent (the API default, 1)",
        "formulate.SYSTEM_PROMPT": formulate.SYSTEM_PROMPT,
        "formulate.LP_SCHEMA": formulate.LP_SCHEMA,
        "baseline.SYSTEM_PROMPT": baseline.SYSTEM_PROMPT,
        "baseline.ANSWER_SCHEMA": baseline.ANSWER_SCHEMA,
        "cells": [list(cell) for cell in resampling.CELLS],
        "unit_sample": resampling.UNIT_SAMPLE,
        "seed.order": followup.ORDER_SEED,
        "tolerance": followup.TOLERANCE,
        "ids.unexposed": followup_freeze.id_list_sha256(unexposed_only=True),
    }


# ---- before the approval ----------------------------------------------------------------


def requests_differ() -> list[str]:
    """Section 3: the 121 problems whose formulation or baseline request isn't the follow-up's
    (by cache key, sample 0); empty if none. Labels only."""
    exposed = followup_report.exposed_labels()
    cache, differ = Cache(FOLLOWUP_CACHE), []
    for p in followup.read_test():
        if not p.scorable or p.id in exposed:
            continue
        for module in (formulate, baseline):
            request = module.build_request(p.document, resampling.MODEL)
            if cache.get(cache.key(request)) is None:
                differ.append(f"{p.id} ({module.__name__.rsplit('.', 1)[1]})")
    return differ


def unfinished() -> list[str]:
    """What's left before the approval, checked from the files; empty when nothing is."""
    todo = []
    if "**Status: DRAFT" in PREREGISTRATION_PATH.read_text():
        todo.append(f"{_relative(PREREGISTRATION_PATH)} is still a draft: approve it first")
    if _sha256(followup.SPLIT_PATH.read_bytes()) != followup_freeze.SPLIT_SHA256:
        todo.append("data/followup/split.json isn't the follow-up's")
    data = followup_freeze.data_files()
    for path, sha in zip(data, followup_freeze.DATA_SHA256.values(), strict=True):
        if not path.exists():
            todo.append(f"{_relative(path)} is missing (python scripts/fetch_llm4or.py)")
        elif _sha256(path.read_bytes()) != sha:
            todo.append(f"{_relative(path)} isn't the follow-up's file")
    if followup_freeze.id_list_sha256(unexposed_only=True) != followup_freeze.UNEXPOSED_SHA256:
        todo.append("the 121 unexposed ids don't give the follow-up's id-list hash")
    if all(path.exists() for path in data) and (differ := requests_differ()):
        todo.append(f"these requests aren't the follow-up's (section 3): {differ[:5]}")
    return todo


def approve(approved_by: str, today: str | None = None) -> ResamplingApproval:
    """Writes docs/resampling/FREEZE.json with the current fingerprint."""
    todo = unfinished()
    if git("status", "--porcelain"):
        todo.append("the working tree has uncommitted changes: commit first, so the approved "
                    "inputs are the ones in git")  # fmt: skip
    if drifted := drifted_packages():
        todo.append(f"installed packages differ from requirements.lock: {sorted(drifted)}")
    if todo:
        raise FreezeError("not ready to freeze the resampling study:\n  " + "\n  ".join(todo))
    prints = fingerprint()
    approval = ResamplingApproval(
        approved_on=today or date.today().isoformat(), commit=git("rev-parse", "HEAD"),
        fingerprint=prints, analysis_sha256=prints[_relative(ANALYSIS_PATH)],
        approved_by=approved_by,
    )  # fmt: skip
    FREEZE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FREEZE_PATH.write_text(approval.model_dump_json(indent=1) + "\n")
    return approval


# ---- checking ---------------------------------------------------------------------------


def approved() -> ResamplingApproval | None:
    if not FREEZE_PATH.exists():
        return None
    return ResamplingApproval.model_validate_json(FREEZE_PATH.read_text())


def check() -> str:
    """The approved fingerprint's digest, if the current inputs are exactly the approved ones
    and the installed packages are the locked ones; otherwise FreezeError, naming every
    difference (names only, never contents)."""
    approval = approved()
    if approval is None:
        raise FreezeError("the resampling study isn't frozen: python -m opt_agent."
                          "resampling_freeze approve, after the steps it lists")  # fmt: skip
    problems = differences(approval.fingerprint, fingerprint())
    if approval.fingerprint.get(_relative(ANALYSIS_PATH)) != approval.analysis_sha256:
        problems.append(f"{FREEZE_PATH.name}: analysis_sha256 isn't the fingerprint's")
    problems += [f"{name}: installed {installed}, locked {locked}"
                 for name, (locked, installed) in drifted_packages().items()]  # fmt: skip
    if problems:
        raise FreezeError(f"the inputs differ from the resampling study's approval of "
                          f"{approval.approved_on}:\n  " + "\n  ".join(problems))  # fmt: skip
    return digest(approval.fingerprint)


def tag_problems(tag: str = FREEZE_TAG) -> list[str]:
    """Does `tag` hold exactly the approved inputs? Empty if it does (freeze.approval_at_tag:
    everything read from git's objects). The LLM4OR data is git-ignored: a copy that's here
    must be the approved one."""
    approval, problems = approval_at_tag(
        tag, "docs/resampling/FREEZE.json", FREEZE_PATH, ResamplingApproval, ("data/external/",)
    )
    if approval is None:
        return problems
    if approval.fingerprint.get(_relative(ANALYSIS_PATH)) != approval.analysis_sha256:
        problems.append(f"docs/resampling/FREEZE.json at {tag}: analysis_sha256 isn't the "
                        "fingerprint's")  # fmt: skip
    for path in followup_freeze.data_files():
        name = _relative(path)
        if path.exists() and _sha256(path.read_bytes()) != approval.fingerprint.get(name):
            problems.append(f"{name}: here, but not the file approved at {tag}")
    return problems


def tag_exists(tag: str = FREEZE_TAG) -> bool:
    return git("rev-parse", "--verify", "--quiet", f"{tag}^{{commit}}") is not None


# ---- command line -----------------------------------------------------------------------


def status() -> str:
    todo = unfinished()
    lines = ["Left to do before the resampling freeze:" if todo
             else "Nothing left to do before the resampling freeze."]  # fmt: skip
    lines += [f"- {item}" for item in todo]
    approval = approved()
    if approval is None:
        return "\n".join([*lines, "Not frozen yet (no docs/resampling/FREEZE.json)."])
    problems = tag_problems()
    if problems:
        lines.append(f"TAG {FREEZE_TAG} DOESN'T HOLD THE APPROVED INPUTS:\n  "
                     + "\n  ".join(problems))  # fmt: skip
    else:
        lines.append(f"Tag {FREEZE_TAG} verifies: it holds the approved inputs.")
    try:
        check()
    except FreezeError as error:
        lines.append(f"HEAD doesn't match the freeze, so the study can't run here: {error}")
    else:
        lines.append(f"Frozen on {approval.approved_on} ({approval.approved_by}); the "
                     "inputs match, so the study may run (python -m opt_agent.resampling "
                     "--plan first)")  # fmt: skip
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The resampling study's freeze.")
    parser.add_argument("action", nargs="?", choices=["status", "approve"], default="status")
    parser.add_argument("--by", help="approve: who approved it, and how")
    args = parser.parse_args(argv)
    if args.action == "status":
        print(status())
        return
    if not args.by:
        sys.exit("approve needs --by: who approved the pre-registration, and how")
    try:
        approval = approve(args.by)
    except FreezeError as error:
        sys.exit(str(error))
    print(f"Wrote {_relative(FREEZE_PATH)} ({len(approval.fingerprint)} hashes, commit "
          f"{approval.commit}). Commit it, then tag that commit {FREEZE_TAG}.")  # fmt: skip


if __name__ == "__main__":
    main()
