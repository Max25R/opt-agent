"""The second-model study's freeze (docs/SECOND_MODEL_PREREGISTRATION.md, section 6, and
Amendment 1): its run starts only when the study's tag exists and holds exactly the approved
inputs, and the inputs here are those.

There are two approvals. The first (ORIGINAL_PATH, tag ORIGINAL_TAG, 2026-11-22) froze the
study as registered; Amendment 1 changed it before any call (stage 1's cap; stage 2, the
no-solver baseline), so the amended study has its own (FREEZE_PATH, tag FREEZE_TAG), and only
that one gates the run. The first stays as it was committed, and its tag must still hold it
(original_tag_problems).

It works like the resampling study's (resampling_freeze.py) and reuses freeze.py's pieces:
- **The fingerprint:** every source file in src/opt_agent/ (the runner, second_model.py, and
  the analysis, second_model_report.py, the analysis also by name with its own SHA-256),
  requirements.lock (installed packages must match it), the pre-registration with its
  amendment, data/followup/split.json, Haiku's record (runs/followup-test/results.jsonl:
  committed, so the tag holds it too) and both LLM4OR data files (git-ignored, so checked by
  hash); and by name, what the comparisons rest on: both models, max_tokens, thinking, effort,
  the formulation and the no-solver prompts and schemas, the stages and their caps, Haiku's
  sample, Sonnet's prices, the run order's and the bootstrap's seeds, the scoring tolerance,
  alpha, the checkpoint and the unexposed id list.
- **Before the approval,** unfinished() checks the promises of section 3 and Amendment 1
  from the files, in both conditions: for each of the 121 problems, Sonnet's request is
  Haiku's sample-0 request with only the model changed, and Haiku's, built by this code, is
  byte for byte the request its run sent (the follow-up's cache); and approve() also replays
  Haiku's sample-0 answers in both conditions from that cache through this code, with a
  client that can't send anything, and requires every recorded field back
  (haiku_replay_differs): the solving, the parsing and the checks are the same in effect.
- **ready()** is the run's gate: the tag exists and holds exactly the approval (read from
  git's objects, freeze.approval_at_tag), and check() passes here. second_model.inputs calls
  it before a run reads a problem.

`python -m opt_agent.second_model_freeze` says what's left and whether the run may start.
`python -m opt_agent.second_model_freeze approve --by "..."` writes FREEZE_PATH. For this
study the owner asked Claude to write the freezes and create their tags (2026-11-22, in chat);
each approval records who and how. Then commit it, and tag that commit FREEZE_TAG.
"""

import argparse
import json
import sys
import tempfile
from datetime import date
from pathlib import Path

from opt_agent import (
    api,
    baseline,
    evaluate,
    followup,
    followup_freeze,
    followup_report,
    formulate,
    pricing,
    second_model,
    second_model_report,
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
from opt_agent.runs import REPO_ROOT, Run, Tags, git

FREEZE_PATH = REPO_ROOT / "docs" / "second_model" / "FREEZE-2.json"  # Amendment 1's approval
FREEZE_TAG = "second-model-freeze-2"
ORIGINAL_PATH = REPO_ROOT / "docs" / "second_model" / "FREEZE.json"  # the first, superseded
ORIGINAL_TAG = "second-model-freeze"
PREREGISTRATION_PATH = REPO_ROOT / "docs" / "SECOND_MODEL_PREREGISTRATION.md"
ANALYSIS_PATH = SOURCE_DIR / "second_model_report.py"
HAIKU_CACHE = second_model.HAIKU_RECORD.parent / "cache"
# Section 2: the record every Sonnet answer is paired with, by its SHA-256.
HAIKU_RECORD_SHA256 = "cedc37164ab5497a62fd79c06154f9cb15f384fa6307174b46d949282c20c18e"
CONDITIONS = (second_model.CONDITION, second_model.BASELINE)  # both stages'
# What a replay can't repeat: time, and what was paid or replayed (as scripts/reproduce.py).
NOT_REPLAYED = {"run_id", "latency_s", "retry_s", "wall_s", "cached_calls", "paid_usd",
                "report_only_paid_usd"}  # fmt: skip
# The one message reworded since followup-freeze (api.UNFINISHED["max_tokens"]): a cut-off
# reply's reason. The words changed, not what it says, so a replay reads the old as the new.
REWORDED = ("the reply was cut off at 16000 tokens",
            "the reply was cut off at its max_tokens limit")  # fmt: skip


class SecondModelApproval(Approval):
    analysis_sha256: str  # second_model_report.py, by name; also in the fingerprint
    approved_by: str  # who approved, and how


# ---- the fingerprint --------------------------------------------------------------------


def fingerprint() -> dict[str, str]:
    """Name -> SHA-256: repo-relative paths for files, dotted names for values. A missing data
    file is hashed as "missing", so the difference names it."""
    files = [PREREGISTRATION_PATH, followup.SPLIT_PATH, LOCK_PATH, second_model.HAIKU_RECORD,
             *sorted(SOURCE_DIR.rglob("*.py"))]  # fmt: skip
    prints = {_relative(p): _sha256(p.read_bytes()) for p in files}
    prints |= {_relative(p): _sha256(p.read_bytes()) if p.exists() else "missing"
               for p in followup_freeze.data_files()}  # fmt: skip
    prints |= {name: _sha256(_canonical(value)) for name, value in frozen_values().items()}
    return dict(sorted(prints.items()))


def frozen_values() -> dict[str, object]:
    """What sections 2 to 6 and Amendment 1 name. Each is also inside a source file's hash;
    naming them says which one changed."""
    normal, long = pricing.PRICES[second_model.MODEL]
    return {
        "model": second_model.MODEL,
        "haiku.model": second_model.HAIKU_MODEL,
        "haiku.record": _relative(second_model.HAIKU_RECORD),
        "haiku.sample": second_model.HAIKU_SAMPLE,
        "sample": second_model.SAMPLE,
        "stages": [list(stage) for stage in second_model.STAGES],
        "api.MAX_TOKENS": api.MAX_TOKENS,
        "api.THINKING": api.THINKING,
        "api.EFFORT": api.EFFORT,
        "temperature": "not sent (the API default, 1)",
        "formulate.SYSTEM_PROMPT": formulate.SYSTEM_PROMPT,
        "formulate.LP_SCHEMA": formulate.LP_SCHEMA,
        "baseline.SYSTEM_PROMPT": baseline.SYSTEM_PROMPT,
        "baseline.ANSWER_SCHEMA": baseline.ANSWER_SCHEMA,
        "prices": [normal.model_dump(), long.model_dump()],
        "seed.order": followup.ORDER_SEED,
        "seed.bootstrap": followup_report.BOOTSTRAP_SEED,
        "tolerance": followup.TOLERANCE,
        "alpha": second_model_report.ALPHA,
        "checkpoint": second_model.CHECKPOINT,
        "ids.unexposed": followup_freeze.id_list_sha256(unexposed_only=True),
    }


# ---- before the approval ----------------------------------------------------------------


def problems() -> list[followup.Problem]:
    """The 121 problems in run order, with no gate: only for the checks before it exists."""
    return second_model.select(followup.read_test())


def recorded(condition: str = second_model.CONDITION) -> dict[str, evaluate.Item]:
    """Haiku's sample-0 items in `condition`: the pairs (section 2, Amendment 1)."""
    return {i.problem_id: i for i in evaluate.latest_items(second_model.HAIKU_RECORD)
            if i.condition == condition and i.sample == second_model.HAIKU_SAMPLE}  # fmt: skip


def requests_differ(records: list[followup.Problem] | None = None) -> list[str]:
    """Section 3 and Amendment 1: the problems whose Sonnet request, in either condition, isn't
    Haiku's sample-0 request with only the model changed, or whose Haiku request, built here,
    isn't byte for byte the one its run sent (stored with its reply in the follow-up's cache,
    under its cache key). Labels only: the problem text is licensed data."""
    found = []
    for record in records or problems():
        for module in (formulate, baseline):
            haiku = module.build_request(record.document, second_model.HAIKU_MODEL)
            sonnet = module.build_request(record.document, second_model.MODEL)
            stored = HAIKU_CACHE / f"{api.cache_key(haiku)}.json"  # api.Cache's file name
            sent = json.loads(stored.read_text())["request"] if stored.exists() else None
            which = f"{record.id} ({module.__name__.rsplit('.', 1)[1]})"
            if sent is None:
                found.append(f"{which}: Haiku's request isn't in its run's cache")
            elif api.canonical_json(sent) != api.canonical_json(haiku):
                found.append(f"{which}: Haiku's request isn't the one its run sent")
            if sonnet != {**haiku, "model": second_model.MODEL}:
                found.append(f"{which}: Sonnet's request differs from Haiku's in more than "
                             "the model")  # fmt: skip
    return found


def haiku_replay_differs(records: list[followup.Problem] | None = None) -> list[str]:
    """Section 3 and Amendment 1: Haiku's sample-0 answers in both conditions, replayed from
    the follow-up's cache through this code (api.ReplayOnlyClient: no key, and nothing can be
    sent), against the recorded items: every field but time and payment. Empty if every
    answer comes back as recorded."""
    found = []
    with tempfile.TemporaryDirectory(prefix="second-model-replay-") as tmp:
        session = Run(log_path=Path(tmp) / "attempts.jsonl", cache=Cache(HAIKU_CACHE))
        for condition in CONDITIONS:
            recorded_items = recorded(condition)
            for record in records or problems():
                tags = Tags(problem_id=record.id, split=followup.TEST_SPLIT, condition=condition)
                try:
                    item = evaluate.run_item(record, condition, api.ReplayOnlyClient(),  # type: ignore[arg-type]  # it stands in for anthropic.Anthropic
                                             session, tags, second_model.HAIKU_MODEL)  # fmt: skip
                except api.NotCached:
                    found.append(f"{record.id} ({condition}): a call isn't in Haiku's cache")
                    continue
                before = recorded_items[record.id].model_dump(mode="json")
                if isinstance(before.get("reason"), str):
                    before["reason"] = before["reason"].replace(*REWORDED)
                after = item.model_dump(mode="json")
                found += [f"{record.id} ({condition}) {name}: recorded {before.get(name)!r}, "
                          f"replayed {after.get(name)!r}"
                          for name in sorted((before.keys() | after.keys()) - NOT_REPLAYED)
                          if before.get(name) != after.get(name)]  # fmt: skip
    return found


def unfinished(replay: bool = False) -> list[str]:
    """What's left before the approval, checked from the files; empty when nothing is. With
    `replay`, also haiku_replay_differs (about 20 s: approve() runs it)."""
    todo = []
    if not PREREGISTRATION_PATH.exists():
        todo.append(f"{_relative(PREREGISTRATION_PATH)} is missing")
    elif "**Status: DRAFT" in PREREGISTRATION_PATH.read_text():
        todo.append(f"{_relative(PREREGISTRATION_PATH)} is still a draft")
    if _sha256(second_model.HAIKU_RECORD.read_bytes()) != HAIKU_RECORD_SHA256:
        todo.append(f"{_relative(second_model.HAIKU_RECORD)} isn't the record section 2 names")
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
    if not all(path.exists() for path in data):
        return todo  # the checks below read the problems
    records = problems()
    for condition in CONDITIONS:
        pairs = recorded(condition)
        if unpaired := [r.id for r in records if r.id not in pairs]:
            todo.append(f"Haiku's record has no sample-0 {condition} answer for {unpaired[:5]}")
    if differ := requests_differ(records):
        todo.append(f"these requests aren't Haiku's but for the model: {differ[:5]}")
    if replay and (differ := haiku_replay_differs(records)):
        todo.append(f"Haiku's answers don't replay as recorded: {differ[:5]}")
    return todo


def approve(approved_by: str, today: str | None = None) -> SecondModelApproval:
    """Writes FREEZE_PATH with the current fingerprint."""
    todo = unfinished(replay=True)
    if git("status", "--porcelain"):
        todo.append("the working tree has uncommitted changes: commit first, so the approved "
                    "inputs are the ones in git")  # fmt: skip
    if drifted := drifted_packages():
        todo.append(f"installed packages differ from requirements.lock: {sorted(drifted)}")
    if todo:
        raise FreezeError("not ready to freeze the second-model study:\n  " + "\n  ".join(todo))
    prints = fingerprint()
    approval = SecondModelApproval(
        approved_on=today or date.today().isoformat(), commit=git("rev-parse", "HEAD"),
        fingerprint=prints, analysis_sha256=prints[_relative(ANALYSIS_PATH)],
        approved_by=approved_by,
    )  # fmt: skip
    FREEZE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FREEZE_PATH.write_text(approval.model_dump_json(indent=1) + "\n")
    return approval


# ---- checking ---------------------------------------------------------------------------


def approved() -> SecondModelApproval | None:
    if not FREEZE_PATH.exists():
        return None
    return SecondModelApproval.model_validate_json(FREEZE_PATH.read_text())


def check() -> str:
    """The approved fingerprint's digest, if the current inputs are exactly the approved ones
    and the installed packages are the locked ones; otherwise FreezeError, naming every
    difference (names only, never contents)."""
    approval = approved()
    if approval is None:
        raise FreezeError("the second-model study isn't frozen: python -m opt_agent."
                          "second_model_freeze approve, after the steps it lists")  # fmt: skip
    problems = differences(approval.fingerprint, fingerprint())
    if approval.fingerprint.get(_relative(ANALYSIS_PATH)) != approval.analysis_sha256:
        problems.append(f"{FREEZE_PATH.name}: analysis_sha256 isn't the fingerprint's")
    problems += [f"{name}: installed {installed}, locked {locked}"
                 for name, (locked, installed) in drifted_packages().items()]  # fmt: skip
    if problems:
        raise FreezeError(f"the inputs differ from the second-model study's approval of "
                          f"{approval.approved_on}:\n  " + "\n  ".join(problems))  # fmt: skip
    return digest(approval.fingerprint)


def tag_problems(tag: str = FREEZE_TAG, path: Path = FREEZE_PATH) -> list[str]:
    """Does `tag` hold exactly the approval in `path`? Empty if it does (everything read from
    git's objects). The LLM4OR data is git-ignored: a copy that's here must be the approved
    one."""
    approval, problems = approval_at_tag(tag, _relative(path), path, SecondModelApproval,
                                         ("data/external/",))  # fmt: skip
    if approval is None:
        return problems
    if approval.fingerprint.get(_relative(ANALYSIS_PATH)) != approval.analysis_sha256:
        problems.append(f"{_relative(path)} at {tag}: analysis_sha256 isn't the fingerprint's")
    for data in followup_freeze.data_files():
        name = _relative(data)
        if data.exists() and _sha256(data.read_bytes()) != approval.fingerprint.get(name):
            problems.append(f"{name}: here, but not the file approved at {tag}")
    return problems


def original_tag_problems() -> list[str]:
    """The first approval, superseded by Amendment 1, must still be what its tag holds."""
    return tag_problems(ORIGINAL_TAG, ORIGINAL_PATH)


def tag_exists(tag: str = FREEZE_TAG) -> bool:
    return git("rev-parse", "--verify", "--quiet", f"{tag}^{{commit}}") is not None


def ready() -> str:
    """The run's gate: the tag exists, it holds exactly the approval, and the inputs here are
    the approved ones (check). The digest, or FreezeError saying what's wrong."""
    if not tag_exists():
        raise FreezeError(f"no tag {FREEZE_TAG} here (git fetch --tags): the run starts only "
                          "from the frozen study")  # fmt: skip
    if problems := tag_problems():
        raise FreezeError(f"tag {FREEZE_TAG} doesn't hold the approved inputs:\n  "
                          + "\n  ".join(problems))  # fmt: skip
    return check()


# ---- command line -----------------------------------------------------------------------


def status() -> str:
    todo = unfinished()
    lines = ["Left to do before the second-model freeze:" if todo
             else "Nothing left to do before the second-model freeze."]  # fmt: skip
    lines += [f"- {item}" for item in todo]
    approval = approved()
    if approval is None:
        return "\n".join([*lines, f"Not frozen yet (no {_relative(FREEZE_PATH)})."])
    try:
        ready()
    except FreezeError as error:
        lines.append(f"THE RUN CAN'T START HERE: {error}")
    else:
        lines.append(f"Frozen on {approval.approved_on} ({approval.approved_by}); tag "
                     f"{FREEZE_TAG} verifies and the inputs match, so the run may start "
                     "(python -m opt_agent.second_model --plan first).")  # fmt: skip
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The second-model study's freeze.")
    parser.add_argument("action", nargs="?", choices=["status", "approve"], default="status")
    parser.add_argument("--by", help="approve: who approved the pre-registration, and how")
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
