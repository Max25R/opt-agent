"""The runner's report-only extras (--estimate, --checklist) and the follow-up dev split:
recorded next to the answer, never changing it or its cost; pinned by the manifest; planned
and guarded like every other call. Examples are NL4Opt dev only. Never calls the API."""

import json

import pytest
from fakes import GAS_CHECKLIST, GAS_CHECKLIST_REPLY, GAS_REPLY, FakeClient
from pytest import approx

from opt_agent import api, evaluate, followup
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.evaluate import worst_case_plan
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records

DEV = {r.id: r for r in load_records(GROUND_TRUTH_DIR / "dev.json")}
GAS = DEV["439170086"]
FAKE_CALL_USD = (1200 * 0.10 + 300 * 0.50) / 1e6
EXTRAS = ("estimate", "checklist")
ANSWER = ("status", "objective", "no_answer", "attempts", "input_tokens", "output_tokens",
          "cost_usd", "paid_usd", "flags")  # fmt: skip


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(api.time, "sleep", lambda s: None)


def says(status, objective=None):
    return json.dumps({"status": status, "objective": objective})


def single_shot(out, *replies, extras=()):
    client = BudgetedClient(FakeClient(*replies), Budget(1.00, out / "spend.jsonl"))
    [item] = evaluate.evaluate([GAS], ("single-shot",), client, out, extras=extras)
    return item


def test_the_extras_are_recorded_and_change_no_answer_or_its_cost(tmp_path):
    plain = single_shot(tmp_path / "plain", GAS_REPLY)
    flagged_checklist = json.dumps({**GAS_CHECKLIST,
                                    "requirements": GAS_CHECKLIST["requirements"][:1]})  # fmt: skip
    extra = single_shot(tmp_path / "extra", GAS_REPLY, says("optimal", 250), flagged_checklist,
                        extras=EXTRAS)  # fmt: skip
    assert {f: getattr(extra, f) for f in ANSWER} == {f: getattr(plain, f) for f in ANSWER}
    assert (extra.estimate_status, extra.estimate_objective) == ("optimal", 250)
    assert extra.low_confidence is True and "250" in extra.low_confidence_reason
    assert [f["kind"] for f in extra.checklist_flags] == ["extra"]
    assert extra.report_only_cost_usd == approx(2 * FAKE_CALL_USD) == extra.report_only_paid_usd
    assert plain.checklist_flags is None and plain.report_only_cost_usd == 0


def test_every_extra_call_goes_through_the_budget_guard(tmp_path):
    single_shot(tmp_path, GAS_REPLY, says("optimal", 251), GAS_CHECKLIST_REPLY, extras=EXTRAS)
    assert Budget(1.00, tmp_path / "spend.jsonl").calls == 3  # formulation, estimate, checklist


def test_the_manifest_pins_the_extras(tmp_path):
    single_shot(tmp_path, GAS_REPLY, says("optimal", 251), GAS_CHECKLIST_REPLY, extras=EXTRAS)
    settings = json.loads((tmp_path / "manifest.json").read_text())["settings"]
    assert set(settings) == {"single-shot", "estimate", "checklist"}
    with pytest.raises(ValueError, match="settings"):
        single_shot(tmp_path, extras=())  # a resume without them is another experiment


def test_the_plan_counts_one_more_call_per_extra_and_solver_pair():
    conditions = ("baseline", "single-shot", "self-correction")
    calls, usd = worst_case_plan([GAS], conditions, set(), "claude-haiku-5-5")
    more, more_usd = worst_case_plan([GAS], conditions, set(), "claude-haiku-5-5", EXTRAS)
    assert more == calls + 4 and more_usd > usd  # 2 extras x 2 solver conditions


def test_the_follow_up_test_split_isnt_offered(tmp_path):
    with pytest.raises(SystemExit):
        evaluate.main(["--split", "complexlp-test", "--all", "--out", str(tmp_path), "--plan"])


@pytest.mark.skipif(not followup.COMPLEXLP.exists(), reason="needs LLM4OR's data")
def test_the_follow_up_dev_run_plans_without_a_key(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    evaluate.main(["--split", "complexlp-dev", "--all", "--conditions", "single-shot",
                   "--estimate", "--checklist", "--out", str(tmp_path / "run"), "--cap", "0.25",
                   "--plan"])  # fmt: skip
    assert "25 pairs pending: at most 75 paid calls" in capsys.readouterr().out
