"""The freeze (pre-registration, section 6): the test split runs only on exactly the inputs
the owner approved.

The **fingerprint** is a SHA-256 for each thing a test run's answers or scores depend on:
- the hand-written inputs and the ground truth: reviews.json, integrality.json,
  exclusions.json, test.json and test-perturbed.json;
- the prompts and schemas Claude sees, each by name (formulate.SYSTEM_PROMPT, ...), and the
  perturbation's seed;
- every source file in src/opt_agent/. The pre-registration lists the prompts, but code
  changes answers too: feedback.py writes the messages self-correction sends Claude, and
  the solvers, the checks and the scoring are code;
- requirements.lock, and the installed packages must match it (another CBC or HiGHS can
  give another answer);
- docs/PREREGISTRATION.md itself.

`python -m opt_agent.freeze` shows what's left to do before the freeze (the
pre-registration's "Before freezing" list, checked from the files) and how the current
fingerprint differs from the approved one. `python -m opt_agent.freeze approve` is the
owner's step, never Claude's: it refuses until that list is done and the tree is committed,
then writes docs/FREEZE.json. Every pass of a test-split run checks the fingerprint against
it first (evaluate.py) and refuses on any difference, naming each one. Every pass records
its fingerprint's digest in its log, so the report can show which inputs each pass ran on.

After the M6 runs, HEAD moves on (milestone 7 changes src/), so the working tree no longer
matches the approval, as it shouldn't. What stays checkable is the tag `m6-freeze`, the
commit both test runs ran on: tag_problems() reads it from git's objects, and a test runs it
in CI. check() still compares the working tree, because it gates a new test run.
"""

import argparse
import hashlib
import subprocess
import sys
from datetime import date
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from pydantic import BaseModel

from opt_agent import baseline, explain, external_check, formulate, packets, perturb
from opt_agent.api import canonical_json
from opt_agent.ground_truth import (
    EXCLUSIONS_PATH,
    GROUND_TRUTH_DIR,
    INTEGRALITY_PATH,
    REVIEWS_PATH,
    load_exclusions,
    load_integrality,
    load_records,
    load_reviews,
)
from opt_agent.runs import REPO_ROOT, git

FREEZE_PATH = REPO_ROOT / "docs" / "FREEZE.json"
FREEZE_TAG = "m6-freeze"  # the commit both M6 test runs ran on; it adds docs/FREEZE.json
PREREGISTRATION_PATH = REPO_ROOT / "docs" / "PREREGISTRATION.md"
LOCK_PATH = REPO_ROOT / "requirements.lock"
SOURCE_DIR = REPO_ROOT / "src" / "opt_agent"
INPUTS = [
    REVIEWS_PATH, INTEGRALITY_PATH, EXCLUSIONS_PATH, GROUND_TRUTH_DIR / "test.json",
    GROUND_TRUTH_DIR / "test-perturbed.json", PREREGISTRATION_PATH, LOCK_PATH,
]  # fmt: skip


class FreezeError(Exception):
    """A test run can't start: the inputs aren't the approved ones, or nothing is approved."""


class Approval(BaseModel):
    approved_on: str
    commit: str | None  # the commit it was approved at, for reference
    fingerprint: dict[str, str]


# ---- the fingerprint --------------------------------------------------------------------


def fingerprint() -> dict[str, str]:
    """Name -> SHA-256: repo-relative paths for files, dotted names for values."""
    sources = sorted(SOURCE_DIR.rglob("*.py"))
    prints = {_relative(p): _sha256(p.read_bytes()) for p in [*INPUTS, *sources]}
    prints |= {name: _sha256(_canonical(value)) for name, value in frozen_values().items()}
    return dict(sorted(prints.items()))


def frozen_values() -> dict[str, object]:
    """What Claude sees, by name, as section 6 lists it. Each is also in a source file's
    hash; naming them says which one changed."""
    return {
        "formulate.SYSTEM_PROMPT": formulate.SYSTEM_PROMPT,
        "formulate.LP_SCHEMA": formulate.LP_SCHEMA,  # built by the SDK: depends on its version
        "explain.SYSTEM_PROMPT": explain.SYSTEM_PROMPT,
        "baseline.SYSTEM_PROMPT": baseline.SYSTEM_PROMPT,
        "baseline.ANSWER_SCHEMA": baseline.ANSWER_SCHEMA,
        "perturb.SEED": perturb.SEED,
    }


def digest(prints: dict[str, str]) -> str:
    """One hash for a whole fingerprint, for a run's log."""
    return _sha256(canonical_json(prints))


def differences(approved: dict[str, str], current: dict[str, str]) -> list[str]:
    """In words, each way the current fingerprint differs from the approved one."""
    changed = []
    for name in sorted(approved.keys() | current.keys()):
        if name not in current:
            changed.append(f"{name}: gone")
        elif name not in approved:
            changed.append(f"{name}: new")
        elif approved[name] != current[name]:
            changed.append(f"{name}: changed")
    return changed


def locked_versions() -> dict[str, str]:
    lines = LOCK_PATH.read_text().splitlines()
    pins = [line.split("==") for line in lines if line and not line.startswith("#")]
    return {name.lower(): pinned for name, pinned in pins}


def drifted_packages() -> dict[str, tuple[str, str | None]]:
    """name -> (locked, installed) for each installed version that isn't the locked one."""
    drifted = {}
    for name, pinned in locked_versions().items():
        try:
            installed = version(name)
        except PackageNotFoundError:
            installed = None
        if installed != pinned:
            drifted[name] = (pinned, installed)
    return drifted


def _relative(path: Path) -> str:
    return (REPO_ROOT / path).resolve().relative_to(REPO_ROOT).as_posix()


def _canonical(value: object) -> str:
    return value if isinstance(value, str) else canonical_json(value)


def _sha256(content: str | bytes) -> str:
    data = content.encode() if isinstance(content, str) else content
    return hashlib.sha256(data).hexdigest()


# ---- checking and approving -------------------------------------------------------------


def approved() -> Approval | None:
    return Approval.model_validate_json(FREEZE_PATH.read_text()) if FREEZE_PATH.exists() else None


def check() -> str:
    """The approved fingerprint's digest, if the current inputs are exactly the approved
    ones and the installed packages are the locked ones. Otherwise FreezeError, naming
    every difference."""
    approval = approved()
    if approval is None:
        raise FreezeError(
            "nothing is frozen yet: the owner approves with `python -m opt_agent.freeze "
            "approve`, after the steps `python -m opt_agent.freeze` lists"
        )
    problems = differences(approval.fingerprint, fingerprint())
    problems += [f"{name}: installed {installed}, locked {locked}"
                 for name, (locked, installed) in drifted_packages().items()]  # fmt: skip
    if problems:
        raise FreezeError(
            f"the inputs differ from the ones approved on {approval.approved_on} "
            f"({FREEZE_PATH.name}):\n  " + "\n  ".join(problems)
        )
    return digest(approval.fingerprint)


def tag_problems(tag: str = FREEZE_TAG) -> list[str]:
    """Does `tag` hold exactly the approved inputs? Empty if it does. Read from git's
    objects, not the working tree, so it holds however far HEAD has moved:
    - the tag exists, and its docs/FREEZE.json is the one in the working tree;
    - the tag's parent is the commit the approval names (approve() records HEAD, and the
      owner then commits FREEZE.json on top);
    - every file the fingerprint names hashes the same at the tag, and the tag has no source
      file the fingerprint lacks. The named values (prompts, schemas, seed) are defined in
      those source files, and the schemas by the locked SDK, so the files cover them."""
    commit = git("rev-parse", "--verify", "--quiet", f"{tag}^{{commit}}")
    if commit is None:
        return [f"no tag {tag} here (git fetch --tags; CI's checkout needs fetch-depth: 0)"]
    committed = _committed(commit, "docs/FREEZE.json")
    if committed is None:
        return [f"docs/FREEZE.json isn't in {tag} ({commit[:7]})"]
    approval = Approval.model_validate_json(committed)
    problems = []
    if not FREEZE_PATH.exists() or FREEZE_PATH.read_bytes() != committed:
        problems.append(f"docs/FREEZE.json differs from the one in {tag}")
    if git("rev-parse", f"{commit}^") != approval.commit:
        problems.append(f"{tag}'s parent isn't the approved commit {approval.commit}")
    for name, sha in approval.fingerprint.items():
        if "/" not in name:
            continue  # a named value, covered by the source file that defines it
        content = _committed(commit, name)
        if content is None:
            problems.append(f"{name}: not in {tag}")
        elif _sha256(content) != sha:
            problems.append(f"{name}: differs at {tag}")
    sources = git("ls-tree", "-r", "--name-only", commit, "--", _relative(SOURCE_DIR)) or ""
    problems += [f"{path}: in {tag} but not in the approval"
                 for path in sources.splitlines()
                 if path.endswith(".py") and path not in approval.fingerprint]  # fmt: skip
    return problems


def _committed(commit: str, path: str) -> bytes | None:
    """A file's bytes as committed, or None if it isn't there."""
    try:
        done = subprocess.run(["git", "show", f"{commit}:{path}"], cwd=REPO_ROOT,
                              capture_output=True)  # fmt: skip
    except OSError:  # no git at all
        return None
    return done.stdout if done.returncode == 0 else None


def unfinished() -> list[str]:
    """What's left before the owner may approve: the pre-registration's own approval, its
    "Before freezing" list (section 6, as Amendment 2 changes it), and a ground truth built
    from the current hand inputs. Checked from the files; empty when nothing is left."""
    todo = []
    if "**Status: DRAFT" in PREREGISTRATION_PATH.read_text():
        todo.append("docs/PREREGISTRATION.md is still a draft: the owner approves it first")
    return todo + judged_labels() + cross_check() + stale_ground_truth()


def judged_labels() -> list[str]:
    """Amendment 2, part 3: both judges' sheets filled in, and the label the two give
    together (packets.combined_labels) applied to integrality.json with source `judge`."""
    sheets, todo = [], []
    for name in packets.JUDGE_SHEETS.values():
        try:
            sheets.append(packets.read_judge_labels(packets.JUDGE_DIR / name))
        except ValueError as unfilled:
            todo.append(f"review/integrality_judge/{name} isn't all filled in ({unfilled})")
    if todo:
        return todo
    combined = packets.combined_labels(*sheets)
    labels = load_integrality(INTEGRALITY_PATH)
    unapplied = sum(
        (label := labels.get(("test", pid))) is None
        or (label.source, label.kind) != ("judge", kind)
        for pid, kind in combined.items()
    )
    if unapplied:
        return [f"{unapplied} of the {len(combined)} judged labels aren't in integrality.json "
                "yet (source judge)"]  # fmt: skip
    return []


def cross_check() -> list[str]:
    """Amendment 2, parts 2, 5 and 6: a decision on every problem the external cross-check
    lists (review/external_check.csv), the judged ones as the review judges' replies give
    them, and every decision applied to the hand inputs. Read from the committed sheet,
    since the benchmark itself isn't committed."""
    path = external_check.DECISIONS_PATH
    if not path.exists():
        return ["the external cross-check hasn't been run (python -m opt_agent.external_check)"]
    try:
        rows = external_check.read_decisions(path)
    except ValueError as wrong:
        return [f"review/external_check.csv has a decision it doesn't allow ({wrong})"]
    try:
        judged = external_check.judged_decisions()
    except ValueError as unfilled:
        return [f"the review judges' sheets aren't all filled in ({unfilled})"]
    todo = []
    undecided = sum(not row["decision"] for row in rows)
    if undecided:
        todo.append(f"{undecided} of the {len(rows)} problems in review/external_check.csv "
                    "have no decision yet")  # fmt: skip
    decided = {row["problem_id"]: row["decision"] for row in rows}
    off = [pid for pid, (decision, _) in judged.items() if decided.get(pid) != decision]
    if off:
        todo.append(f"review/external_check.csv doesn't follow the review judges for {off} "
                    "(python -m opt_agent.external_check judges --decide)")  # fmt: skip
    unapplied = [row["problem_id"] for row in rows if not _applied(row)]
    if unapplied:
        todo.append(f"{len(unapplied)} decisions in review/external_check.csv aren't in the "
                    "hand inputs yet (python -m opt_agent.external_check apply)")  # fmt: skip
    return todo


def _applied(row: dict[str, str]) -> bool:
    """A decision as the hand inputs must show it: a review's outcome in reviews.json, an
    exclusion in exclusions.json, a changed label as `either` from the owner."""
    key, decision = ("test", row["problem_id"]), row["decision"]
    if decision in ("confirmed", "disputed"):
        review = load_reviews(REVIEWS_PATH).get(key)
        return review is not None and review.judged == decision
    if decision == "exclude":
        return key in load_exclusions(EXCLUSIONS_PATH)
    if decision == "change":
        label = load_integrality(INTEGRALITY_PATH).get(key)
        return label is not None and (label.kind, label.source) == ("either", "owner")
    return True  # keep, or not decided yet (counted above)


def stale_ground_truth() -> list[str]:
    """A review or label applied after the last rebuild would be frozen unused. So the
    committed test split must carry exactly the current reviews, labels and exclusions, and
    the perturbed split must be exactly its eligible problems, with the same reviews and
    labels."""
    reviews, labels = load_reviews(REVIEWS_PATH), load_integrality(INTEGRALITY_PATH)
    exclusions = load_exclusions(EXCLUSIONS_PATH)
    test = {r.id: r for r in load_records(GROUND_TRUTH_DIR / "test.json")}
    stale = set()
    for pid, r in test.items():
        key = ("test", pid)
        label = labels.get(key, r.integrality)  # a problem without a hand label has the rule's
        if (r.review, r.excluded, r.integrality) != (reviews.get(key), exclusions.get(key), label):
            stale.add(pid)
    perturbed = {r.id: r for r in load_records(GROUND_TRUTH_DIR / "test-perturbed.json")}
    eligible = {pid for pid, r in test.items() if perturb.ineligible_record(r) is None}
    stale |= set(perturbed) ^ eligible  # missing, or no longer eligible
    for pid, r in perturbed.items():
        if pid in test and (r.review, r.integrality) != (test[pid].review, test[pid].integrality):
            stale.add(pid)
    if not stale:
        return []
    return [f"the ground truth is older than the hand inputs for {len(stale)} problems: run "
            "`python -m opt_agent.ground_truth`, then `python -m opt_agent.perturb`"]  # fmt: skip


def approve(today: str | None = None) -> Approval:
    """The owner's step. Writes docs/FREEZE.json with the current fingerprint."""
    todo = unfinished()
    if git("status", "--porcelain"):
        todo.append("the working tree has uncommitted changes: commit first, so the approved "
                    "inputs are the ones in git")  # fmt: skip
    if drifted := drifted_packages():
        todo.append(f"installed packages differ from requirements.lock: {sorted(drifted)}")
    if todo:
        raise FreezeError("not ready to freeze:\n  " + "\n  ".join(todo))
    approval = Approval(approved_on=today or date.today().isoformat(),
                        commit=git("rev-parse", "HEAD"), fingerprint=fingerprint())  # fmt: skip
    FREEZE_PATH.write_text(approval.model_dump_json(indent=1) + "\n")
    return approval


# ---- command line -----------------------------------------------------------------------


def status() -> str:
    todo = unfinished()
    lines = ["Left to do before the freeze:" if todo else "Nothing left to do before the freeze."]
    lines += [f"- {item}" for item in todo]
    approval = approved()
    if approval is None:
        lines.append("Not approved yet (no docs/FREEZE.json), so test runs can't start.")
        return "\n".join(lines)
    try:
        check()
    except FreezeError as error:
        lines.append(f"FROZEN INPUTS CHANGED, so test runs can't start: {error}")
    else:
        lines.append(f"Frozen on {approval.approved_on}, and the inputs match: test runs may "
                     "start.")  # fmt: skip
    if problems := tag_problems():
        lines.append(f"TAG {FREEZE_TAG} DOESN'T HOLD THE APPROVED INPUTS:\n  "
                     + "\n  ".join(problems))  # fmt: skip
    else:
        lines.append(f"Tag {FREEZE_TAG} holds exactly the approved inputs: the M6 results "
                     "rebuild from it.")  # fmt: skip
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The pre-registration's freeze (section 6).")
    parser.add_argument("action", nargs="?", choices=["status", "approve"], default="status")
    args = parser.parse_args(argv)
    if args.action == "status":
        print(status())
        return
    try:
        approval = approve()
    except FreezeError as error:
        sys.exit(str(error))
    print(f"Wrote {FREEZE_PATH.relative_to(REPO_ROOT)} ({len(approval.fingerprint)} hashes, "
          f"commit {approval.commit}). Commit it; test runs may then start.")  # fmt: skip


if __name__ == "__main__":
    main()
