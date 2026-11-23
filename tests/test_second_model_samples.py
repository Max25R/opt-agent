"""The second-model samples study's runner and freeze (docs/second_model/SAMPLES_PREREGISTRATION.md,
sections 3 and 6), with tests/fakes.FakeClient in place of Claude: samples 1 and 2 of each
problem, in order, sent as the follow-up sent Haiku's (the same request, the cache key salted
by the sample), resumable, with errored calls re-run on resume; the cost guard (the checkpoint,
projecting from token counts alone, and the hard cap); a run only from the tag, on the frozen
inputs; what the pre-registration says was known; and, where LLM4OR's data is here, the checks
on all 121 problems. No API calls."""

import hashlib
import json
import re

import pytest
from fakes import FakeClient, status_error

from opt_agent import (
    api,
    formulate,
    freeze,
    pricing,
    second_model,
    second_model_freeze,
    second_model_samples,
    second_model_samples_freeze,
)
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.freeze import FreezeError
from opt_agent.runs import REPO_ROOT, git

runner, gate = second_model_samples, second_model_samples_freeze


def model_reply(bound: float = 4) -> str:
    """Claude's model for a toy problem: maximize x with x <= bound."""
    return json.dumps({
        "variables": [{"name": "x", "lower": 0, "upper": None, "integer": False}],
        "objective": {"sense": "max", "terms": [{"var": "x", "coef": 1}]},
        "constraints": [{"name": "cap", "terms": [{"var": "x", "coef": 1}], "sense": "<=",
                         "rhs": bound}],
    })  # fmt: skip


PROBLEMS = [second_model.followup.Problem(id=f"complexlp:{900 + i}", document=f"toy problem {i}",
                                          answer=4.0) for i in range(12)]  # fmt: skip
CALLS = 2 * len(PROBLEMS)
CALL_USD = (1200 * 2.00 + 300 * 10.00) / 1e6  # a FakeClient reply's tokens, at Sonnet's prices
HAS_DATA = all(p.exists() for p in gate.followup_freeze.data_files())
needs_data = pytest.mark.skipif(not HAS_DATA, reason="needs LLM4OR's data (fetch_llm4or.py)")


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(api.time, "sleep", lambda s: None)


def results(path) -> list[dict]:
    return [json.loads(line) for line in (path / "results.jsonl").read_text().splitlines()]


def test_the_design_is_the_pre_registrations():
    assert (runner.MODEL, runner.HAIKU_MODEL) == ("claude-sonnet-5-5", "claude-haiku-5-5")
    assert (runner.CONDITION, runner.SAMPLES, runner.HAIKU_SAMPLES) == ("single-shot", (1, 2),
                                                                        (0, 1, 2))  # fmt: skip
    assert (runner.CAP_USD, runner.CHECKPOINT) == (7.00, 10)
    relative = {name: getattr(runner, name).relative_to(REPO_ROOT).as_posix()
                for name in ("RUN_DIR", "SONNET_RECORD", "HAIKU_RECORD")}  # fmt: skip
    assert relative == {"RUN_DIR": "runs/second-model-samples",
                        "SONNET_RECORD": "runs/second-model/results.jsonl",
                        "HAIKU_RECORD": "runs/followup-test/results.jsonl"}  # fmt: skip


# ---- the calls ----------------------------------------------------------------------------


def test_each_problem_runs_sample_1_then_2_in_order_and_a_rerun_calls_nothing(tmp_path):
    client = FakeClient(*[model_reply()] * CALLS)
    items = runner.run(client, tmp_path, PROBLEMS, "test")
    assert client.replies == []  # exactly 24 calls
    assert [(i.problem_id, i.sample) for i in items] == [(p.id, s) for p in PROBLEMS
                                                         for s in (1, 2)]  # fmt: skip
    assert {(i.split, i.condition, i.model_id, i.outcome) for i in items} == {
        ("second-model-samples", "single-shot", "claude-sonnet-5-5", "done")}  # fmt: skip
    assert runner.run(FakeClient(), tmp_path, PROBLEMS, "test") == []  # replays, free
    assert runner.complete(tmp_path, PROBLEMS)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert (manifest["samples"], manifest["cap_usd"], manifest["model"]) == (
        [1, 2], 7.00, "claude-sonnet-5-5")  # fmt: skip


def test_each_sample_is_sent_as_haikus_were_the_same_request_with_a_salted_key(tmp_path):
    """No field of a request names its sample: both samples send sample 0's request, Sonnet's
    (Haiku's but for the model), and each is cached under its own salted key, so the two
    samples get their own replies."""
    client = FakeClient(model_reply(4), model_reply(5))
    items = runner.run(client, tmp_path, PROBLEMS[:1], "test")
    request = formulate.build_request(PROBLEMS[0].document, runner.MODEL)
    assert client.requests == [request, request]
    assert request == {**formulate.build_request(PROBLEMS[0].document, runner.HAIKU_MODEL),
                       "model": runner.MODEL}  # fmt: skip
    assert [i.objective for i in items] == [4.0, 5.0]  # each sample its own reply
    cached = {p.stem for p in (tmp_path / "cache").glob("*.json")}
    assert cached == {api.cache_key(request, 1), api.cache_key(request, 2)}
    assert api.cache_key(request, 0) not in cached  # sample 0's key is never used here


def test_the_checkpoint_projects_from_token_counts_and_continues_under_the_cap(tmp_path):
    runner.run(FakeClient(*[model_reply()] * CALLS), tmp_path, PROBLEMS, "test")
    [check] = [e for e in results(tmp_path) if e["kind"] == "checkpoint"]
    assert (check["answered"], check["calls"], check["decision"]) == (20, CALLS, "continue")
    assert check["cost_usd"] == pytest.approx(20 * CALL_USD)
    assert check["projected_usd"] == pytest.approx(CALLS * CALL_USD)  # the mean, times all
    assert [e["kind"] for e in results(tmp_path)].index("checkpoint") == 20  # before the 21st


def test_the_checkpoint_stops_a_run_projected_over_the_cap_and_again_on_resume(tmp_path):
    cap = (CALLS - 1) * CALL_USD  # under the projected 24 calls' worth
    client = FakeClient(*[model_reply()] * CALLS)
    with pytest.raises(runner.ProjectionTooHigh, match="after the first 10 problems"):
        runner.run(client, tmp_path, PROBLEMS, "test", cap=cap)
    assert len(client.replies) == 4  # twenty calls, then the stop
    found = results(tmp_path)
    assert [e["kind"] for e in found] == ["item"] * 20 + ["checkpoint", "stopped"]
    assert found[20]["decision"] == "stop"
    with pytest.raises(runner.ProjectionTooHigh):  # a resume stops at the same place
        runner.run(FakeClient(), tmp_path, PROBLEMS, "test", cap=cap)


def test_the_projection_reads_cost_alone_never_correctness():
    entry = {"outcome": "done", "cost_usd": 0.02, "status": "optimal", "objective": 4.0}
    found = {(p.id, s): [entry] for p in PROBLEMS[:10] for s in (1, 2)}
    wrong = {key: [{**e, "objective": 99.0} for e in entries] for key, entries in found.items()}
    one = runner.projection(PROBLEMS, found)
    assert one == runner.projection(PROBLEMS, wrong)
    assert one["projected_usd"] == pytest.approx(0.02 * CALLS)
    # An errored call returned nothing: the mean is over the answers.
    errored = {**found, (PROBLEMS[0].id, 1): [{"outcome": "errored", "cost_usd": 0}]}
    assert runner.projection(PROBLEMS, errored)["answered"] == 19
    assert runner.projection(PROBLEMS, errored)["projected_usd"] == pytest.approx(0.02 * CALLS)
    assert runner.projection(PROBLEMS, {})["projected_usd"] is None


def test_with_nothing_to_project_from_the_checkpoint_stops(tmp_path):
    with pytest.raises(runner.ProjectionTooHigh, match="no answer"):
        runner.checkpoint(tmp_path, PROBLEMS, 7.00)


def test_the_hard_cap_stops_before_a_call_could_pass_it(tmp_path):
    worst = pricing.worst_case_usd(formulate.build_request(PROBLEMS[0].document, runner.MODEL))
    cap = worst + 2.5 * CALL_USD  # room for three calls' worst cases, as each is reserved
    client = BudgetedClient(FakeClient(*[model_reply()] * CALLS),
                            Budget(cap, tmp_path / "spend.jsonl"))  # fmt: skip
    with pytest.raises(api.RunStopped, match="could cost up to"):
        runner.run(client, tmp_path, PROBLEMS, "test")  # type: ignore[arg-type]
    assert client.budget.calls == 3 and client.budget.spent_usd <= cap
    assert [e["kind"] for e in results(tmp_path)] == ["item"] * 3 + ["stopped"]
    assert len((tmp_path / "spend.jsonl").read_text().splitlines()) == 3  # the ledger


def test_an_errored_call_is_rerun_until_it_has_failed_four_passes(tmp_path):
    one = PROBLEMS[:1]
    for _ in range(4):  # the first pass and three resumes, each retrying the errored call
        runner.run(FakeClient(status_error(400), model_reply()), tmp_path, one, "test")
    assert runner.run(FakeClient(), tmp_path, one, "test") == []  # now final: no call
    found = runner.lines(tmp_path)
    assert [e["outcome"] for e in found[one[0].id, 1]] == ["errored"] * 4
    assert [e["outcome"] for e in found[one[0].id, 2]] == ["done"]
    assert runner.complete(tmp_path, one)


def test_three_api_errors_in_a_row_stop_the_run(tmp_path):
    with pytest.raises(api.RunStopped, match="3 API errors in a row"):
        runner.run(FakeClient(*[status_error(400)] * 3), tmp_path, PROBLEMS, "test")
    assert results(tmp_path)[-1]["kind"] == "stopped"
    assert not runner.complete(tmp_path, PROBLEMS)


def test_a_resume_with_other_problems_is_refused(tmp_path):
    runner.run(FakeClient(model_reply(), model_reply()), tmp_path, PROBLEMS[:1], "test")
    with pytest.raises(ValueError, match="another run"):
        runner.run(FakeClient(), tmp_path, PROBLEMS[:2], "test")


def test_a_replay_stops_where_the_committed_run_did_mid_problem(tmp_path):
    """A replay passes the calls the run reached; a stop can come between two samples."""
    runner.run(FakeClient(*[model_reply()] * 3), tmp_path, PROBLEMS, "test", limit=3)
    assert sorted(runner.lines(tmp_path)) == sorted([(PROBLEMS[0].id, 1), (PROBLEMS[0].id, 2),
                                                     (PROBLEMS[1].id, 1)])  # fmt: skip


def test_the_plan_counts_unsettled_calls_at_their_worst(tmp_path):
    expected = 2 * sum(pricing.worst_case_usd(formulate.build_request(p.document, runner.MODEL))
                       for p in PROBLEMS)  # fmt: skip
    calls, worst = runner.plan(PROBLEMS, tmp_path)
    assert calls == CALLS and worst == pytest.approx(expected)
    runner.run(FakeClient(*[model_reply()] * 3), tmp_path, PROBLEMS, "test", limit=3)
    assert runner.plan(PROBLEMS, tmp_path)[0] == CALLS - 3


def test_the_second_model_studys_run_is_only_read():
    assert runner.RUN_DIR != second_model.RUN_DIR
    assert runner.SONNET_RECORD.parent == second_model.RUN_DIR


# ---- the command line (no freeze, no key, no calls) -------------------------------------


@pytest.fixture
def toy_inputs(monkeypatch):
    monkeypatch.setattr(runner, "inputs", lambda tag=True: (PROBLEMS, "test"))


def test_the_command_line_plans_and_needs_a_key(tmp_path, toy_inputs, monkeypatch, capsys):
    runner.main(["--plan", "--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert "samples 1 and 2: 24 calls left" in out and "hard cap $7.00" in out
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPT_AGENT_LIVE", raising=False)
    with pytest.raises(SystemExit):  # no key: nothing can be sent
        runner.main(["--out", str(tmp_path)])
    assert not (tmp_path / "results.jsonl").exists()


def test_the_command_line_runs_within_the_cap(tmp_path, toy_inputs, monkeypatch, capsys):
    monkeypatch.setattr(runner, "get_api_key", lambda: "a test key")
    monkeypatch.setattr(runner.anthropic, "Anthropic",
                        lambda api_key: FakeClient(*[model_reply()] * CALLS))  # fmt: skip
    runner.main(["--out", str(tmp_path)])
    out = capsys.readouterr().out
    assert "24 calls this pass" in out and "Complete." in out
    assert len((tmp_path / "spend.jsonl").read_text().splitlines()) == CALLS


def test_the_command_line_says_when_it_stopped_or_isnt_complete(tmp_path, toy_inputs,
                                                                 monkeypatch):  # fmt: skip
    monkeypatch.setattr(runner, "get_api_key", lambda: "a test key")
    monkeypatch.setattr(runner.anthropic, "Anthropic",
                        lambda api_key: FakeClient(*[status_error(400)] * 3))  # fmt: skip
    with pytest.raises(SystemExit, match="stopped: 3 API errors in a row"):
        runner.main(["--out", str(tmp_path / "a")])
    monkeypatch.setattr(runner.anthropic, "Anthropic", lambda api_key: FakeClient(
        status_error(400), *[model_reply()] * (CALLS - 1)))  # fmt: skip
    with pytest.raises(SystemExit, match="Not complete"):
        runner.main(["--out", str(tmp_path / "b")])


# ---- the freeze ---------------------------------------------------------------------------


def approval_of(prints: dict) -> gate.SamplesApproval:
    return gate.SamplesApproval(
        approved_on="2026-11-23", commit=None, fingerprint=prints, approved_by="a test",
        analysis_sha256=prints["src/opt_agent/second_model_samples_report.py"])  # fmt: skip


@pytest.fixture
def frozen_here(tmp_path, monkeypatch):
    """A fresh approval of the inputs as they are, with matching packages."""
    path = tmp_path / "SAMPLES_FREEZE.json"
    path.write_text(approval_of(gate.fingerprint()).model_dump_json())
    monkeypatch.setattr(gate, "FREEZE_PATH", path)
    monkeypatch.setattr(gate, "drifted_packages", lambda: {})
    return path


def test_the_fingerprint_names_what_the_comparison_rests_on():
    named = {
        "docs/second_model/SAMPLES_PREREGISTRATION.md", "src/opt_agent/second_model_samples.py",
        "src/opt_agent/second_model_samples_report.py", "requirements.lock",
        "runs/followup-test/results.jsonl", "runs/second-model/results.jsonl",
        "data/followup/split.json", "model", "samples", "condition", "sonnet.record",
        "sonnet.record_sample", "haiku.model", "haiku.record", "haiku.samples", "api.MAX_TOKENS",
        "api.THINKING", "api.EFFORT", "temperature", "formulate.SYSTEM_PROMPT",
        "formulate.LP_SCHEMA", "prices", "cap_usd", "checkpoint", "seed.order", "seed.bootstrap",
        "bootstrap.resamples", "tolerance", "alpha", "ids.unexposed",
    }  # fmt: skip
    assert named <= set(gate.fingerprint())


def test_a_fresh_approval_checks_and_any_change_refuses(frozen_here):
    prints = gate.fingerprint()
    assert gate.check() == freeze.digest(prints)
    frozen_here.write_text(approval_of(prints | {"cap_usd": "another"}).model_dump_json())
    with pytest.raises(FreezeError, match="cap_usd"):
        gate.check()


def test_a_run_needs_the_tag_holding_the_approval_and_these_inputs(frozen_here, monkeypatch):
    monkeypatch.setattr(gate, "tag_exists", lambda tag=None: False)
    with pytest.raises(FreezeError, match="no tag second-model-samples-freeze"):
        runner.inputs()
    monkeypatch.setattr(gate, "tag_exists", lambda tag=None: True)
    monkeypatch.setattr(gate, "tag_problems", lambda *args: ["a difference"])
    with pytest.raises(FreezeError, match="doesn't hold the approved inputs"):
        runner.inputs()
    monkeypatch.setattr(gate, "tag_problems", lambda *args: [])
    assert gate.ready() == freeze.digest(gate.fingerprint())
    assert "the run may start" in gate.status()


def test_without_an_approval_nothing_reads_a_problem(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "FREEZE_PATH", tmp_path / "missing.json")
    monkeypatch.setattr(gate, "tag_exists", lambda tag=None: True)
    monkeypatch.setattr(gate, "tag_problems", lambda *args: [])
    for tag in (True, False):
        with pytest.raises(FreezeError, match="isn't frozen"):
            runner.inputs(tag=tag)


def test_the_records_are_the_ones_section_2_names():
    text = gate.PREREGISTRATION_PATH.read_text()
    for path, sha in ((gate.HAIKU_RECORD, gate.HAIKU_RECORD_SHA256),
                      (gate.SONNET_RECORD, gate.SONNET_RECORD_SHA256)):  # fmt: skip
        assert hashlib.sha256(path.read_bytes()).hexdigest() == sha
        assert sha in text and path.relative_to(REPO_ROOT).as_posix() in text
    assert gate.HAIKU_RECORD_SHA256 == second_model_freeze.HAIKU_RECORD_SHA256


def test_before_the_approval_the_freeze_lists_what_is_left(tmp_path, monkeypatch, capsys):
    draft = tmp_path / "PREREGISTRATION.md"
    draft.write_text("**Status: DRAFT (a test)**")
    monkeypatch.setattr(gate, "PREREGISTRATION_PATH", draft)
    monkeypatch.setattr(gate, "FREEZE_PATH", tmp_path / "SAMPLES_FREEZE.json")
    monkeypatch.setattr(gate, "_relative", str)  # the draft lives outside the repo
    monkeypatch.setattr(gate, "replay_differs", lambda records=None: [])
    assert any("still a draft" in item for item in gate.unfinished())
    with pytest.raises(FreezeError, match="not ready"):
        gate.approve("a test")
    gate.main(["status"])
    assert "Not frozen yet" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="--by"):
        gate.main(["approve"])
    with pytest.raises(SystemExit, match="not ready"):
        gate.main(["approve", "--by", "a test"])
    draft.unlink()
    assert any("is missing" in item for item in gate.unfinished())


def test_a_ready_clean_tree_is_approved_and_then_checks(tmp_path, monkeypatch):
    monkeypatch.setattr(gate, "FREEZE_PATH", tmp_path / "SAMPLES_FREEZE.json")
    monkeypatch.setattr(gate, "unfinished", lambda replay=False: [])
    monkeypatch.setattr(gate, "drifted_packages", lambda: {})
    monkeypatch.setattr(gate, "git", lambda *args: "" if args[0] == "status" else "abc123")
    written = gate.approve("a test", today="2026-11-23")
    approval = gate.approved()
    assert approval == written and approval.approved_on == "2026-11-23"
    assert approval.analysis_sha256 == approval.fingerprint[
        "src/opt_agent/second_model_samples_report.py"]  # fmt: skip
    assert gate.check() == freeze.digest(approval.fingerprint)


def test_the_tag_check_also_needs_the_analysis_hash(frozen_here, monkeypatch):
    wrong = gate.approved().model_copy(update={"analysis_sha256": "another"})
    monkeypatch.setattr(gate, "approval_at_tag", lambda *args: (wrong, []))
    assert any("analysis_sha256" in p for p in gate.tag_problems())
    monkeypatch.setattr(gate, "approval_at_tag", lambda *args: (None, ["no tag"]))
    assert gate.tag_problems() == ["no tag"]


def test_the_tag_if_it_exists_holds_exactly_its_approval():
    """Before the tag exists there's nothing to check; from then on, it must verify."""
    if gate.tag_exists():
        assert gate.FREEZE_PATH.exists()
        assert gate.tag_problems() == []


def test_the_pipeline_is_second_model_freeze_2s_plus_this_studys_modules():
    """Section 3's declared difference 2: since second-model-freeze-2, nothing under
    src/opt_agent/ or in the lock changed but this study's three new modules (at its tag once
    it exists; here before)."""
    if not second_model_freeze.tag_exists():
        pytest.skip("needs the tag second-model-freeze-2 (git fetch --tags)")
    to = [gate.FREEZE_TAG] if gate.tag_exists() else []
    changed = git("diff", "--name-status", second_model_freeze.FREEZE_TAG, *to, "--",
                  "src/opt_agent", "requirements.lock") or ""  # fmt: skip
    rows = [line.split("\t") for line in changed.splitlines()]
    new = {"src/opt_agent/second_model_samples.py",
           "src/opt_agent/second_model_samples_report.py",
           "src/opt_agent/second_model_samples_freeze.py"}  # fmt: skip
    assert all(status == "A" and path in new for status, path in rows), rows


# ---- what the pre-registration says was known ----------------------------------------------


def test_the_preregistration_discloses_the_second_model_studys_results():
    """Its table and S1's verdict, as results/second_model.json has them (formatted as
    docs/second_model/RESULTS.md formats them)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "second_model_results", REPO_ROOT / "scripts" / "second_model_results.py")  # fmt: skip
    shown = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shown)
    data = json.loads((REPO_ROOT / "results" / "second_model.json").read_text())
    text = gate.PREREGISTRATION_PATH.read_text()
    s1, sens = data["s1"], data["sensitivity"]
    rows = [("0 (S1)", s1), ("1 (sensitivity, no claim)", sens["haiku_sample_1"]),
            ("2 (sensitivity, no claim)", sens["haiku_sample_2"])]  # fmt: skip
    for name, row in rows:
        assert (f"| {name} | {row['haiku_right']} | {s1['sonnet_right']} | "
                f"{row['only_sonnet_right']} | {row['only_haiku_right']} | "
                f"{shown.p(row['p_value'])} | {shown.difference(row)} |") in text  # fmt: skip
    assert f"S1's verdict was **{s1['verdict']}**" in text
    assert f"no difference larger than {s1['within_pp']}\npoints" in text
    assert f"over its three samples is {shown.pct(sens['haiku_mean_accuracy'])}" in text
    failures = data["failures"]
    assert (f"{failures['sonnet']['silent']['k']} silent failures among its "
            f"{failures['sonnet']['verified']} verified answers") in text  # fmt: skip
    assert (f"{failures['haiku']['silent']['k']} among {failures['haiku']['verified']}"
            in text)  # fmt: skip


@needs_data
def test_the_known_haiku_side_and_what_sonnet_would_need():
    """The arithmetic in "What was known", from the two records through this study's own
    analysis: Haiku's 298 of 363, its per-problem counts and majority, and the 211 of 242 that
    Sonnet's new samples would need for a higher mean score."""
    from opt_agent import second_model_samples_report as report

    text = re.sub(r"\s+", " ", gate.PREREGISTRATION_PATH.read_text())
    problems = gate.problems()
    haiku = report.scores(problems, report.haiku_items())
    sonnet_0 = report.scores(problems, {0: report.items_of(report.SONNET_RECORD, 0)})
    total, counts = sum(haiku.values()), [sum(v == k for v in haiku.values()) for k in (3, 2, 1, 0)]
    assert f"right on {total} of its {3 * len(problems)} answers" in text
    assert (f"all three are right on {counts[0]} problems, two on {counts[1]}, one on "
            f"{counts[2]} and none on {counts[3]}") in text  # fmt: skip
    assert f"majority of three is right on {counts[0] + counts[1]}" in text
    need = total - sum(sonnet_0.values()) + 1  # one more than a tie
    assert f"at least {need} of their {2 * len(problems)} answers" in text
    assert f"({100 * need / (2 * len(problems)):.1f}%; {need - 1} ties)" in text


# ---- section 3's checks, on all 121 problems ----------------------------------------------


@needs_data
def test_every_answer_is_recorded_and_the_requests_are_section_3s():
    records = gate.problems()
    assert len(records) == 121
    for _, record_path, _, _, samples in gate.SOURCES:
        for sample in samples:
            items = gate.recorded(record_path, sample)
            assert all(r.id in items and items[r.id].outcome == "done" for r in records)
    assert gate.requests_differ(records) == []


@needs_data
def test_the_recorded_answers_replay_as_recorded_through_this_code():
    """Haiku's samples 1 and 2 and Sonnet's sample 0 (about 35 s); Haiku's sample 0 is
    tests/test_second_model.py's replay. approve() replays all four."""
    sources = [(model, record, cache, split, tuple(s for s in samples if (model, s) !=
                                                    (runner.HAIKU_MODEL, 0)))
               for model, record, cache, split, samples in gate.SOURCES]  # fmt: skip
    assert gate.replay_differs(sources=sources) == []


@needs_data
def test_a_changed_request_or_answer_is_named(monkeypatch):
    records = gate.problems()[:2]
    real = formulate.build_request
    monkeypatch.setattr(formulate, "build_request",
                        lambda problem, model_id, revision=None: {
                            **real(problem, model_id, revision), "max_tokens": 1})  # fmt: skip
    found = gate.requests_differ(records)
    assert len(found) == 6  # per problem: sample 0's request, and Haiku's samples 1 and 2
    assert sum("not the request Sonnet's sample 0 was sent" in f for f in found) == 2
    monkeypatch.setattr(formulate, "build_request", real)
    real_recorded = gate.recorded
    monkeypatch.setattr(gate, "recorded", lambda record, sample: {
        pid: item.model_copy(update={"objective": -1.0})
        for pid, item in real_recorded(record, sample).items()})  # fmt: skip
    sonnet_only = [s for s in gate.SOURCES if s[0] == runner.MODEL]
    found = gate.replay_differs(records, sonnet_only)
    assert len(found) == 2 and all("objective" in f for f in found)
