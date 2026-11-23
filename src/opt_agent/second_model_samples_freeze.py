"""The second-model samples study's freeze (docs/second_model/SAMPLES_PREREGISTRATION.md, section
6): its run starts only when the study's tag exists and holds exactly the approved inputs, and
the inputs here are those.

It works like the second-model study's (second_model_freeze.py) and reuses its pieces:
- **The fingerprint:** every source file in src/opt_agent/ (the runner,
  second_model_samples.py, and the analysis, second_model_samples_report.py, the analysis also
  by name with its own SHA-256), requirements.lock (installed packages must match it), the
  pre-registration, data/followup/split.json, both answer records the comparison rests on
  (Haiku's, runs/followup-test/results.jsonl, and Sonnet's sample 0,
  runs/second-model/results.jsonl: committed, so the tag holds them too) and both LLM4OR data
  files (git-ignored, so checked by hash); and by name, what the comparison rests on: both
  models, the samples, max_tokens, thinking, effort, the formulation prompt and schema,
  Sonnet's prices, the cap and the checkpoint, the run order's and the bootstrap's seeds, the
  scoring tolerance, alpha and the unexposed id list.
- **Before the approval,** unfinished() checks the promises of section 3 from the files: both
  records are the ones section 2 names, with a done single-shot item for every problem and
  sample they're used for; and for each of the 121 problems, the request samples 1 and 2 will
  send is the one the second-model study's run sent for Sonnet's sample 0, and Haiku's sample
  1 and 2 requests (as the follow-up's run sent them, in its cache under their salted keys) but
  for the model (requests_differ). approve() also replays every answer the comparison uses
  (Haiku's samples 0 to 2 and Sonnet's sample 0) from its run's cache through this code, with a
  client that can't send anything, and requires every recorded field back (replay_differs):
  the solving, the parsing and the checks are the same in effect.
- **ready()** is the run's gate: the tag exists and holds exactly the approval (read from
  git's objects, freeze.approval_at_tag), and check() passes here.
  second_model_samples.inputs calls it before a run reads a problem.

`python -m opt_agent.second_model_samples_freeze` says what's left and whether the run may
start. `python -m opt_agent.second_model_samples_freeze approve --by "..."` writes FREEZE_PATH.
For this study the owner asked Claude to write the freeze and create its tag (2026-11-23, in
chat); the approval records who and how. Then commit it, and tag that commit FREEZE_TAG.
"""

import argparse
import json
import sys
import tempfile
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from opt_agent import (
    api,
    evaluate,
    followup,
    followup_freeze,
    followup_report,
    formulate,
    pricing,
    second_model,
    second_model_samples,
    second_model_samples_report,
)
from opt_agent.api import Cache
from opt_agent.freeze import (
    LOCK_PATH,
    SOURCE_DIR,
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
from opt_agent.second_model_freeze import NOT_REPLAYED, REWORDED
from opt_agent.second_model_freeze import SecondModelApproval as SamplesApproval

FREEZE_PATH = REPO_ROOT / "docs" / "second_model" / "SAMPLES_FREEZE.json"
FREEZE_TAG = "second-model-samples-freeze"
PREREGISTRATION_PATH = REPO_ROOT / "docs" / "second_model" / "SAMPLES_PREREGISTRATION.md"
ANALYSIS_PATH = SOURCE_DIR / "second_model_samples_report.py"
SONNET_RECORD = second_model_samples.SONNET_RECORD
HAIKU_RECORD = second_model_samples.HAIKU_RECORD
SONNET_CACHE = SONNET_RECORD.parent / "cache"
HAIKU_CACHE = HAIKU_RECORD.parent / "cache"
# Section 2: the two records the comparison rests on, by their SHA-256.
SONNET_RECORD_SHA256 = "0440e003cdcb6db04a43dce88d30ce9993d246b8ad867b972e40a9a699189a49"
HAIKU_RECORD_SHA256 = "cedc37164ab5497a62fd79c06154f9cb15f384fa6307174b46d949282c20c18e"
CONDITION = second_model_samples.CONDITION


# The recorded answers the comparison uses: (model, record, cache, split, samples).
SOURCES = (
    (second_model_samples.HAIKU_MODEL, HAIKU_RECORD, HAIKU_CACHE, followup.TEST_SPLIT,
     second_model_samples.HAIKU_SAMPLES),
    (second_model_samples.MODEL, SONNET_RECORD, SONNET_CACHE, second_model.SPLIT, (0,)),
)  # fmt: skip


# ---- the fingerprint --------------------------------------------------------------------


def fingerprint() -> dict[str, str]:
    """Name -> SHA-256: repo-relative paths for files, dotted names for values. A missing data
    file is hashed as "missing", so the difference names it."""
    files = [PREREGISTRATION_PATH, followup.SPLIT_PATH, LOCK_PATH, HAIKU_RECORD, SONNET_RECORD,
             *sorted(SOURCE_DIR.rglob("*.py"))]  # fmt: skip
    prints = {_relative(p): _sha256(p.read_bytes()) for p in files}
    prints |= {_relative(p): _sha256(p.read_bytes()) if p.exists() else "missing"
               for p in followup_freeze.data_files()}  # fmt: skip
    prints |= {name: _sha256(_canonical(value)) for name, value in frozen_values().items()}
    return dict(sorted(prints.items()))


def frozen_values() -> dict[str, object]:
    """What sections 2 to 6 name. Each is also inside a source file's hash; naming them says
    which one changed."""
    normal, long = pricing.PRICES[second_model_samples.MODEL]
    return {
        "model": second_model_samples.MODEL,
        "samples": list(second_model_samples.SAMPLES),
        "condition": CONDITION,
        "sonnet.record": _relative(SONNET_RECORD),
        "sonnet.record_sample": 0,
        "haiku.model": second_model_samples.HAIKU_MODEL,
        "haiku.record": _relative(HAIKU_RECORD),
        "haiku.samples": list(second_model_samples.HAIKU_SAMPLES),
        "api.MAX_TOKENS": api.MAX_TOKENS,
        "api.THINKING": api.THINKING,
        "api.EFFORT": api.EFFORT,
        "temperature": "not sent (the API default, 1)",
        "formulate.SYSTEM_PROMPT": formulate.SYSTEM_PROMPT,
        "formulate.LP_SCHEMA": formulate.LP_SCHEMA,
        "prices": [normal.model_dump(), long.model_dump()],
        "cap_usd": second_model_samples.CAP_USD,
        "checkpoint": second_model_samples.CHECKPOINT,
        "seed.order": followup.ORDER_SEED,
        "seed.bootstrap": followup_report.BOOTSTRAP_SEED,
        "bootstrap.resamples": followup_report.BOOTSTRAP_RESAMPLES,
        "tolerance": followup.TOLERANCE,
        "alpha": second_model_samples_report.ALPHA,
        "ids.unexposed": followup_freeze.id_list_sha256(unexposed_only=True),
    }


# ---- before the approval ----------------------------------------------------------------


def problems() -> list[followup.Problem]:
    """The 121 problems in run order, with no gate: only for the checks before it exists."""
    return second_model.select(followup.read_test())


def recorded(record: Path, sample: int) -> dict[str, evaluate.Item]:
    """A record's latest single-shot items of `sample`, by problem."""
    return {i.problem_id: i for i in evaluate.latest_items(record)
            if i.condition == CONDITION and i.sample == sample}  # fmt: skip


def sent(cache: Path, request: dict, sample: int) -> dict | None:
    """The request a run sent for `sample`, as its cache stored it (api.Cache's file name)."""
    stored = cache / f"{api.cache_key(request, sample)}.json"
    return json.loads(stored.read_text())["request"] if stored.exists() else None


def requests_differ(records: list[followup.Problem] | None = None) -> list[str]:
    """Section 3: the problems whose request for samples 1 and 2 isn't the one the second-model
    study's run sent for Sonnet's sample 0, or isn't Haiku's sample 1 and 2 requests (as the
    follow-up's run sent them) but for the model. Labels only: the problem text is licensed
    data."""
    found = []
    for record in records or problems():
        haiku = formulate.build_request(record.document, second_model_samples.HAIKU_MODEL)
        sonnet = formulate.build_request(record.document, second_model_samples.MODEL)
        if sonnet != {**haiku, "model": second_model_samples.MODEL}:
            found.append(f"{record.id}: the request differs from Haiku's in more than the model")
        first = sent(SONNET_CACHE, sonnet, 0)
        if first is None or api.canonical_json(first) != api.canonical_json(sonnet):
            found.append(f"{record.id}: not the request Sonnet's sample 0 was sent")
        for sample in second_model_samples.SAMPLES:
            haikus = sent(HAIKU_CACHE, haiku, sample)
            if haikus is None or api.canonical_json(haikus) != api.canonical_json(haiku):
                found.append(f"{record.id}: Haiku's sample {sample} wasn't sent this request "
                             "but for the model")  # fmt: skip
    return found


def replay_differs(records: list[followup.Problem] | None = None,
                   sources: Sequence[tuple] = SOURCES) -> list[str]:  # fmt: skip
    """Section 3: every answer the comparison uses (Haiku's samples 0 to 2, Sonnet's sample 0:
    SOURCES, unless a test names fewer), replayed from its run's cache through this code
    (api.ReplayOnlyClient: no key, and nothing can be sent), against the recorded items: every
    field but time and payment. Empty if every answer comes back as recorded."""
    found = []
    records = records or problems()
    with tempfile.TemporaryDirectory(prefix="samples-replay-") as tmp:
        for model, record_path, cache, split, samples in sources:
            for sample in samples:
                items = recorded(record_path, sample)
                session = Run(log_path=Path(tmp) / "attempts.jsonl", cache=Cache(cache, sample))
                for record in records:
                    which = f"{record.id} ({model}, sample {sample})"
                    tags = Tags(problem_id=record.id, split=split, condition=CONDITION)
                    try:
                        item = evaluate.run_item(record, CONDITION, api.ReplayOnlyClient(),  # type: ignore[arg-type]  # it stands in for anthropic.Anthropic
                                                 session, tags, model)  # fmt: skip
                    except api.NotCached:
                        found.append(f"{which}: a call isn't in its run's cache")
                        continue
                    before = items[record.id].model_dump(mode="json")
                    if isinstance(before.get("reason"), str):
                        before["reason"] = before["reason"].replace(*REWORDED)
                    after = item.model_dump(mode="json")
                    found += [f"{which} {name}: recorded {before.get(name)!r}, replayed "
                              f"{after.get(name)!r}"
                              for name in sorted((before.keys() | after.keys()) - NOT_REPLAYED)
                              if before.get(name) != after.get(name)]  # fmt: skip
    return found


def unfinished(replay: bool = False) -> list[str]:
    """What's left before the approval, checked from the files; empty when nothing is. With
    `replay`, also replay_differs (about a minute: approve() runs it)."""
    todo = []
    if not PREREGISTRATION_PATH.exists():
        todo.append(f"{_relative(PREREGISTRATION_PATH)} is missing")
    elif "**Status: DRAFT" in PREREGISTRATION_PATH.read_text():
        todo.append(f"{_relative(PREREGISTRATION_PATH)} is still a draft")
    for path, sha in ((HAIKU_RECORD, HAIKU_RECORD_SHA256), (SONNET_RECORD, SONNET_RECORD_SHA256)):
        if _sha256(path.read_bytes()) != sha:
            todo.append(f"{_relative(path)} isn't the record section 2 names")
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
    for model, record_path, _, _, samples in SOURCES:
        for sample in samples:
            items = recorded(record_path, sample)
            if missing := [r.id for r in records
                           if r.id not in items or items[r.id].outcome != "done"]:  # fmt: skip
                todo.append(f"{model}'s record has no done sample-{sample} answer for "
                            f"{missing[:5]}")  # fmt: skip
    if differ := requests_differ(records):
        todo.append(f"these requests aren't the ones section 3 names: {differ[:5]}")
    if replay and (differ := replay_differs(records)):
        todo.append(f"recorded answers don't replay as recorded: {differ[:5]}")
    return todo


def approve(approved_by: str, today: str | None = None) -> SamplesApproval:
    """Writes FREEZE_PATH with the current fingerprint."""
    todo = unfinished(replay=True)
    if git("status", "--porcelain"):
        todo.append("the working tree has uncommitted changes: commit first, so the approved "
                    "inputs are the ones in git")  # fmt: skip
    if drifted := drifted_packages():
        todo.append(f"installed packages differ from requirements.lock: {sorted(drifted)}")
    if todo:
        raise FreezeError("not ready to freeze the samples study:\n  " + "\n  ".join(todo))
    prints = fingerprint()
    approval = SamplesApproval(
        approved_on=today or date.today().isoformat(), commit=git("rev-parse", "HEAD"),
        fingerprint=prints, analysis_sha256=prints[_relative(ANALYSIS_PATH)],
        approved_by=approved_by,
    )  # fmt: skip
    FREEZE_PATH.parent.mkdir(parents=True, exist_ok=True)
    FREEZE_PATH.write_text(approval.model_dump_json(indent=1) + "\n")
    return approval


# ---- checking ---------------------------------------------------------------------------


def approved() -> SamplesApproval | None:
    if not FREEZE_PATH.exists():
        return None
    return SamplesApproval.model_validate_json(FREEZE_PATH.read_text())


def check() -> str:
    """The approved fingerprint's digest, if the current inputs are exactly the approved ones
    and the installed packages are the locked ones; otherwise FreezeError, naming every
    difference (names only, never contents)."""
    approval = approved()
    if approval is None:
        raise FreezeError("the samples study isn't frozen: python -m "
                          "opt_agent.second_model_samples_freeze approve, after the steps it "
                          "lists")  # fmt: skip
    problems = differences(approval.fingerprint, fingerprint())
    if approval.fingerprint.get(_relative(ANALYSIS_PATH)) != approval.analysis_sha256:
        problems.append(f"{FREEZE_PATH.name}: analysis_sha256 isn't the fingerprint's")
    problems += [f"{name}: installed {installed}, locked {locked}"
                 for name, (locked, installed) in drifted_packages().items()]  # fmt: skip
    if problems:
        raise FreezeError(f"the inputs differ from the samples study's approval of "
                          f"{approval.approved_on}:\n  " + "\n  ".join(problems))  # fmt: skip
    return digest(approval.fingerprint)


def tag_problems(tag: str = FREEZE_TAG, path: Path = FREEZE_PATH) -> list[str]:
    """Does `tag` hold exactly the approval in `path`? Empty if it does (everything read from
    git's objects). The LLM4OR data is git-ignored: a copy that's here must be the approved
    one."""
    approval, problems = approval_at_tag(tag, _relative(path), path, SamplesApproval,
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
    lines = ["Left to do before the samples study's freeze:" if todo
             else "Nothing left to do before the samples study's freeze."]  # fmt: skip
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
                     "(python -m opt_agent.second_model_samples --plan first).")  # fmt: skip
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="The second-model samples study's freeze.")
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
