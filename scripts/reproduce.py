"""Rebuild every reported number from the committed runs, with each study's frozen code and
no API key, and compare with the committed files.

Each study runs in its tag's own tree (opt_agent.frozen), so nothing HEAD
changes can move a number, and nothing here writes into this checkout. Two checks per study:

1. **Replay** (skip with --no-replay): every pair of every committed run again, from the run's
   cached replies, through the frozen pipeline, with a client that refuses every request
   (scripts/replay_run.py). Every recorded field of every answer must equal the committed
   results.jsonl, except what a replay can't repeat: time (latency, retry and wall time) and
   what was paid or cached. So the committed answers are what the frozen code makes of the
   cached replies.
2. **Rebuild** the reports and results files from the committed run records, byte for byte:
   - M6 (m6-freeze): opt_agent.report for runs/test and runs/test-perturbed, Amendment 3's
     row (scripts/amendment3.py), and results/eval.json (scripts/eval_json.py, which adds
     Amendments 4 and 5);
   - the follow-up (followup-freeze): opt_agent.followup_report, then results/followup.json
     and docs/followup/RESULTS.md (scripts/followup_results.py);
   - the resampling study (resampling-freeze): results/resampling.json, the frozen
     analysis's report (opt_agent.resampling_report.build), and docs/resampling/RESULTS.md,
     both by scripts/resampling_results.py, which writes the report because the frozen
     main() can't (deviation 1, docs/resampling/DEVIATIONS.md);
   - the second-model study (second-model-freeze-2, its Amendment 1's freeze): both stages
     replayed, and results/second_model.json rebuilt by its frozen analysis (python -m
     opt_agent.second_model_report);
   - the second-model samples study (second-model-samples-freeze): Sonnet's samples 1 and 2
     replayed, and results/second_model_samples.json rebuilt by its frozen analysis (python
     -m opt_agent.second_model_samples_report), which also reads the two earlier runs' records
     (committed, so in the tag's tree).
   Each of the last two runs is the owner's; until its run directory is committed there's
   nothing to rebuild, and this says so.
   The write-up scripts were written after the freezes, against the same package, so they're
   copied in from this checkout.

Latency and cost in the reports come from the recorded runs (a replay is faster, and pays
nothing), so they're rebuilt, not replayed. Exact on macOS arm64, where all three studies ran
(CI runs it there). On Linux x86_64 (checked in CI, 2026-11-15) M6 is exact too, but in the
follow-up CBC returns another, equally optimal solution for one model, so one pair's
checklist finds no flags and skips a revision, with the same answer, and four sign-flip
p-values differ in their 16th digit (the resampling study wasn't checked there). Needs the
tags (git fetch --tags) and LLM4OR's data, which holds the follow-up's keys (the resampling
study's too) and Amendment 5's external key (python scripts/fetch_llm4or.py). Exits 1 on any
difference, printing it, or if something can't be rebuilt; 0 when everything matches.

Run:  python scripts/reproduce.py              # rebuild and replay (a few minutes)
      python scripts/reproduce.py --no-replay  # rebuild only (about 15 s)
"""

import argparse
import difflib
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

from opt_agent import (
    followup_freeze,
    resampling_freeze,
    second_model_freeze,
    second_model_samples_freeze,
)
from opt_agent.freeze import FREEZE_TAG as M6_TAG
from opt_agent.frozen import FrozenError, Tree

ROOT = Path(__file__).resolve().parents[1]
RUN_FILES = ("manifest.json", "results.jsonl", "attempts.jsonl", "spend.jsonl")
LLM4OR = "data/external/llm4or-clean"
M6_RUNS = ("runs/test", "runs/test-perturbed")
M6_OUTPUTS = ("runs/test/report.json", "runs/test-perturbed/report.json", "results/eval.json")
M6_SCRIPTS = ("amendment3", "amendment4", "amendment5", "eval_json")
FOLLOWUP_RUN = "runs/followup-test"
FOLLOWUP_OUTPUTS = (f"{FOLLOWUP_RUN}/followup_report.json", "results/followup.json",
                    "docs/followup/RESULTS.md")  # fmt: skip
RESAMPLING_RUN = "runs/resampling"
RESAMPLING_OUTPUTS = ("results/resampling.json", "docs/resampling/RESULTS.md")
SECOND_MODEL_RUN = "runs/second-model"
SECOND_MODEL_OUTPUTS = ("results/second_model.json",)
SAMPLES_RUN = "runs/second-model-samples"
SAMPLES_OUTPUTS = ("results/second_model_samples.json",)
# What a replay can't repeat: time, and what was paid or replayed (evaluate.Item).
NOT_REPLAYED = {"run_id", "latency_s", "retry_s", "wall_s", "cached_calls", "paid_usd",
                "report_only_paid_usd"}  # fmt: skip
DIFF_LINES = 40  # of each difference, printed


# ---- the studies --------------------------------------------------------------------------


def m6(workdir: Path, replay: bool) -> tuple[dict[str, bytes], list[str]]:
    """M6's three files, rebuilt in m6-freeze's tree, and the replay's differences."""
    tree = Tree.extract(M6_TAG, workdir / "m6")
    tree.copy(*(f"{run}/{name}" for run in M6_RUNS for name in RUN_FILES), LLM4OR,
              "review/blind_grading/test", "review/taxonomy/test",
              *(f"scripts/{name}.py" for name in M6_SCRIPTS))  # fmt: skip
    differences = []
    if replay:
        differences = [d for run in M6_RUNS for d in replayed(tree, run)]
    tree.python("-m", "opt_agent.report", "runs/test")
    tree.python("scripts/amendment3.py", "runs/test")  # the row a report rebuild drops
    tree.python("-m", "opt_agent.report", "runs/test-perturbed", "--original", "runs/test")
    tree.python("scripts/eval_json.py")
    return {rel: tree.read(rel) for rel in M6_OUTPUTS}, differences


def followup(workdir: Path, replay: bool) -> tuple[dict[str, bytes], list[str]]:
    """The follow-up's three files, rebuilt in followup-freeze's tree, and the replay's."""
    tree = Tree.extract(followup_freeze.FREEZE_TAG, workdir / "followup")
    tree.copy(*(f"{FOLLOWUP_RUN}/{name}" for name in RUN_FILES), LLM4OR,
              "scripts/followup_results.py")  # fmt: skip
    differences = replayed(tree, FOLLOWUP_RUN) if replay else []
    tree.python("-m", "opt_agent.followup_report", FOLLOWUP_RUN)
    tree.python("scripts/followup_results.py")
    return {rel: tree.read(rel) for rel in FOLLOWUP_OUTPUTS}, differences


def rebuild_followup(workdir: Path) -> dict[str, bytes]:
    """The follow-up's files alone, rebuilt (tests/test_followup_results.py)."""
    require_data()
    return followup(workdir, replay=False)[0]


def resampling(workdir: Path, replay: bool) -> tuple[dict[str, bytes], list[str]]:
    """The resampling study's two files, rebuilt in resampling-freeze's tree, and the replay's."""
    tree = Tree.extract(resampling_freeze.FREEZE_TAG, workdir / "resampling")
    tree.copy(*(f"{RESAMPLING_RUN}/{name}" for name in RUN_FILES), LLM4OR,
              "scripts/resampling_results.py")  # fmt: skip
    differences = replayed(tree, RESAMPLING_RUN) if replay else []
    tree.python("scripts/resampling_results.py")
    return {rel: tree.read(rel) for rel in RESAMPLING_OUTPUTS}, differences


def rebuild_resampling(workdir: Path) -> dict[str, bytes]:
    """The resampling study's files alone, rebuilt (tests/test_resampling_results.py)."""
    require_data()
    return resampling(workdir, replay=False)[0]


def second_model(
    workdir: Path,
    replay: bool,
    run: Path = ROOT / SECOND_MODEL_RUN,
    tag: str = second_model_freeze.FREEZE_TAG,
) -> tuple[dict[str, bytes], list[str]]:
    """The second-model study's results file, rebuilt in its tag's tree, and the replay's
    differences; nothing while the run isn't here. `run` and `tag` are for a test, which
    rebuilds a fake run in HEAD's tree before the tag exists."""
    return owners_run(workdir, replay, run, tag, SECOND_MODEL_RUN, "opt_agent.second_model_report",
                      SECOND_MODEL_OUTPUTS)  # fmt: skip


def second_model_samples(
    workdir: Path,
    replay: bool,
    run: Path = ROOT / SAMPLES_RUN,
    tag: str = second_model_samples_freeze.FREEZE_TAG,
) -> tuple[dict[str, bytes], list[str]]:
    """The second-model samples study's results file, rebuilt in its tag's tree, and the
    replay's differences; nothing while the run isn't here. `run` and `tag` are for a test."""
    return owners_run(workdir, replay, run, tag, SAMPLES_RUN,
                      "opt_agent.second_model_samples_report", SAMPLES_OUTPUTS)  # fmt: skip


def owners_run(workdir: Path, replay: bool, run: Path, tag: str, where: str, analysis: str,
               outputs: tuple[str, ...]) -> tuple[dict[str, bytes], list[str]]:  # fmt: skip
    """A study whose run the owner commits after its tag: `run` copied to `where` in the tag's
    tree, replayed there (scripts/replay_run.py), and its frozen `analysis` module run, which
    writes `outputs`. Nothing while the run isn't here."""
    if not (run / "results.jsonl").exists():
        return {}, []
    tree = Tree.extract(tag, workdir / Path(where).name)
    tree.copy(LLM4OR)
    target = tree.root / where
    target.mkdir(parents=True, exist_ok=True)
    for name in RUN_FILES:  # a run the cap stopped early still has them all but the ledger
        if (run / name).exists():
            shutil.copy2(run / name, target / name)
    differences = []
    if replay:
        shutil.copytree(run / "cache", target / "cache", dirs_exist_ok=True)
        tree.copy("scripts/replay_run.py")
        out = f"replay/{Path(where).name}"
        tree.python("scripts/replay_run.py", where, out)
        differences = item_differences(run / "results.jsonl", tree.root / out / "results.jsonl",
                                       where)  # fmt: skip
    tree.python("-m", analysis, where)
    return {rel: tree.read(rel) for rel in outputs}, differences


# ---- the replay ---------------------------------------------------------------------------


def replayed(tree: Tree, run: str) -> list[str]:
    """Replay `run` in `tree` from its committed cache, and compare every answer."""
    tree.copy(f"{run}/cache", "scripts/replay_run.py")
    out = f"replay/{Path(run).name}"
    tree.python("scripts/replay_run.py", run, out)
    return item_differences(ROOT / run / "results.jsonl", tree.root / out / "results.jsonl",
                            run)  # fmt: skip


def latest_items(path: Path) -> dict[tuple, dict]:
    """Each pair's last item line, as evaluate.latest_items picks it (a resume's line
    replaces an earlier one), keyed by problem, condition and sample."""
    items = {}
    for line in path.read_text().splitlines():
        entry = json.loads(line)
        if entry.get("kind") == "item":
            items[entry["problem_id"], entry["condition"], entry.get("sample", 0)] = entry
    return items


def item_differences(committed: Path, replay: Path, run: str) -> list[str]:
    before, after = latest_items(committed), latest_items(replay)
    found = [f"{run}: pair {key} is only in the {where}" for key, where in
             [(k, "committed run") for k in before.keys() - after.keys()]
             + [(k, "replay") for k in after.keys() - before.keys()]]  # fmt: skip
    for key in sorted(before.keys() & after.keys()):
        for name in sorted((before[key].keys() | after[key].keys()) - NOT_REPLAYED):
            if before[key].get(name) != after[key].get(name):
                found.append(f"{run}: {key} {name}: committed {before[key].get(name)!r}, "
                             f"replayed {after[key].get(name)!r}")  # fmt: skip
    return found


# ---- comparing ------------------------------------------------------------------------------


def require_data() -> None:
    if (
        not all(p.exists() for p in followup_freeze.data_files())
        or not (ROOT / LLM4OR / "NL4Opt").is_dir()
    ):
        raise FrozenError(f"needs LLM4OR's data in {LLM4OR} (the follow-up's keys and "
                          "Amendment 5's): python scripts/fetch_llm4or.py")  # fmt: skip


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
    parser.add_argument("--no-replay", action="store_true", help="rebuild only (fast)")
    args = parser.parse_args(argv)
    replay = not args.no_replay
    failures, rebuilt = [], {}
    with tempfile.TemporaryDirectory(prefix="reproduce-") as workdir:
        try:
            require_data()
            studies = (("M6", m6, None), ("follow-up", followup, None),
                       ("resampling", resampling, None),
                       ("second model", second_model, SECOND_MODEL_RUN),
                       ("second model, samples 1 and 2", second_model_samples,
                        SAMPLES_RUN))  # fmt: skip
            for name, study, run in studies:
                start = time.monotonic()
                files, replay_differences = study(Path(workdir), replay)
                if not files:
                    print(f"{name}: not run yet ({run} isn't here), nothing to rebuild")
                    continue
                rebuilt |= files
                failures += replay_differences
                what = "replayed and rebuilt" if replay else "rebuilt"
                print(f"{name}: {what} in {time.monotonic() - start:.0f} s")
        except FrozenError as error:
            sys.exit(f"CAN'T REBUILD: {error}")
    failures += differences(rebuilt)
    for rel in rebuilt:
        print(f"{'DIFFERS' if any(f.startswith(f'DIFFERS: {rel}') for f in failures) else 'same'}"
              f"  {rel}")  # fmt: skip
    if failures:
        print("\n\n".join(failures[:50]))
        sys.exit(f"{len(failures)} difference(s): the committed results don't reproduce")
    replays = "every committed answer replays from the cache, and " if replay else ""
    print(f"Reproduced: {replays}all {len(rebuilt)} files rebuild byte for byte.")


if __name__ == "__main__":
    main()
