"""A run directory read back: every (problem, condition) pair, scored, and the model behind
each answer.

report.py summarizes a run from this; the hand-check packets (blind_grading.py,
taxonomy.py) need the same pairs and also the models, which only the attempt log has.

Each (problem, condition) pair in the manifest is, following Amendment 1:
- **scored**: done in some pass, or errored in the first pass and in each of the
  RESUME_PASSES after it. The second counts as wrong (loud, "api error").
- **open**: errored in fewer passes, or pending (no line yet).
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from opt_agent.api import canonical_json
from opt_agent.evaluate import Item, Manifest
from opt_agent.formulate import parse_reply
from opt_agent.ground_truth import GROUND_TRUTH_DIR, Record, load_records
from opt_agent.schema import LPModel
from opt_agent.scoring import Score, score

RESUME_PASSES = 3  # Amendment 1: after the first pass and 3 resumes, an error counts as wrong


class Pair(BaseModel):
    problem_id: str
    condition: str
    state: Literal["scored", "errored", "pending"]  # errored and pending are open
    item: Item | None = None  # the done line, else the last errored one
    errored_passes: int = 0  # a pass writes at most one line per pair
    score: Score | None = None  # scored pairs only
    retry_s: float = 0.0  # over every pass, errored ones included
    wall_s: float = 0.0  # likewise

    @property
    def no_answer(self) -> str | None:
        if self.state != "scored" or self.score.correct or self.score.failure != "loud":
            return None
        return self.item.no_answer if self.item.outcome == "done" else "api error"


@dataclass
class ScoredRun:
    directory: Path
    manifest: Manifest
    by_id: dict[str, Record]  # every record in the split
    pairs: list[Pair]

    @property
    def name(self) -> str:
        """The run directory's name, which also names its hand-check packets in review/."""
        return self.directory.name

    @property
    def records(self) -> list[Record]:
        """The run's problems, in manifest order."""
        return [self.by_id[i] for i in self.manifest.problem_ids]


def load(run_dir: Path) -> ScoredRun:
    manifest = Manifest.model_validate_json((run_dir / "manifest.json").read_text())
    by_id = {r.id: r for r in load_records(GROUND_TRUTH_DIR / f"{manifest.split}.json")}
    pairs = load_pairs(manifest, run_dir / "results.jsonl", by_id)
    return ScoredRun(directory=run_dir, manifest=manifest, by_id=by_id, pairs=pairs)


def load_pairs(manifest: Manifest, results: Path, by_id: dict[str, Record]) -> list[Pair]:
    lines: dict[tuple[str, str], list[Item]] = {}
    for line in results.read_text().splitlines() if results.exists() else []:
        entry = json.loads(line)
        if entry["kind"] == "item":
            item = Item.model_validate(entry)
            lines.setdefault((item.problem_id, item.condition), []).append(item)
    pairs = []
    for problem_id in manifest.problem_ids:
        for condition in manifest.conditions:
            items = lines.get((problem_id, condition), [])
            done = [i for i in items if i.outcome == "done"]
            errored = [i for i in items if i.outcome == "errored"]
            pair = Pair(problem_id=problem_id, condition=condition, state="pending",
                        errored_passes=len(errored), retry_s=sum(i.retry_s for i in items),
                        wall_s=sum(i.wall_s for i in items))  # fmt: skip
            if done:
                record = by_id[problem_id]
                item = done[-1]
                pair = pair.model_copy(update={"state": "scored", "item": item,
                                               "score": score(record, item.status,
                                                              item.objective)})  # fmt: skip
            elif len(errored) >= 1 + RESUME_PASSES:
                pair = pair.model_copy(update={"state": "scored", "item": errored[-1],
                                               "score": Score(correct=False,
                                                              failure="loud")})  # fmt: skip
            elif errored:
                pair = pair.model_copy(update={"state": "errored", "item": errored[-1]})
            pairs.append(pair)
    return pairs


def final_models(run_dir: Path) -> dict[tuple[str, str, str], LPModel]:
    """(problem id, condition, pass) -> the model the answer came from: as in
    self_correct.Outcome.final, the last attempt in that pass that gave a usable model.
    Read back from the replies in the attempt log, parsed as formulate does."""
    models: dict[tuple[str, str, str], LPModel] = {}
    log = run_dir / "attempts.jsonl"
    for line in log.read_text().splitlines() if log.exists() else []:
        entry = json.loads(line)
        if entry["kind"] != "attempt":
            continue
        model, _ = parse_reply(entry["reply"], entry["stop_reason"])
        if model is not None:
            models[(entry["problem_id"], entry["condition"], entry["run_id"])] = model
    return models


def model_of(pair: Pair, models: dict[tuple[str, str, str], LPModel]) -> LPModel:
    """The model behind a scored pair's confirmed answer (single-shot, self-correction)."""
    return models[(pair.problem_id, pair.condition, pair.item.run_id)]


# The hand-check sheets name their rows by these keys, not by position, so a regenerated
# packet keeps what the owner wrote, and a key shows nothing a grader could look up. The
# same model of the same problem gets the same key in every packet.


def model_key(problem_id: str, model: LPModel) -> str:
    return _key({"problem": problem_id, "model": model.model_dump(mode="json")})


def answer_key(problem_id: str, status: str | None, objective: float | None) -> str:
    """For a baseline answer, which has no model. As a float, 250 and 250.0 are one key."""
    value = None if objective is None else float(objective)
    return _key({"problem": problem_id, "answer": [status, value]})


def _key(what: dict) -> str:
    return hashlib.sha256(canonical_json(what).encode()).hexdigest()[:12]
