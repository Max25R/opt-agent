"""Run problems through the evaluation's conditions: resumable, and within a dollar cap.

The conditions (docs/PREREGISTRATION.md, section 2): "baseline" (Claude answers directly,
no solver), "single-shot" (one formulation, solved and checked) and "self-correction" (up
to 3 attempts). Self-correction's first request is byte-identical to single-shot's, so it
replays from the run's cache: the two are paired on the same first replies, paid once.

Each (problem, condition) pair becomes one "item" line in results.jsonl, recording what
the condition answered, never whether that's right: report.py scores the answers against
the ground truth afterwards (scoring.py), so a corrected review never needs a paid re-run.
- **done**: the answer (a confirmed status and objective; for the baseline, a parsed one),
  or no answer and the kind of failure (`no_answer`: an unusable reply, solvers
  disagreeing, a solver time-out, ...).
- **errored**: an API error outlasted every retry (api.call). That isn't Claude's
  failure, so a resumed run tries the pair again (pre-registration, Amendment 1). Each
  line names its pass (`run_id`), so the report can count how many passes a pair needed.

A run directory is one experiment: manifest.json, written by the first pass, fixes its
split, problems, conditions, model, and request settings, and a resume with any of them
changed is refused. The manifest is also the report's denominator: a pair with no line yet
is pending, never silently missing.

The run stops cleanly, with a "stopped" line, when the budget's next call could exceed the
cap (budget.py), when the account reaches its spend limit, or after MAX_ERRORS_IN_A_ROW
errored pairs. Re-running the same command resumes it: done pairs are skipped, and every
call that already succeeded replays from the run's cache, so nothing is paid for twice.
The cap counts what earlier runs in the same directory spent (its spend.jsonl).

The test splits (test, test-perturbed) run only on frozen inputs (freeze.py): every pass
first checks the fingerprint against the owner's approval and refuses on any difference.
A test run is the whole pre-registered experiment, every scorable problem in every
condition, so it takes --all and no subset. Every pass records its fingerprint's digest.

Report-only extras (M7, audit finding 2): with --estimate and --checklist, the solver
conditions also record agent.run's low-confidence flag and checklist flags, with their calls'
cost apart (report_only_*). They change no answer. The manifest records them, so a resume
with different extras is refused. The follow-up dev split (complexlp-dev, followup.py) runs
too; its answers are compared with the benchmark's at 1e-4.

The follow-up test run (`--split followup-test`, followup.TEST_SPLIT) holds both sealed
benchmarks in one directory, each problem named by its label ("complexlp:1",
"industryor:1"): results, resumes, the manifest and the run order all use the labels. Its
problems load only on the follow-up's frozen inputs (followup_freeze.check), so even --plan
needs the owner's approval, and it is the whole experiment: every scorable problem (a key
that can't be parsed is left out by format alone), all four conditions, samples 0, 1, 2.

Run:  python -m opt_agent.evaluate --out runs/smoke --cap 1.00 ID [ID ...]
      python -m opt_agent.evaluate --out runs/dev --cap 0.50 --all
      (add --plan to see the pending pairs and the worst-case cost without calling; a plan
      needs no freeze, even for a test split)
"""

import argparse
import json
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import anthropic
from pydantic import BaseModel

from opt_agent import agent, api, baseline, feedback, followup, formulate, freeze, pricing
from opt_agent import checklist as formulation_checklist
from opt_agent.api import Cache, RunStopped
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.config import MissingAPIKeyError, get_api_key
from opt_agent.ground_truth import GROUND_TRUTH_DIR, Record, load_records
from opt_agent.ground_truth import scorable as is_scorable
from opt_agent.runs import Run, Tags
from opt_agent.scoring import score
from opt_agent.self_correct import MAX_ATTEMPTS
from opt_agent.solver import Status

Condition = Literal["baseline", "single-shot", "self-correction", "checklist-revision"]
CONDITIONS: tuple[Condition, ...] = ("baseline", "single-shot", "self-correction")  # M6's
# The follow-up's four (docs/FOLLOWUP_PREREGISTRATION.md, section 3): M6's, and
# single-shot with one checklist-triggered revision (agent.run(checklist_revision=True)).
FOLLOWUP_CONDITIONS: tuple[Condition, ...] = (*CONDITIONS, "checklist-revision")
ATTEMPTS = {"single-shot": 1, "self-correction": MAX_ATTEMPTS, "checklist-revision": 1}
MAX_ERRORS_IN_A_ROW = 3  # the API is down or the limits are too low: stop, resume later
DEV_SPLITS = ["dev", "dev-perturbed"]
FOLLOWUP_DEV_SPLITS = sorted(followup.DEV_SPLITS)  # the follow-up's dev; its test is sealed
TEST_SPLITS = ["test", "test-perturbed"]  # frozen inputs only (freeze.py)
FOLLOWUP_TEST = followup.TEST_SPLIT  # the follow-up's frozen inputs only (followup_freeze.py)
FOLLOWUP_SAMPLES = (0, 1, 2)  # follow-up pre-registration, section 3

# Why a done pair has no answer: the loud failures of pre-registration section 3g. (An API
# error is an errored pair instead; only the report turns one into a failure.)
NoAnswer = Literal[
    "unusable reply", "refusal", "solvers disagree", "solver time-out", "solver error",
    "failed check",
]  # fmt: skip


class Item(BaseModel):
    """One (problem, condition) pair in one pass: what the condition answered."""

    kind: Literal["item"] = "item"
    problem_id: str
    split: str
    condition: Condition
    outcome: Literal["done", "errored"]
    run_id: str | None = None  # the pass that wrote this line (runs.Run)
    sample: int = 0  # which repeated sample of the pair (Cache(dir, sample))
    model_id: str
    settings_sha256: str  # the condition's request template: prompt, schema, settings
    status: str | None = None  # the system's answer; None if there's no confirmed one
    objective: float | None = None
    no_answer: NoAnswer | None = None  # why a done pair has no answer
    reason: str | None = None  # in words: why the loop stopped, or the error
    flags: list[str] = []  # revisions that deleted or loosened something (changes.py)
    dropped: list[str] = []  # unused variables the answer's model had dropped (a note)
    # checklist-revision only: whether a revision was made, kept, and why (or why not)
    revised: bool | None = None
    revision_kept: bool | None = None
    revision_reason: str | None = None
    original_status: str | None = None  # the single-shot answer a revision started from
    original_objective: float | None = None
    attempts: int = 0
    cached_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0  # includes thinking
    cost_usd: float = 0.0  # every call the answer used, at its original token counts
    paid_usd: float = 0.0  # only the calls this run paid for (not replayed from the cache)
    latency_s: float = 0.0  # API plus solver time, without retries
    retry_s: float = 0.0  # failed tries and the waits after them
    wall_s: float = 0.0  # as measured in this pass; shorter when calls replay from the cache
    # Report-only extras (--estimate, --checklist): never part of the answer or its cost.
    estimate_status: str | None = None
    estimate_objective: float | None = None
    low_confidence: bool | None = None
    low_confidence_reason: str | None = None
    checklist_flags: list[dict] | None = None
    checklist_notes: list[str] = []
    report_only_cost_usd: float = 0.0  # the estimate's and the checklist's calls
    report_only_paid_usd: float = 0.0


class Manifest(BaseModel):
    """What a run directory is an experiment of. Fixed by its first pass."""

    split: str
    problem_ids: list[str]
    conditions: list[Condition]
    model_id: str
    settings: dict[str, str]  # condition -> settings_sha256


def manifest_for(
    split: str,
    records: list[Record],
    conditions: tuple[Condition, ...],
    model_id: str,
    extras: tuple[str, ...] = (),
    samples: tuple[int, ...] = (0,),
) -> Manifest:
    """`extras`: "estimate" and/or "checklist", recorded with their request settings.
    `samples`: the repeated samples the run directory holds. Sample 0 alone isn't recorded,
    and one other sample is recorded as before, so older manifests still match."""
    settings = {c: settings_sha256(c, model_id) for c in conditions}
    settings |= {extra: extra_settings_sha256(extra, model_id) for extra in extras}
    if len(samples) > 1:
        settings["samples"] = ",".join(map(str, samples))
    elif samples != (0,):
        settings["sample"] = str(samples[0])
    return Manifest(split=split, problem_ids=[r.id for r in records],
                    conditions=list(conditions), model_id=model_id, settings=settings)  # fmt: skip


def fix_manifest(out: Path, manifest: Manifest) -> None:
    """Write the manifest on the first pass; afterwards, refuse a pass that differs."""
    path = out / "manifest.json"
    if not path.exists():
        out.mkdir(parents=True, exist_ok=True)
        path.write_text(manifest.model_dump_json(indent=1) + "\n")
        return
    fixed = Manifest.model_validate_json(path.read_text())
    if fixed != manifest:
        changed = [k for k in Manifest.model_fields if getattr(fixed, k) != getattr(manifest, k)]
        raise ValueError(
            f"{path} was made with different {', '.join(changed)}; a resume must repeat the "
            "same experiment, so start a new run directory instead"
        )


def extra_settings_sha256(extra: str, model_id: str) -> str:
    if extra == "estimate":
        template = baseline.build_request("", model_id)
    else:
        template = formulation_checklist.build_request("", [], model_id)
    return api.request_sha256(template)[:12]


def settings_sha256(condition: Condition, model_id: str) -> str:
    """Changes whenever the condition's prompt, schema, or pinned settings change, so
    results from different versions can't be mixed in one run directory."""
    template = (baseline if condition == "baseline" else formulate).build_request("", model_id)
    if condition == "checklist-revision":  # its checklist and feedback decide answers too
        template = {"formulate": template,
                    "checklist": formulation_checklist.build_request("", [], model_id),
                    "feedback": [feedback.CHECKLIST_INTRO, feedback.CHECKLIST_OUTRO]}  # fmt: skip
    return api.request_sha256(template)[:12]


def evaluate(
    records: list[Record],
    conditions: tuple[Condition, ...],
    client: anthropic.Anthropic,
    out: Path,
    split: str = "dev",
    model_id: str = formulate.DEFAULT_MODEL,
    extras: tuple[str, ...] = (),
    sample: int | tuple[int, ...] = 0,
) -> list[Item]:
    """Every pending pair, in order; returns the items this call added. Raises RunStopped
    (after writing a "stopped" line) when the run has to stop. On a test split, raises
    FreezeError (before writing anything) unless the inputs are the approved ones, and
    ValueError unless it's the whole experiment.

    `sample`: one sample, or several, all in this directory under one cap. Each problem
    runs every sample in every condition before the next problem starts, so a stopped run
    leaves whole problems. A follow-up split runs in its pre-registered order
    (followup.in_run_order); NL4Opt splits keep file order, as M6 ran them."""
    samples = (sample,) if isinstance(sample, int) else tuple(sample)
    if split in FOLLOWUP_DEV_SPLITS or split == FOLLOWUP_TEST:
        records = followup.in_run_order(split, records)
    if split in TEST_SPLITS:
        prints = freeze.check()
        require_whole_experiment(split, records, conditions)
    elif split == FOLLOWUP_TEST:
        from opt_agent import (
            followup_freeze,  # here: it imports followup_report, which imports this
        )

        prints = followup_freeze.check()
        require_whole_followup(records, conditions, samples)
    else:
        prints = freeze.digest(freeze.fingerprint())
    fix_manifest(out, manifest_for(split, records, conditions, model_id, extras, samples))
    results = out / "results.jsonl"
    done = done_pairs(results, model_id)
    first = Run.start(log_path=out / "attempts.jsonl", cache=Cache(out / "cache", samples[0]),
                      fingerprint=prints)  # fmt: skip
    # One pass, one run_id and one log; each sample reads and writes its own cache entries.
    sessions = {s: replace(first, cache=Cache(out / "cache", s)) for s in samples}
    added: list[Item] = []
    errors_in_a_row = 0
    try:
        for record in records:
            for s in samples:
                for condition in conditions:
                    if (record.id, condition, s) in done:
                        continue
                    tags = Tags(problem_id=record.id, split=split, condition=condition)
                    item = run_item(record, condition, client, sessions[s], tags, model_id,
                                    extras)  # fmt: skip
                    _append(results, item.model_dump(mode="json"))
                    added.append(item)
                    errors_in_a_row = errors_in_a_row + 1 if item.outcome == "errored" else 0
                    if errors_in_a_row >= MAX_ERRORS_IN_A_ROW:
                        raise RunStopped(f"{errors_in_a_row} API errors in a row: {item.reason}")
    except RunStopped as stop:
        _append(results, {"kind": "stopped", "time": _now(), "reason": str(stop)})
        raise
    return added


def require_whole_experiment(
    split: str, records: list[Record], conditions: tuple[Condition, ...]
) -> None:
    """A test run is the pre-registered experiment: every scorable problem in the split, in
    file order, in every condition. A subset would be another experiment."""
    expected = scorable_records(split)
    if [r.id for r in records] != [r.id for r in expected]:
        raise ValueError(f"a {split} run covers all {len(expected)} scorable problems (--all)")
    if tuple(conditions) != CONDITIONS:
        raise ValueError(f"a {split} run covers every condition: {', '.join(CONDITIONS)}")


def require_whole_followup(
    records: list[Record], conditions: tuple[Condition, ...], samples: tuple[int, ...]
) -> None:
    """The follow-up test run is its pre-registered experiment: every scorable problem, in
    the pre-registered order, in all four conditions, with samples 0, 1 and 2."""
    expected = followup.in_run_order(FOLLOWUP_TEST, scorable_records(FOLLOWUP_TEST))
    if [r.id for r in records] != [r.id for r in expected]:
        raise ValueError(f"a {FOLLOWUP_TEST} run covers all {len(expected)} scorable problems, "
                         "in the pre-registered order (--all)")  # fmt: skip
    if tuple(conditions) != FOLLOWUP_CONDITIONS:
        raise ValueError(f"a {FOLLOWUP_TEST} run covers every condition: "
                         f"{', '.join(FOLLOWUP_CONDITIONS)}")  # fmt: skip
    if tuple(samples) != FOLLOWUP_SAMPLES:
        raise ValueError(f"a {FOLLOWUP_TEST} run holds samples 0 1 2 (--sample 0 1 2)")


def followup_problems(split: str) -> list[followup.Problem]:
    """Every problem of a follow-up split, scorable or not (the test split only on frozen
    inputs: FreezeError otherwise)."""
    return followup.load_test() if split == FOLLOWUP_TEST else followup.load(split)


def scorable_records(split: str) -> list[Record]:
    if split in FOLLOWUP_DEV_SPLITS or split == FOLLOWUP_TEST:
        # a key that can't be parsed leaves its problem out, by format alone (section 4)
        return [p for p in followup_problems(split) if p.scorable]
    return [r for r in load_records(GROUND_TRUTH_DIR / f"{split}.json") if is_scorable(r)]


def _correct(record, item: Item) -> bool:
    if isinstance(record, followup.Problem):
        return followup.is_correct(record, item.status, item.objective)
    return score(record, item.status, item.objective).correct


def run_item(
    record: Record,
    condition: Condition,
    client: anthropic.Anthropic,
    session: Run,
    tags: Tags,
    model_id: str,
    extras: tuple[str, ...] = (),
) -> Item:
    base = {
        "problem_id": record.id,
        "split": tags.split,
        "condition": condition,
        "run_id": session.run_id,
        "sample": session.cache.sample if session.cache else 0,
        "model_id": model_id,
        "settings_sha256": settings_sha256(condition, model_id),
    }
    if condition == "baseline":
        return _baseline_item(record, client, session, tags, model_id, base)
    return _solver_item(record, condition, client, session, tags, model_id, base, extras)


def _baseline_item(
    record: Record,
    client: anthropic.Anthropic,
    session: Run,
    tags: Tags,
    model_id: str,
    base: dict,
) -> Item:
    start = time.perf_counter()
    a = baseline.answer_directly(record.document, client, model_id, session.cache)
    wall = time.perf_counter() - start
    session.write("baseline", tags, model_id=model_id, request_sha256=a.call.request_sha256,
                  request=a.request, reply=a.raw_text, stop_reason=a.stop_reason,
                  usage=a.usage.model_dump(), call=a.call.model_dump(), error=a.error,
                  status=a.status, objective=a.objective)  # fmt: skip
    cost = pricing.cost_usd(a.usage, model_id)
    spend = {"attempts": 1, "cached_calls": int(a.call.cached),
             "input_tokens": a.usage.input_tokens, "output_tokens": a.usage.output_tokens,
             "cost_usd": cost, "paid_usd": 0.0 if a.call.cached else cost,
             "latency_s": a.call.latency_s, "retry_s": a.call.retry_s, "wall_s": wall}  # fmt: skip
    if a.api_failed:
        return Item(**base, **spend, outcome="errored", reason=a.call.error)
    no_answer = None
    if a.status is None:
        no_answer = "refusal" if a.stop_reason == "refusal" else "unusable reply"
    return Item(**base, **spend, outcome="done", status=a.status, objective=a.objective,
                no_answer=no_answer, reason=a.error)  # fmt: skip


def _solver_item(
    record: Record,
    condition: Condition,
    client: anthropic.Anthropic,
    session: Run,
    tags: Tags,
    model_id: str,
    base: dict,
    extras: tuple[str, ...] = (),
) -> Item:
    revising = condition == "checklist-revision"
    result = agent.run(record.document, client, model_id, with_explanation=False,
                       max_attempts=ATTEMPTS[condition], session=session, tags=tags,
                       estimate="estimate" in extras, checklist="checklist" in extras,
                       checklist_revision=revising)  # fmt: skip
    # Every call the answer used: for checklist-revision that includes its checklist.
    calls = list(result.formulations)
    if revising and result.checklist is not None:
        calls.append(result.checklist)
    formulations = calls
    costs = [pricing.cost_usd(f.usage, f.model_id) for f in formulations]
    spend = {
        "attempts": len(result.formulations),  # formulation attempts, not the checklist
        "cached_calls": sum(f.call.cached for f in formulations),
        "input_tokens": sum(f.usage.input_tokens for f in formulations),
        "output_tokens": sum(f.usage.output_tokens for f in formulations),
        "cost_usd": sum(costs),
        "paid_usd": sum(c for c, f in zip(costs, formulations, strict=True) if not f.call.cached),
        "latency_s": result.latency_s,
        "retry_s": result.retry_s,
        "wall_s": result.wall_s,
    }
    if result.api_error is not None:
        return Item(**base, **spend, outcome="errored", reason=result.api_error)
    s = result.solution
    status, objective = (s.status, s.objective) if result.confirmed else (None, None)
    revision = {}
    if revising:
        revision = {"revised": result.checklist_revision is not None,
                    "revision_kept": result.revision_kept,
                    "revision_reason": result.revision_reason}  # fmt: skip
        if revision["revised"]:  # it started from a confirmed optimum: record it
            first = result.outcome.attempts[0].solution
            revision |= {"original_status": first.status, "original_objective": first.objective}
    return Item(**base, **spend, **_report_only(result, revising), **revision, outcome="done",
                status=status, objective=objective, no_answer=_no_answer(result),
                reason=_reason(result), flags=result.outcome.flags,
                dropped=result.formulation.dropped)  # fmt: skip


def _report_only(result: agent.Result, checklist_decides: bool = False) -> dict:
    """The estimate's and the checklist's outcome and cost: recorded, never scored. With
    `checklist_decides` (checklist-revision) the checklist is part of the answer, so its
    flags are recorded here but its cost is the answer's, not report-only."""
    report_only = (result.estimate,) if checklist_decides else (result.estimate, result.checklist)
    calls = [x for x in report_only if x is not None]
    costs = [pricing.cost_usd(x.usage, x.model_id) for x in calls]
    e = result.estimate
    return {
        "estimate_status": e.status if e else None,
        "estimate_objective": e.objective if e else None,
        "low_confidence": result.low_confidence,
        "low_confidence_reason": result.low_confidence_reason,
        "checklist_flags": None if result.checklist_flags is None
        else [f.model_dump() for f in result.checklist_flags],
        "checklist_notes": result.checklist_notes,
        "report_only_cost_usd": sum(costs),
        "report_only_paid_usd": sum(c for c, x in zip(costs, calls, strict=True)
                                    if not x.call.cached),
    }  # fmt: skip


def _no_answer(result: agent.Result) -> NoAnswer | None:
    if result.confirmed:
        return None
    if result.solution is None:
        return "refusal" if result.outcome.stopped == "refused" else "unusable reply"
    for s in (result.solution, result.highs_solution):
        if s is not None and s.failed:
            return "solver time-out" if s.status is Status.TIMEOUT else "solver error"
    return "solvers disagree" if result.highs_agrees is False else "failed check"


def _reason(result: agent.Result) -> str:
    stopped = result.outcome.stopped
    if result.confirmed:
        return stopped
    if result.solution is None:
        return f"{stopped}; no usable model: {result.formulation.error}"
    if result.solution.failed or (result.highs_solution and result.highs_solution.failed):
        return f"{stopped}; a solver timed out or failed"
    if result.highs_agrees is False:
        return f"{stopped}; CBC and HiGHS disagree"
    return f"{stopped}; failed checks: {'; '.join(result.check_problems)}"


# ---- resuming ---------------------------------------------------------------------------


def done_pairs(results: Path, model_id: str) -> set[tuple[str, str, int]]:
    """The (problem, condition, sample) pairs already done. A later line for a pair replaces
    an earlier one (errored, then done on resume)."""
    if not results.exists():
        return set()
    latest: dict[tuple[str, str, int], dict] = {}
    for line in results.read_text().splitlines():
        entry = json.loads(line)
        if entry["kind"] == "item":
            latest[(entry["problem_id"], entry["condition"], entry.get("sample", 0))] = entry
    for (problem_id, condition, _), entry in latest.items():
        expected = settings_sha256(condition, model_id)
        if (entry["model_id"], entry["settings_sha256"]) != (model_id, expected):
            raise ValueError(
                f"{results} has {condition} results for {problem_id} from another model or "
                f"prompt version ({entry['model_id']}, {entry['settings_sha256']}); start a "
                "new run directory instead of mixing them"
            )
    return {pair for pair, entry in latest.items() if entry["outcome"] == "done"}


def latest_items(results: Path) -> list[Item]:
    latest: dict[tuple[str, str, int], Item] = {}
    for line in results.read_text().splitlines() if results.exists() else []:
        entry = json.loads(line)
        if entry["kind"] == "item":
            item = Item.model_validate(entry)
            latest[(item.problem_id, item.condition, item.sample)] = item
    return list(latest.values())


def _append(path: Path, entry: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


# ---- planning and reporting -------------------------------------------------------------


# The checklist's request names the model's variables, unknown before the run: plan for many
# long names, so the bound stays a bound.
PLANNED_NAMES = ["a_long_variable_name_for_the_worst_case"] * 30


def worst_case_plan(
    records: list[Record],
    conditions: tuple[Condition, ...],
    done: set,
    model_id: str,
    extras: tuple[str, ...] = (),
    samples: tuple[int, ...] = (0,),
) -> tuple[int, float]:
    """(most paid calls, most they can cost) for the pending pairs, if every reply used
    all of max_tokens. Self-correction's and checklist-revision's first call is free when
    single-shot runs too. Each extra (estimate, checklist) is one more call per solver pair,
    counted as paid; checklist-revision adds its checklist and one revision, and takes no
    checklist extra (its own checklist is the same call)."""
    calls, usd = 0, 0.0
    # A revision carries the previous reply (at most max_tokens) and feedback on top.
    revision_extra = pricing.prices_for(model_id, 0).input * (api.MAX_TOKENS + 2_000) / 1e6
    pending = [(r, c) for r in records for s in samples for c in conditions
               if (r.id, c, s) not in done]  # fmt: skip
    for record, condition in pending:
        module = baseline if condition == "baseline" else formulate
        first = pricing.worst_case_usd(module.build_request(record.document, model_id))
        if condition == "baseline":
            calls, usd = calls + 1, usd + first
            continue
        replayed = condition != "single-shot" and "single-shot" in conditions
        paid_first = 0 if replayed else 1
        revisions = ATTEMPTS[condition] - 1
        calls += paid_first + revisions
        usd += paid_first * first + revisions * (first + revision_extra)
        if condition == "checklist-revision":
            checklist = _extra_request("checklist", record.document, model_id)
            calls += 2
            usd += pricing.worst_case_usd(checklist) + first + revision_extra
        for extra in extras:
            if extra == "checklist" and condition == "checklist-revision":
                continue
            request = _extra_request(extra, record.document, model_id)
            calls, usd = calls + 1, usd + pricing.worst_case_usd(request)
    return calls, usd


def _extra_request(extra: str, problem: str, model_id: str) -> dict:
    if extra == "estimate":
        return baseline.build_request(problem, model_id)
    return formulation_checklist.build_request(problem, PLANNED_NAMES, model_id)


def render(items: list[Item], records: dict[str, Record], budget: Budget) -> str:
    rows = [["problem", "condition", "result", "tries", "tokens in/out", "cost", "paid",
             "low conf", "checklist"]]  # fmt: skip
    right: dict[str, int] = {}
    for i in items:
        if i.outcome == "errored":
            result = "ERRORED (not scored yet)"
        else:
            correct = _correct(records[i.problem_id], i)
            right[i.condition] = right.get(i.condition, 0) + correct
            result = "right" if correct else ("wrong (loud)" if i.status is None else "wrong")
        flags = "-" if i.checklist_flags is None else (
            ", ".join(f["kind"] for f in i.checklist_flags) or "none")  # fmt: skip
        low = {True: "LOW", False: "ok", None: "-"}[i.low_confidence]
        rows.append([i.problem_id, i.condition, result, str(i.attempts),
                     f"{i.input_tokens:,}/{i.output_tokens:,}", f"${i.cost_usd:.4f}",
                     f"${i.paid_usd:.4f}", low, flags])  # fmt: skip
    widths = [max(len(r[k]) for r in rows) for k in range(len(rows[0]))]
    lines = ["  ".join(cell.ljust(w) for cell, w in zip(r, widths, strict=True)) for r in rows]
    lines.append("")
    for condition in FOLLOWUP_CONDITIONS:
        mine = [i for i in items if i.condition == condition]
        if mine:
            scored = [i for i in mine if i.outcome == "done"]
            extra = sum(i.report_only_cost_usd for i in mine)
            lines.append(
                f"{condition}: {right.get(condition, 0)}/{len(scored)} right, "
                f"{len(mine) - len(scored)} errored; cost ${sum(i.cost_usd for i in mine):.4f}"
                + (f", plus ${extra:.4f} report-only" if extra else "")
            )
    lines.append(
        f"Spent in this directory: ${budget.spent_usd:.4f} on {budget.calls} paid calls, "
        f"cap ${budget.cap_usd:.2f}"
    )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run problems through the conditions.")
    parser.add_argument("ids", nargs="*", help="problem ids from the split (or --all)")
    parser.add_argument("--all", action="store_true", help="every scorable problem in the split")
    parser.add_argument("--out", type=Path, required=True, help="the run's directory")
    parser.add_argument("--cap", type=float, default=1.00, help="dollar cap (default 1.00)")
    parser.add_argument("--split", choices=DEV_SPLITS + TEST_SPLITS + FOLLOWUP_DEV_SPLITS
                        + [FOLLOWUP_TEST], default="dev",
                        help="a test split runs only on frozen inputs, with --all; "
                        f"{FOLLOWUP_TEST} loads only on the follow-up's frozen inputs, even for "
                        "--plan")  # fmt: skip
    parser.add_argument("--conditions", nargs="+", choices=FOLLOWUP_CONDITIONS,
                        default=list(CONDITIONS))  # fmt: skip
    parser.add_argument("--model", default=formulate.DEFAULT_MODEL)
    parser.add_argument("--plan", action="store_true", help="show the worst case; no calls")
    parser.add_argument("--estimate", action="store_true",
                        help="solver conditions: also record the low-confidence flag "
                             "(report-only, one more call per pair)")  # fmt: skip
    parser.add_argument("--sample", type=int, nargs="+", default=[0],
                        help="which repeated samples this run directory holds: 0 replays "
                             "existing caches; 1, 2, ... ask again. Several (0 1 2) run "
                             "together, problem by problem, under one cap")  # fmt: skip
    parser.add_argument("--checklist", action="store_true",
                        help="solver conditions: also record the checklist flags "
                             "(report-only, one more call per pair)")  # fmt: skip
    args = parser.parse_args(argv)
    extras = tuple(x for x in ("estimate", "checklist") if getattr(args, x))

    if args.all == bool(args.ids):
        sys.exit("give problem ids or --all, not both")
    if args.split in [*TEST_SPLITS, FOLLOWUP_TEST] and not args.all:
        sys.exit(f"a {args.split} run covers every scorable problem: use --all")
    followup_split = args.split in FOLLOWUP_DEV_SPLITS or args.split == FOLLOWUP_TEST
    if followup_split:
        try:
            by_id = {p.id: p for p in followup_problems(args.split)}
        except freeze.FreezeError as refused:  # the sealed split: no approval, or a change
            sys.exit(f"REFUSED: {refused}")
    else:
        by_id = {r.id: r for r in load_records(GROUND_TRUTH_DIR / f"{args.split}.json")}
    unknown = [i for i in args.ids if i not in by_id or not (
        by_id[i].scorable if followup_split else is_scorable(by_id[i]))]  # fmt: skip
    if unknown:
        sys.exit(f"not scorable {args.split} problems: {', '.join(unknown)}")
    records = scorable_records(args.split) if args.all else [by_id[i] for i in args.ids]
    if followup_split:  # the order evaluate() runs them in
        records = followup.in_run_order(args.split, records)
    conditions = tuple(c for c in FOLLOWUP_CONDITIONS if c in args.conditions)  # baseline first
    samples = tuple(dict.fromkeys(args.sample))
    budget = Budget(args.cap, args.out / "spend.jsonl")

    done = done_pairs(args.out / "results.jsonl", args.model)
    pending = sum((r.id, c, s) not in done for r in records for s in samples for c in conditions)
    calls, worst = worst_case_plan(records, conditions, done, args.model, extras, samples)
    print(f"{pending} pairs pending: at most {calls} paid "
          f"calls, at most ${worst:.4f} if every reply used all {api.MAX_TOKENS:,} tokens. "
          f"Already spent here: ${budget.spent_usd:.4f} of the ${args.cap:.2f} cap.")  # fmt: skip
    if args.plan:
        return
    if args.split in TEST_SPLITS:  # before the key is even read
        try:
            freeze.check()
            require_whole_experiment(args.split, records, conditions)
        except (freeze.FreezeError, ValueError) as refused:
            sys.exit(f"REFUSED: {refused}")
    if args.split == FOLLOWUP_TEST:  # already frozen, or the problems wouldn't have loaded
        try:
            require_whole_followup(records, conditions, samples)
        except ValueError as refused:
            sys.exit(f"REFUSED: {refused}")
    try:
        client = BudgetedClient(anthropic.Anthropic(api_key=get_api_key()), budget)
    except MissingAPIKeyError as error:
        sys.exit(str(error))
    try:
        evaluate(records, conditions, client, args.out, args.split, args.model, extras,
                 samples)  # fmt: skip
    except RunStopped as stop:
        print(render(latest_items(args.out / "results.jsonl"), by_id, budget))
        sys.exit(f"\nSTOPPED: {stop}\nRe-run the same command to resume; nothing is paid twice.")
    print(render(latest_items(args.out / "results.jsonl"), by_id, budget))


if __name__ == "__main__":
    main()
