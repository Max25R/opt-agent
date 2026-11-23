"""The second-model study's runner and freeze (docs/SECOND_MODEL_PREREGISTRATION.md, sections 3
and 6, and Amendment 1), with tests/fakes.FakeClient in place of Claude: one call per problem
per stage, in order, resumable, with errored calls re-run on resume; stage 2 only after stage 1
is complete; the cost guard (each stage's checkpoint, projecting from token counts alone, and
the hard caps, stage 2's over both stages); a run only from the amended tag, on the frozen
inputs, with the first tag still holding its approval; and, where LLM4OR's data is here, the
checks on all 121 problems in both conditions. No API calls."""

import hashlib
import json

import pytest
from fakes import FakeClient, status_error

from opt_agent import (
    api,
    baseline,
    followup,
    formulate,
    freeze,
    pricing,
    second_model,
    second_model_freeze,
)
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.freeze import FreezeError

STAGE_1, STAGE_2 = second_model.STAGES


def model_reply(bound: float = 4) -> str:
    """Claude's model for a toy problem: maximize x with x <= bound."""
    return json.dumps({
        "variables": [{"name": "x", "lower": 0, "upper": None, "integer": False}],
        "objective": {"sense": "max", "terms": [{"var": "x", "coef": 1}]},
        "constraints": [{"name": "cap", "terms": [{"var": "x", "coef": 1}], "sense": "<=",
                         "rhs": bound}],
    })  # fmt: skip


def baseline_reply(value: float = 4.0) -> str:
    """Claude's direct answer, with no solver."""
    return json.dumps({"status": "optimal", "objective": value})


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


def stage_1(path, n: int = 12) -> None:
    """Stage 1 on the toy problems, complete."""
    second_model.run(FakeClient(*[model_reply()] * n), path, PROBLEMS[:n], "test")


def test_the_design_is_the_pre_registrations():
    assert (second_model.MODEL, second_model.HAIKU_MODEL) == ("claude-sonnet-5-5",
                                                              "claude-haiku-5-5")  # fmt: skip
    assert (second_model.SAMPLE, second_model.HAIKU_SAMPLE) == (0, 0)
    assert second_model.STAGES == ((1, "single-shot", 11.00), (2, "baseline", 13.50))
    assert (second_model.CHECKPOINT, second_model.PROBLEMS) == (10, 121)
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


# ---- stage 1 ------------------------------------------------------------------------------


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
    assert [(s["stage"], s["condition"], s["cap_usd"]) for s in manifest["stages"]] == [
        (1, "single-shot", 11.00), (2, "baseline", 13.50)]  # fmt: skip


def test_the_checkpoint_projects_from_token_counts_and_continues_under_the_cap(tmp_path):
    stage_1(tmp_path)
    [check] = [e for e in results(tmp_path) if e["kind"] == "checkpoint"]
    assert (check["stage"], check["answered"], check["decision"]) == (1, 10, "continue")
    assert (check["cap_usd"], check["earlier_usd"]) == (11.00, 0)
    assert check["cost_usd"] == pytest.approx(10 * CALL_USD)
    assert check["projected_usd"] == pytest.approx(12 * CALL_USD)  # the mean, times all
    assert [e["kind"] for e in results(tmp_path)].index("checkpoint") == 10  # before the 11th


def test_the_checkpoint_stops_a_run_projected_over_the_cap_and_again_on_resume(tmp_path):
    cap = 11 * CALL_USD  # under the projected 12 calls' worth
    client = FakeClient(*[model_reply()] * 12)
    with pytest.raises(second_model.ProjectionTooHigh, match="stage 1, after its first 10"):
        second_model.run(client, tmp_path, PROBLEMS, "test", cap=cap)
    assert len(client.replies) == 2  # ten calls, then the stop
    found = results(tmp_path)
    assert [e["kind"] for e in found] == ["item"] * 10 + ["checkpoint", "stopped"]
    assert found[10]["decision"] == "stop"
    with pytest.raises(second_model.ProjectionTooHigh):  # a resume stops at the same place
        second_model.run(FakeClient(), tmp_path, PROBLEMS, "test", cap=cap)


def test_the_projection_reads_cost_alone_never_correctness():
    entry = {"outcome": "done", "cost_usd": 0.02, "status": "optimal", "objective": 4.0}
    found = {(p.id, "single-shot"): [entry] for p in PROBLEMS[:10]}
    wrong = {key: [{**e, "objective": 99.0} for e in entries] for key, entries in found.items()}
    one = second_model.projection(PROBLEMS, found, STAGE_1)
    assert one == second_model.projection(PROBLEMS, wrong, STAGE_1)
    assert one["projected_usd"] == pytest.approx(0.02 * 12)
    # An errored call returned nothing: the mean is over the answers.
    errored = {**found, (PROBLEMS[0].id, "single-shot"): [{"outcome": "errored", "cost_usd": 0}]}
    assert second_model.projection(PROBLEMS, errored, STAGE_1)["answered"] == 9
    assert second_model.projection(PROBLEMS, errored, STAGE_1)["projected_usd"] == pytest.approx(
        0.24)  # fmt: skip
    assert second_model.projection(PROBLEMS, {}, STAGE_1)["projected_usd"] is None


def test_with_nothing_to_project_from_the_checkpoint_stops(tmp_path):
    with pytest.raises(second_model.ProjectionTooHigh, match="no answer"):
        second_model.checkpoint(tmp_path, PROBLEMS, STAGE_1, 11.00)


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
    assert [e["outcome"] for e in second_model.lines(tmp_path)[one[0].id, "single-shot"]] == [
        "errored"] * 4  # fmt: skip
    assert second_model.stage_complete(tmp_path, one, STAGE_1)


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


# ---- stage 2 (Amendment 1) ----------------------------------------------------------------


def test_stage_2_waits_for_stage_1_to_be_complete(tmp_path):
    second_model.run(FakeClient(*[model_reply()] * 3), tmp_path, PROBLEMS, "test", limit=3)
    client = FakeClient(baseline_reply())
    with pytest.raises(second_model.StageOneIncomplete):
        second_model.run(client, tmp_path, PROBLEMS, "test", STAGE_2)
    assert client.requests == []  # nothing was sent


def test_stage_2_is_the_no_solver_baseline_with_sonnet(tmp_path):
    stage_1(tmp_path)
    client = FakeClient(*[baseline_reply()] * 12)
    items = second_model.run(client, tmp_path, PROBLEMS, "test", STAGE_2)
    assert client.replies == [] and len(items) == 12
    assert {(i.condition, i.sample, i.model_id, i.status) for i in items} == {
        ("baseline", 0, "claude-sonnet-5-5", "optimal")}  # fmt: skip
    assert client.requests[0] == baseline.build_request(PROBLEMS[0].document, second_model.MODEL)
    assert second_model.stage_complete(tmp_path, PROBLEMS, STAGE_2)
    assert second_model.run(FakeClient(), tmp_path, PROBLEMS, "test", STAGE_2) == []  # free


def test_stage_2s_checkpoint_projects_the_total_with_stage_1s_cost(tmp_path):
    stage_1(tmp_path)
    second_model.run(FakeClient(*[baseline_reply()] * 12), tmp_path, PROBLEMS, "test", STAGE_2)
    check = [e for e in results(tmp_path) if e["kind"] == "checkpoint"][-1]
    assert (check["stage"], check["cap_usd"], check["decision"]) == (2, 13.50, "continue")
    assert check["earlier_usd"] == pytest.approx(12 * CALL_USD)  # all of stage 1
    assert check["projected_usd"] == pytest.approx(24 * CALL_USD)  # plus stage 2's mean x 12


def test_stage_2s_checkpoint_stops_over_the_total_cap(tmp_path):
    stage_1(tmp_path)
    client = FakeClient(*[baseline_reply()] * 12)
    with pytest.raises(second_model.ProjectionTooHigh, match="stage 2"):
        second_model.run(client, tmp_path, PROBLEMS, "test", STAGE_2, cap=23 * CALL_USD)
    assert len(client.replies) == 2
    assert results(tmp_path)[-1] == {**results(tmp_path)[-1], "kind": "stopped", "stage": 2}


def test_the_total_cap_counts_both_stages(tmp_path):
    ledger = tmp_path / "spend.jsonl"
    worst = pricing.worst_case_usd(baseline.build_request(PROBLEMS[0].document,
                                                          second_model.MODEL))  # fmt: skip
    first = BudgetedClient(FakeClient(*[model_reply()] * 12), Budget(1.00, ledger))
    second_model.run(first, tmp_path, PROBLEMS, "test")  # type: ignore[arg-type]
    total = 12 * CALL_USD + worst + 1.5 * CALL_USD  # room for two more calls in all
    client = BudgetedClient(FakeClient(*[baseline_reply()] * 12), Budget(total, ledger))
    with pytest.raises(api.RunStopped, match="could cost up to"):
        second_model.run(client, tmp_path, PROBLEMS, "test", STAGE_2)  # type: ignore[arg-type]
    assert client.budget.calls == 14 and client.budget.spent_usd <= total  # 12 + 2, one ledger


def test_the_plan_counts_each_stages_unsettled_problems_at_their_worst(tmp_path):
    rows = second_model.plan(PROBLEMS, tmp_path)
    expected = [sum(pricing.worst_case_usd(second_model.request(p, s)) for p in PROBLEMS)
                for s in second_model.STAGES]  # fmt: skip
    assert [(s.number, calls) for s, calls, _ in rows] == [(1, 12), (2, 12)]
    assert [worst for _, _, worst in rows] == pytest.approx(expected)
    stage_1(tmp_path)
    assert [(calls, worst) for _, calls, worst in second_model.plan(PROBLEMS, tmp_path)][0] == (
        0, 0.0)  # fmt: skip


# ---- the command line (no freeze, no key, no calls) -------------------------------------


@pytest.fixture
def toy_inputs(monkeypatch):
    monkeypatch.setattr(second_model, "inputs", lambda tag=True: (PROBLEMS, "test"))


def test_the_command_line_plans_and_needs_a_key(tmp_path, toy_inputs, monkeypatch, capsys):
    second_model.main(["--plan", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert "24 calls left" in out and "hard cap $11.00" in out
    assert "hard cap $13.50 for both stages" in out
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPT_AGENT_LIVE", raising=False)
    with pytest.raises(SystemExit):  # no key: nothing can be sent
        second_model.main(["--out", str(tmp_path)])
    assert not (tmp_path / "results.jsonl").exists()


def test_the_command_line_runs_both_stages_within_their_caps(
    tmp_path, toy_inputs, monkeypatch, capsys
):
    monkeypatch.setattr(second_model, "get_api_key", lambda: "a test key")
    fakes = iter([FakeClient(*[model_reply()] * 12), FakeClient(*[baseline_reply()] * 12)])
    monkeypatch.setattr(second_model.anthropic, "Anthropic", lambda api_key: next(fakes))
    second_model.main(["--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert "stage 1: 12 calls this pass" in out and "stage 2: 12 calls this pass" in out
    assert len((tmp_path / "spend.jsonl").read_text().splitlines()) == 24  # one ledger


def test_the_command_line_holds_stage_2_until_stage_1_is_complete(
    tmp_path, toy_inputs, monkeypatch
):
    monkeypatch.setattr(second_model, "get_api_key", lambda: "a test key")
    first = FakeClient(status_error(400), *[model_reply()] * 11)  # one error, retried later
    fakes = iter([first, FakeClient()])
    monkeypatch.setattr(second_model.anthropic, "Anthropic", lambda api_key: next(fakes))
    with pytest.raises(SystemExit, match="Stage 1 isn't complete"):
        second_model.main(["--out", str(tmp_path)])
    assert not any(e["condition"] == "baseline" for e in results(tmp_path) if e["kind"] == "item")


def test_the_command_line_says_when_a_stage_stopped(tmp_path, toy_inputs, monkeypatch):
    monkeypatch.setattr(second_model, "get_api_key", lambda: "a test key")
    monkeypatch.setattr(second_model.anthropic, "Anthropic",
                        lambda api_key: FakeClient(*[status_error(400)] * 3))  # fmt: skip
    with pytest.raises(SystemExit, match="stopped in stage 1: 3 API errors in a row"):
        second_model.main(["--out", str(tmp_path)])


# ---- the freeze ---------------------------------------------------------------------------


def approval_of(prints: dict) -> second_model_freeze.SecondModelApproval:
    return second_model_freeze.SecondModelApproval(
        approved_on="2026-11-22", commit=None, fingerprint=prints, approved_by="a test",
        analysis_sha256=prints["src/opt_agent/second_model_report.py"])  # fmt: skip


@pytest.fixture
def frozen_here(tmp_path, monkeypatch):
    """A fresh approval of the inputs as they are, with matching packages."""
    path = tmp_path / "FREEZE-2.json"
    path.write_text(approval_of(second_model_freeze.fingerprint()).model_dump_json())
    monkeypatch.setattr(second_model_freeze, "FREEZE_PATH", path)
    monkeypatch.setattr(second_model_freeze, "drifted_packages", lambda: {})
    return path


def test_the_fingerprint_names_what_the_comparisons_rest_on():
    named = {
        "docs/SECOND_MODEL_PREREGISTRATION.md", "src/opt_agent/second_model.py",
        "src/opt_agent/second_model_report.py", "requirements.lock",
        "runs/followup-test/results.jsonl", "data/followup/split.json", "model", "haiku.model",
        "haiku.record", "haiku.sample", "sample", "stages", "api.MAX_TOKENS", "api.THINKING",
        "api.EFFORT", "temperature", "formulate.SYSTEM_PROMPT", "formulate.LP_SCHEMA",
        "baseline.SYSTEM_PROMPT", "baseline.ANSWER_SCHEMA", "prices", "checkpoint", "alpha",
        "seed.order", "seed.bootstrap", "tolerance", "ids.unexposed",
    }  # fmt: skip
    assert named <= set(second_model_freeze.fingerprint())


def test_a_fresh_approval_checks_and_any_change_refuses(frozen_here):
    prints = second_model_freeze.fingerprint()
    assert second_model_freeze.check() == freeze.digest(prints)
    changed = approval_of(prints | {"stages": "another"})
    frozen_here.write_text(changed.model_dump_json())
    with pytest.raises(FreezeError, match="stages"):
        second_model_freeze.check()


def test_a_run_needs_the_tag_holding_the_approval_and_these_inputs(frozen_here, monkeypatch):
    monkeypatch.setattr(second_model_freeze, "tag_exists", lambda tag=None: False)
    with pytest.raises(FreezeError, match="no tag second-model-freeze-2"):
        second_model.inputs()
    monkeypatch.setattr(second_model_freeze, "tag_exists", lambda tag=None: True)
    monkeypatch.setattr(second_model_freeze, "tag_problems", lambda *args: ["a difference"])
    with pytest.raises(FreezeError, match="doesn't hold the approved inputs"):
        second_model.inputs()
    monkeypatch.setattr(second_model_freeze, "tag_problems", lambda *args: [])
    assert second_model_freeze.ready() == freeze.digest(second_model_freeze.fingerprint())
    assert "the run may start" in second_model_freeze.status()


def test_without_an_approval_nothing_reads_a_problem(tmp_path, monkeypatch):
    monkeypatch.setattr(second_model_freeze, "FREEZE_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(second_model_freeze, "tag_exists", lambda tag=None: True)
    monkeypatch.setattr(second_model_freeze, "tag_problems", lambda *args: [])
    for tag in (True, False):
        with pytest.raises(FreezeError, match="isn't frozen"):
            second_model.inputs(tag=tag)


def test_haikus_record_is_the_one_section_2_names():
    sha = hashlib.sha256(second_model.HAIKU_RECORD.read_bytes()).hexdigest()
    assert sha == second_model_freeze.HAIKU_RECORD_SHA256
    text = second_model_freeze.PREREGISTRATION_PATH.read_text()
    assert sha in text and "runs/followup-test/results.jsonl" in text


def test_the_amendment_is_added_below_the_text_the_first_tag_froze():
    """Amendment 1 adds a section; the text second-model-freeze holds is unchanged above it."""
    from opt_agent.runs import git

    text = second_model_freeze.PREREGISTRATION_PATH.read_text()
    assert "## Amendment 1 (before any paid call), 2026-11-22" in text
    if second_model_freeze.tag_exists(second_model_freeze.ORIGINAL_TAG):
        first = git(
            "show", f"{second_model_freeze.ORIGINAL_TAG}:docs/SECOND_MODEL_PREREGISTRATION.md"
        )
        assert first is not None and text.startswith(first)


def test_before_the_approval_the_freeze_lists_what_is_left(tmp_path, monkeypatch, capsys):
    draft = tmp_path / "PREREGISTRATION.md"
    draft.write_text("**Status: DRAFT (a test)**")
    monkeypatch.setattr(second_model_freeze, "PREREGISTRATION_PATH", draft)
    monkeypatch.setattr(second_model_freeze, "FREEZE_PATH", tmp_path / "FREEZE-2.json")
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
    monkeypatch.setattr(second_model_freeze, "FREEZE_PATH", tmp_path / "FREEZE-2.json")
    monkeypatch.setattr(second_model_freeze, "unfinished", lambda replay=False: [])
    monkeypatch.setattr(second_model_freeze, "drifted_packages", lambda: {})
    monkeypatch.setattr(second_model_freeze, "git",
                        lambda *args: "" if args[0] == "status" else "abc123")  # fmt: skip
    written = second_model_freeze.approve("a test", today="2026-11-22")
    approval = second_model_freeze.approved()
    assert approval == written and approval.approved_on == "2026-11-22"
    assert approval.analysis_sha256 == approval.fingerprint["src/opt_agent/second_model_report.py"]
    assert second_model_freeze.check() == freeze.digest(approval.fingerprint)


def test_the_tag_check_also_needs_the_analysis_hash(frozen_here, monkeypatch):
    approval = second_model_freeze.approved()
    wrong = approval.model_copy(update={"analysis_sha256": "another"})
    monkeypatch.setattr(second_model_freeze, "approval_at_tag", lambda *args: (wrong, []))
    assert any("analysis_sha256" in p for p in second_model_freeze.tag_problems())
    monkeypatch.setattr(second_model_freeze, "approval_at_tag", lambda *args: (None, ["no tag"]))
    assert second_model_freeze.tag_problems() == ["no tag"]


def test_each_tag_if_it_exists_holds_exactly_its_approval():
    """The first tag keeps the first approval; the amended tag, Amendment 1's. Before a tag
    exists there's nothing to check; from then on, it must verify."""
    if second_model_freeze.tag_exists(second_model_freeze.ORIGINAL_TAG):
        assert second_model_freeze.original_tag_problems() == []
    if second_model_freeze.tag_exists():
        assert second_model_freeze.FREEZE_PATH.exists()
        assert second_model_freeze.tag_problems() == []


@needs_data
def test_every_problem_has_haikus_answers_and_sonnets_requests_are_haikus():
    """Section 3 and Amendment 1, from the files: for each of the 121 problems and both
    conditions, Sonnet's request is Haiku's sample-0 request but for the model, and Haiku's is
    the one its run sent."""
    records = second_model_freeze.problems()
    assert len(records) == 121
    for condition in second_model_freeze.CONDITIONS:
        pairs = second_model_freeze.recorded(condition)
        assert all(r.id in pairs and pairs[r.id].outcome == "done" for r in records)
    assert second_model_freeze.requests_differ(records) == []


@needs_data
def test_haikus_answers_replay_as_recorded_through_this_code():
    """Both conditions: the solving, the parsing and the checks are the same in effect, with
    one message's rewording read as the same (about 20 s)."""
    assert second_model_freeze.haiku_replay_differs() == []


@needs_data
def test_a_changed_request_or_answer_is_named(monkeypatch):
    records = second_model_freeze.problems()[:2]
    real = formulate.build_request
    monkeypatch.setattr(formulate, "build_request",
                        lambda problem, model_id, revision=None: {
                            **real(problem, model_id, revision), "max_tokens": 1})  # fmt: skip
    found = second_model_freeze.requests_differ(records)
    assert len(found) == 2 and all("(formulate): Haiku's request isn't in" in f for f in found)
    monkeypatch.setattr(formulate, "build_request", real)
    real_recorded = second_model_freeze.recorded
    monkeypatch.setattr(second_model_freeze, "recorded", lambda condition="single-shot": {
        pid: item.model_copy(update={"objective": -1.0})
        for pid, item in real_recorded(condition).items()})  # fmt: skip
    found = second_model_freeze.haiku_replay_differs(records)
    assert {f.split(")")[0].split("(")[1] for f in found if "objective" in f} == {
        "single-shot", "baseline"}  # fmt: skip


def test_the_old_wording_of_a_cut_off_reply_reads_as_the_new():
    old, new = second_model_freeze.REWORDED
    assert old.replace(*second_model_freeze.REWORDED) == new
    assert "16000" in old and "max_tokens limit" in new
