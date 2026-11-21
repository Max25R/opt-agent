"""scripts/limits_claims.py (docs/analysis/limits_claims.md, exploratory): the committed record
is the script's own and the doc shows it; claims are judged by the solver's facts; the two runs
must explain the same models; and the regenerated run replays from its committed cache. No API
calls."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "limits_claims.py"
spec = importlib.util.spec_from_file_location("limits_claims", SCRIPT)
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)


def test_the_committed_record_is_the_scripts_own():
    committed = json.loads(measure.OUT.read_text())
    assert measure.compute() == committed
    assert measure.render(committed) in measure.DOC.read_text()
    assert committed["integer_programs"] + committed["lp_explanations_unchanged"] == 88


def facts(dropped: bool | None, binding: list[str]) -> dict:
    return {"binding": binding, "slack": {"budget": 2.0, "cap": 0.0},
            "limits": {"budget": {"dropped_improves": dropped, "loosened_improves": False},
                       "cap": {"dropped_improves": False, "loosened_improves": False}}}  # fmt: skip


MODEL = measure.LPModel.model_validate({
    "variables": [{"name": "r", "lower": 0, "upper": None, "integer": True}],
    "objective": {"sense": "max", "terms": [{"var": "r", "coef": 1}]},
    "constraints": [{"name": n, "terms": [{"var": "r", "coef": 1}], "sense": "<=", "rhs": 5}
                    for n in ("budget", "cap")],
})  # fmt: skip


@pytest.mark.parametrize(("dropped", "verdict"), [(True, "false"), (False, "true"),
                                                  (None, "unknown")])  # fmt: skip
def test_a_not_limiting_claim_is_judged_by_dropping_the_constraint(dropped, verdict):
    text = "The budget is not the bottleneck, since $2 of it stays unspent."
    assert measure.judged(text, MODEL, facts(dropped, ["cap"])) == [
        {"constraint": "budget", "wording": "limit", "verdict": verdict, "slack": 2.0}
    ]


def test_a_not_binding_claim_is_judged_by_the_binding_list():
    text = "The cap is not binding."
    assert measure.judged(text, MODEL, facts(True, ["cap"]))[0]["verdict"] == "false"
    assert measure.judged(text, MODEL, facts(True, []))[0]["verdict"] == "true"


def test_the_runs_must_explain_the_same_models():
    row = {"model": MODEL.model_dump(mode="json"), "explanation": "x", "facts": facts(True, []),
           "unsupported_numbers": []}  # fmt: skip
    other = row | {"model": {**row["model"], "constraints": []}}
    with pytest.raises(SystemExit, match="different models"):
        measure.per_problem({"p": row}, {"p": other})
    lp = {**row["model"], "variables": [{**row["model"]["variables"][0], "integer": False}]}
    changed = row | {"model": lp, "explanation": "y"}
    with pytest.raises(SystemExit, match="an LP's explanation changed"):
        measure.per_problem({"p": row | {"model": lp}}, {"p": changed})


def test_the_regenerated_run_replays_from_its_committed_cache():
    """Every sixth problem (all 92 replay; that takes most of a minute): agent.run with the
    limits, from the run's own cache, with a client that refuses every request."""
    from opt_agent import agent
    from opt_agent.api import Cache, ReplayOnlyClient
    from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records, scorable
    from opt_agent.runs import Run

    texts = {r.id: r.document for r in load_records(GROUND_TRUTH_DIR / "dev.json") if scorable(r)}
    cache = Cache(measure.AFTER.parent / "cache")
    rows = list(map(json.loads, measure.AFTER.read_text().splitlines()))[::6]
    for row in rows:
        session = Run(cache=cache)
        result = agent.run(texts[row["problem"]], ReplayOnlyClient(), "claude-haiku-5-5",
                           with_explanation=True, max_attempts=1, session=session)  # fmt: skip
        assert (result.explanation.text if result.explanation else None) == row["explanation"]
    assert len(rows) == 16


HEADLINED = ["README.md", "CLAUDE.md", "docs/HANDOFF.md", "docs/analysis/limits_claims.md",
             "docs/adr/0009-what-limits-an-integer-program.md", "docs/adr/README.md"]  # fmt: skip


def test_the_headline_is_the_records_count_everywhere():
    """The owner's request (2026-11-20): ADR-0009's headline is the rule's count, before -> after,
    wherever its result is stated; what the 4 are stays a labeled post hoc note."""
    runs = json.loads(measure.OUT.read_text())["runs"]
    before = runs["before"]["explanations_with_a_false_claim"]
    after = runs["after"]["explanations_with_a_false_claim"]
    headline = f"{before} → {after}"
    assert headline == "13 → 4"
    for rel in HEADLINED:
        assert headline in (ROOT / rel).read_text(), rel
    readme = (ROOT / "README.md").read_text()
    note = readme[readme.index(headline) :][:400]
    assert "post hoc note" in note and "naming the wrong constraint" in note
