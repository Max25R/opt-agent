"""The second-model study's runner and freeze (docs/SECOND_MODEL_PREREGISTRATION.md, sections 3
and 6), with tests/fakes.FakeClient in place of Claude: one call per problem, in order,
resumable, with errored calls re-run as Amendment 1 says; the cost guard (the checkpoint's
projection from token counts alone, and the hard cap); a run only from the tag, on the frozen
inputs; and, where LLM4OR's data is here, section 3's checks on all 121 problems. No API
calls."""

import hashlib
import json

import pytest
from fakes import FakeClient, status_error

from opt_agent import (
    api,
    followup,
    formulate,
    freeze,
    pricing,
    second_model,
    second_model_freeze,
)
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.freeze import FreezeError


def model_reply(bound: float = 4) -> str:
    """Claude's model for a toy problem: maximize x with x <= bound."""
    return json.dumps({
        "variables": [{"name": "x", "lower": 0, "upper": None, "integer": False}],
        "objective": {"sense": "max", "terms": [{"var": "x", "coef": 1}]},
        "constraints": [{"name": "cap", "terms": [{"var": "x", "coef": 1}], "sense": "<=",
                         "rhs": bound}],
    })  # fmt: skip


PROBLEMS = [followup.Problem(id=f"complexlp:{900 + i}", document=f"toy problem {i}", answer=4.0)
            for i in range(12)]  # fmt: skip
CALL_USD = (1200 * 2.00 + 300 * 10.00) / 1e6  # a FakeClient reply's tokens, at Sonnet's prices
HAS_DATA = all(p.exists() for p in second_model_freeze.followup_freeze.data_files())
needs_data = pytest.mark.skipif(not HAS_DATA, reason="needs LLM4OR's data (fetch_llm4or.py)")


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(api.time, "sleep", lambda s: None)


def results(path) -> list[dict]:
    return [json.loads(line) for line in (path / "results.jsonl").read_text().splitlines()]


def test_the_design_is_the_pre_registrations():
    assert (second_model.MODEL, second_model.HAIKU_MODEL) == ("claude-sonnet-5-5",
                                                              "claude-haiku-5-5")  # fmt: skip
    assert (second_model.CONDITION, second_model.SAMPLE, second_model.HAIKU_SAMPLE) == (
        "single-shot", 0, 0)  # fmt: skip
    assert (second_model.CAP_USD, second_model.CHECKPOINT, second_model.PROBLEMS) == (7.00, 10, 121)
    assert second_model.HAIKU_RECORD.relative_to(second_model.REPO_ROOT).as_posix() == (
        "runs/followup-test/results.jsonl")  # fmt: skip


def test_sonnets_price_is_on_the_pricing_page():
    """$2 and $10 per million input and output tokens at every prompt length (2026-11-22)."""
    for prompt in (1_000, 150_000):
        p = pricing.prices_for(second_model.MODEL, prompt)
        assert (p.input, p.output, p.cache_write, p.cache_read) == (2.00, 10.00, 4.00, 0.10)
    usage = api.TokenUsage(input_tokens=1200, output_tokens=300)
    assert pricing.cost_usd(usage, second_model.MODEL) == pytest.approx(CALL_USD)
    assert pricing.cost_usd(usage, second_model.MODEL) == pytest.approx(
        20 * pricing.cost_usd(usage, second_model.HAIKU_MODEL))  # fmt: skip


# ---- the runner --------------------------------------------------------------------------


def test_every_problem_runs_once_in_order_and_a_rerun_calls_nothing(tmp_path):
    client = FakeClient(*[model_reply()] * 12)
    items = second_model.run(client, tmp_path, PROBLEMS, "test")
    assert client.replies == []  # exactly twelve calls
    assert [i.problem_id for i in items] == [p.id for p in PROBLEMS]
    assert all(i.outcome == "done" and i.objective == 4.0 for i in items)
    assert {(i.split, i.condition, i.sample, i.model_id) for i in items} == {
        ("second-model", "single-shot", 0, "claude-sonnet-5-5")}  # fmt: skip
    # The request is the formulation request, Sonnet's: Haiku's but for the model.
    assert client.requests[0] == formulate.build_request(PROBLEMS[0].document, second_model.MODEL)
    assert second_model.run(FakeClient(), tmp_path, PROBLEMS, "test") == []  # replays, free
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert (manifest["model"], manifest["cap_usd"], manifest["checkpoint"]) == (
        "claude-sonnet-5-5", 7.00, 10)  # fmt: skip


def test_the_checkpoint_projects_from_token_counts_and_continues_under_the_cap(tmp_path):
    second_model.run(FakeClient(*[model_reply()] * 12), tmp_path, PROBLEMS, "test")
    [check] = [e for e in results(tmp_path) if e["kind"] == "checkpoint"]
    assert (check["answered"], check["decision"], check["cap_usd"]) == (10, "continue", 7.00)
    assert check["cost_usd"] == pytest.approx(10 * CALL_USD)
    assert check["projected_usd"] == pytest.approx(12 * CALL_USD)  # the mean, times all
    kinds = [e["kind"] for e in results(tmp_path)]
    assert kinds.index("checkpoint") == 10  # after the first 10 items, before the 11th


def test_the_checkpoint_stops_a_run_projected_over_the_cap_and_again_on_resume(tmp_path):
    cap = 11 * CALL_USD  # under the projected 12 calls' worth
    client = FakeClient(*[model_reply()] * 12)
    with pytest.raises(second_model.ProjectionTooHigh, match="after the first 10 problems"):
        second_model.run(client, tmp_path, PROBLEMS, "test", cap=cap)
    assert len(client.replies) == 2  # ten calls, then the stop
    found = results(tmp_path)
    assert [e["kind"] for e in found] == ["item"] * 10 + ["checkpoint", "stopped"]
    assert found[10]["decision"] == "stop"
    with pytest.raises(second_model.ProjectionTooHigh):  # a resume stops at the same place
        second_model.run(FakeClient(), tmp_path, PROBLEMS, "test", cap=cap)


def test_the_projection_reads_cost_alone_never_correctness():
    entry = {"outcome": "done", "cost_usd": 0.02, "status": "optimal", "objective": 4.0}
    found = {p.id: [entry] for p in PROBLEMS[:10]}
    wrong = {pid: [{**e, "objective": 99.0} for e in entries] for pid, entries in found.items()}
    assert second_model.projection(PROBLEMS, found) == second_model.projection(PROBLEMS, wrong)
    assert second_model.projection(PROBLEMS, found)["projected_usd"] == pytest.approx(0.02 * 12)
    # An errored call returned nothing: the mean is over the answers.
    errored = {**found, PROBLEMS[0].id: [{"outcome": "errored", "cost_usd": 0.0}]}
    assert second_model.projection(PROBLEMS, errored)["answered"] == 9
    assert second_model.projection(PROBLEMS, errored)["projected_usd"] == pytest.approx(0.24)
    assert second_model.projection(PROBLEMS, {})["projected_usd"] is None


def test_with_nothing_to_project_from_the_checkpoint_stops(tmp_path):
    with pytest.raises(second_model.ProjectionTooHigh, match="no answer"):
        second_model.checkpoint(tmp_path, PROBLEMS, 7.00)


def test_the_hard_cap_stops_before_a_call_could_pass_it(tmp_path):
    worst = pricing.worst_case_usd(formulate.build_request(PROBLEMS[0].document,
                                                           second_model.MODEL))  # fmt: skip
    cap = worst + 2.5 * CALL_USD  # room for three calls' worst cases, as each is reserved
    client = BudgetedClient(FakeClient(*[model_reply()] * 12),
                            Budget(cap, tmp_path / "spend.jsonl"))  # fmt: skip
    with pytest.raises(api.RunStopped, match="could cost up to"):
        second_model.run(client, tmp_path, PROBLEMS, "test")  # type: ignore[arg-type]
    assert client.budget.calls == 3 and client.budget.spent_usd <= cap
    assert [e["kind"] for e in results(tmp_path)] == ["item"] * 3 + ["stopped"]
    assert len((tmp_path / "spend.jsonl").read_text().splitlines()) == 3  # the ledger


def test_an_errored_call_is_rerun_until_it_has_failed_four_passes(tmp_path):
    one = PROBLEMS[:1]
    for _ in range(4):  # the first pass and three resumes, each retrying the errored call
        second_model.run(FakeClient(status_error(400)), tmp_path, one, "test")
    assert second_model.run(FakeClient(), tmp_path, one, "test") == []  # now final: no call
    assert [e["outcome"] for e in second_model.lines(tmp_path)[one[0].id]] == ["errored"] * 4


def test_three_api_errors_in_a_row_stop_the_run(tmp_path):
    with pytest.raises(api.RunStopped, match="3 API errors in a row"):
        second_model.run(FakeClient(*[status_error(400)] * 3), tmp_path, PROBLEMS, "test")
    assert results(tmp_path)[-1]["kind"] == "stopped"


def test_a_resume_with_other_problems_is_refused(tmp_path):
    second_model.run(FakeClient(model_reply()), tmp_path, PROBLEMS[:1], "test")
    with pytest.raises(ValueError, match="another run"):
        second_model.run(FakeClient(), tmp_path, PROBLEMS[:2], "test")


def test_a_replay_stops_where_the_committed_run_did(tmp_path):
    second_model.run(FakeClient(*[model_reply()] * 3), tmp_path, PROBLEMS, "test", limit=3)
    assert len(second_model.lines(tmp_path)) == 3


def test_the_plan_counts_unsettled_problems_at_their_worst(tmp_path):
    calls, worst = second_model.plan(PROBLEMS, tmp_path)
    expected = sum(pricing.worst_case_usd(formulate.build_request(p.document, second_model.MODEL))
                   for p in PROBLEMS)  # fmt: skip
    assert calls == 12 and worst == pytest.approx(expected)
    second_model.run(FakeClient(*[model_reply()] * 12), tmp_path, PROBLEMS, "test")
    assert second_model.plan(PROBLEMS, tmp_path) == (0, 0.0)


# ---- the command line (no freeze, no key, no calls) -------------------------------------


@pytest.fixture
def toy_inputs(monkeypatch):
    monkeypatch.setattr(second_model, "inputs", lambda tag=True: (PROBLEMS, "test"))


def test_the_command_line_plans_and_needs_a_key(tmp_path, toy_inputs, monkeypatch, capsys):
    second_model.main(["--plan", "--out", str(tmp_path)])
    assert "12 calls left" in capsys.readouterr().out
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPT_AGENT_LIVE", raising=False)
    with pytest.raises(SystemExit):  # no key: nothing can be sent
        second_model.main(["--out", str(tmp_path)])
    assert not (tmp_path / "results.jsonl").exists()


def test_the_command_line_runs_within_the_cap_and_says_when_it_stopped(
    tmp_path, toy_inputs, monkeypatch, capsys
):
    monkeypatch.setattr(second_model, "get_api_key", lambda: "a test key")
    fakes = iter([FakeClient(*[model_reply()] * 12), FakeClient(*[status_error(400)] * 3)])
    monkeypatch.setattr(second_model.anthropic, "Anthropic", lambda api_key: next(fakes))
    second_model.main(["--out", str(tmp_path / "a")])
    assert "12 calls this pass" in capsys.readouterr().out
    assert len((tmp_path / "a" / "spend.jsonl").read_text().splitlines()) == 12
    with pytest.raises(SystemExit, match="stopped: 3 API errors in a row"):
        second_model.main(["--out", str(tmp_path / "b")])


# ---- the freeze ---------------------------------------------------------------------------


def approval_of(prints: dict) -> second_model_freeze.SecondModelApproval:
    return second_model_freeze.SecondModelApproval(
        approved_on="2026-11-22", commit=None, fingerprint=prints, approved_by="a test",
        analysis_sha256=prints["src/opt_agent/second_model_report.py"])  # fmt: skip


@pytest.fixture
def frozen_here(tmp_path, monkeypatch):
    """A fresh approval of the inputs as they are, with matching packages."""
    path = tmp_path / "FREEZE.json"
    path.write_text(approval_of(second_model_freeze.fingerprint()).model_dump_json())
    monkeypatch.setattr(second_model_freeze, "FREEZE_PATH", path)
    monkeypatch.setattr(second_model_freeze, "drifted_packages", lambda: {})
    return path


def test_the_fingerprint_names_what_the_comparison_rests_on():
    named = {
        "docs/SECOND_MODEL_PREREGISTRATION.md", "src/opt_agent/second_model.py",
        "src/opt_agent/second_model_report.py", "requirements.lock",
        "runs/followup-test/results.jsonl", "data/followup/split.json", "model", "haiku.model",
        "haiku.record", "haiku.sample", "api.MAX_TOKENS", "api.THINKING", "api.EFFORT",
        "temperature", "formulate.SYSTEM_PROMPT", "formulate.LP_SCHEMA", "prices", "cap_usd",
        "checkpoint", "alpha", "seed.order", "seed.bootstrap", "tolerance", "ids.unexposed",
    }  # fmt: skip
    assert named <= set(second_model_freeze.fingerprint())


def test_a_fresh_approval_checks_and_any_change_refuses(frozen_here):
    prints = second_model_freeze.fingerprint()
    assert second_model_freeze.check() == freeze.digest(prints)
    changed = approval_of(prints | {"cap_usd": "another"})
    frozen_here.write_text(changed.model_dump_json())
    with pytest.raises(FreezeError, match="cap_usd"):
        second_model_freeze.check()


def test_a_run_needs_the_tag_holding_the_approval_and_these_inputs(frozen_here, monkeypatch):
    monkeypatch.setattr(second_model_freeze, "tag_exists", lambda tag=None: False)
    with pytest.raises(FreezeError, match="no tag second-model-freeze"):
        second_model.inputs()
    monkeypatch.setattr(second_model_freeze, "tag_exists", lambda tag=None: True)
    monkeypatch.setattr(second_model_freeze, "tag_problems", lambda tag=None: ["a difference"])
    with pytest.raises(FreezeError, match="doesn't hold the approved inputs"):
        second_model.inputs()
    monkeypatch.setattr(second_model_freeze, "tag_problems", lambda tag=None: [])
    assert second_model_freeze.ready() == freeze.digest(second_model_freeze.fingerprint())
    assert "the run may start" in second_model_freeze.status()


def test_without_an_approval_nothing_reads_a_problem(tmp_path, monkeypatch):
    monkeypatch.setattr(second_model_freeze, "FREEZE_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(second_model_freeze, "tag_exists", lambda tag=None: True)
    monkeypatch.setattr(second_model_freeze, "tag_problems", lambda tag=None: [])
    for tag in (True, False):
        with pytest.raises(FreezeError, match="isn't frozen"):
            second_model.inputs(tag=tag)


def test_haikus_record_is_the_one_section_2_names():
    sha = hashlib.sha256(second_model.HAIKU_RECORD.read_bytes()).hexdigest()
    assert sha == second_model_freeze.HAIKU_RECORD_SHA256
    text = second_model_freeze.PREREGISTRATION_PATH.read_text()
    assert sha in text and "runs/followup-test/results.jsonl" in text


def test_before_the_approval_the_freeze_lists_what_is_left(tmp_path, monkeypatch, capsys):
    draft = tmp_path / "PREREGISTRATION.md"
    draft.write_text("**Status: DRAFT (a test)**")
    monkeypatch.setattr(second_model_freeze, "PREREGISTRATION_PATH", draft)
    monkeypatch.setattr(second_model_freeze, "FREEZE_PATH", tmp_path / "FREEZE.json")
    monkeypatch.setattr(second_model_freeze, "_relative", str)  # the draft lives outside the repo
    monkeypatch.setattr(second_model_freeze, "haiku_replay_differs", lambda records=None: [])
    assert any("still a draft" in item for item in second_model_freeze.unfinished())
    with pytest.raises(FreezeError, match="not ready"):
        second_model_freeze.approve("a test")
    second_model_freeze.main(["status"])
    assert "Not frozen yet" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="--by"):
        second_model_freeze.main(["approve"])
    with pytest.raises(SystemExit, match="not ready"):
        second_model_freeze.main(["approve", "--by", "a test"])
    draft.unlink()
    assert any("is missing" in item for item in second_model_freeze.unfinished())


def test_a_ready_clean_tree_is_approved_and_then_checks(tmp_path, monkeypatch):
    monkeypatch.setattr(second_model_freeze, "FREEZE_PATH", tmp_path / "FREEZE.json")
    monkeypatch.setattr(second_model_freeze, "unfinished", lambda replay=False: [])
    monkeypatch.setattr(second_model_freeze, "drifted_packages", lambda: {})
    monkeypatch.setattr(second_model_freeze, "git",
                        lambda *args: "" if args[0] == "status" else "abc123")  # fmt: skip
    written = second_model_freeze.approve("a test", today="2026-11-22")
    approval = second_model_freeze.approved()
    assert approval == written and approval.approved_on == "2026-11-22"
    assert (approval.commit, approval.approved_by) == ("abc123", "a test")
    assert approval.analysis_sha256 == approval.fingerprint["src/opt_agent/second_model_report.py"]
    assert second_model_freeze.check() == freeze.digest(approval.fingerprint)


def test_the_tag_check_also_needs_the_analysis_hash(frozen_here, monkeypatch):
    approval = second_model_freeze.approved()
    wrong = approval.model_copy(update={"analysis_sha256": "another"})
    monkeypatch.setattr(second_model_freeze, "approval_at_tag", lambda *args: (wrong, []))
    assert any("analysis_sha256" in p for p in second_model_freeze.tag_problems())
    monkeypatch.setattr(second_model_freeze, "approval_at_tag", lambda *args: (None, ["no tag"]))
    assert second_model_freeze.tag_problems() == ["no tag"]


def test_the_tag_if_it_exists_holds_exactly_the_approval():
    """Before the tag exists there's nothing to check; from then on, it must verify."""
    if second_model_freeze.tag_exists():
        assert second_model_freeze.FREEZE_PATH.exists()
        assert second_model_freeze.tag_problems() == []


@needs_data
def test_every_problem_has_haikus_sample_0_answer_and_sonnets_requests_are_haikus():
    """Section 3, from the files: for each of the 121 problems, Sonnet's request is Haiku's
    sample-0 request but for the model, and Haiku's is the one its run sent."""
    records, pairs = second_model_freeze.problems(), second_model_freeze.recorded()
    assert len(records) == 121 and all(r.id in pairs for r in records)
    assert all(pairs[r.id].outcome == "done" for r in records)
    assert second_model_freeze.requests_differ(records) == []


@needs_data
def test_haikus_answers_replay_as_recorded_through_this_code():
    """Section 3: the solving and the checks are the same in effect (about 10 s)."""
    assert second_model_freeze.haiku_replay_differs() == []


@needs_data
def test_a_changed_request_or_answer_is_named(monkeypatch):
    records = second_model_freeze.problems()[:2]
    real = formulate.build_request
    monkeypatch.setattr(formulate, "build_request",
                        lambda problem, model_id, revision=None: {
                            **real(problem, model_id, revision), "max_tokens": 1})  # fmt: skip
    found = second_model_freeze.requests_differ(records)
    assert len(found) == 2 and all("isn't in its run's cache" in f for f in found)
    monkeypatch.setattr(formulate, "build_request", real)
    pairs = second_model_freeze.recorded()
    altered = {pid: item.model_copy(update={"objective": -1.0}) for pid, item in pairs.items()}
    monkeypatch.setattr(second_model_freeze, "recorded", lambda: altered)
    assert any("objective" in f for f in second_model_freeze.haiku_replay_differs(records))
