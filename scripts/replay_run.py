"""Replay a committed run from its cache: every pair again, through the code of the tree this
runs in, with a client that refuses every request. scripts/reproduce.py copies it into a
study's tag tree (opt_agent.frozen) and runs it there, so the code is the frozen code; it
then compares the new results.jsonl with the committed one.

For M6's and the follow-up's runs it uses only what both their tags have:
evaluate.scorable_records, evaluate.evaluate, and the manifest's split, problems, conditions,
model and samples. The resampling study's run (split "resampling", resampling-freeze) has its
own runner, so it replays through that: resampling.run, which reads the problems only on the
frozen inputs and runs every cell through evaluate.run_item. Either way the committed manifest
goes into the new run directory first, so the runner refuses anything but the same
experiment. A request that isn't in the cache raises NotInCache: nothing here can reach the
API.

Run (inside a tag's tree):  python scripts/replay_run.py runs/test replay/test
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

from opt_agent import evaluate


class NotInCache(Exception):
    """Not an anthropic.APIError, so the pipeline can't treat it as a failed call."""


class RefusingClient:
    def __init__(self):
        self.messages = self  # so that client.messages.create(...) works

    def with_options(self, **options) -> "RefusingClient":
        return self

    def create(self, **request):
        # Which call missed, without the problem's text (licensed data; CI logs are shared).
        sha = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
        raise NotInCache(f"a request wasn't in the run's cache ({len(request['messages'])} "
                         f"message(s); system prompt {request['system'][:48]!r}...; "
                         f"sha256 {sha[:12]}): a replay never calls the API")  # fmt: skip


def replay(run: Path, out: Path) -> None:
    manifest = json.loads((run / "manifest.json").read_text())
    out.mkdir(parents=True)
    shutil.copy(run / "manifest.json", out / "manifest.json")
    shutil.copytree(run / "cache", out / "cache")
    try:
        if manifest["split"] == "resampling":
            from opt_agent import resampling  # only resampling-freeze's tree has it

            resampling.run(RefusingClient(), out)  # type: ignore[arg-type]
        else:
            run_evaluate(manifest, out)
    except NotInCache as miss:
        results = out / "results.jsonl"
        done = len(results.read_text().splitlines()) if results.exists() else 0
        raise SystemExit(f"{run}: the replay stopped after {done} pairs: {miss}") from None


def run_evaluate(manifest: dict, out: Path) -> None:
    split, ids = manifest["split"], manifest["problem_ids"]
    records = [r for r in evaluate.scorable_records(split) if r.id in set(ids)]
    if sorted(r.id for r in records) != sorted(ids):
        raise SystemExit(f"{split}: the scorable problems aren't the manifest's")
    samples = manifest["settings"].get("samples")  # only a run of several samples records it
    more = {"sample": tuple(int(s) for s in samples.split(","))} if samples else {}
    evaluate.evaluate(records, tuple(manifest["conditions"]), RefusingClient(), out, split,
                      manifest["model_id"], **more)  # fmt: skip


if __name__ == "__main__":
    replay(Path(sys.argv[1]), Path(sys.argv[2]))
