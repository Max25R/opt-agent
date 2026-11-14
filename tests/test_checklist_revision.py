"""The follow-up's condition 4, checklist-triggered revision (pre-registration, section 3):
single-shot, then, on a confirmed optimum with checklist flags, one revision whose feedback is
the flags; its answer is kept only if it's a confirmed optimum, else the original stands.
Examples are NL4Opt dev only. Never calls the API."""

import json

import pytest
from fakes import (
    GAS_CHECKLIST,
    GAS_CHECKLIST_REPLY,
    GAS_REPLY,
    INFEASIBLE_REPLY,
    FakeClient,
    status_error,
)
from pytest import approx

from opt_agent import api, evaluate, feedback
from opt_agent.checklist import ChecklistFlag
from opt_agent.evaluate import settings_sha256, worst_case_plan
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records

GAS = {r.id: r for r in load_records(GROUND_TRUTH_DIR / "dev.json")}["439170086"]
FAKE_CALL_USD = (1200 * 0.10 + 300 * 0.50) / 1e6

# The checklist says trains are continuous: one integrality flag on the gas model.
FLAGGING = json.dumps({**GAS_CHECKLIST, "variables": [
    {**v, "kind": "continuous"} if v["name"] == "trains" else v for v in GAS_CHECKLIST["variables"]
]})  # fmt: skip
# A revision with a different, still confirmed, optimum (so a kept one shows in the answer).
REVISED = json.loads(GAS_REPLY)
REVISED["constraints"][0]["rhs"] = 1_200_000
REVISED_REPLY = json.dumps(REVISED)


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(api.time, "sleep", lambda s: None)


def run(out, *replies, conditions=("checklist-revision",)):
    client = FakeClient(*replies)
    items = evaluate.evaluate([GAS], conditions, client, out)
    return items, client


def log(out, kind):
    lines = [json.loads(x) for x in (out / "attempts.jsonl").read_text().splitlines()]
    return [x for x in lines if x["kind"] == kind]


def test_no_flags_no_revision(tmp_path):
    [item], client = run(tmp_path, GAS_REPLY, GAS_CHECKLIST_REPLY)
    assert (item.status, item.objective, item.attempts) == ("optimal", 251, 1)
    assert (item.revised, item.revision_kept) == (False, None)
    assert "no checklist flags" in item.revision_reason
    assert item.checklist_flags == [] and len(client.requests) == 2
    # The checklist decides the answer here, so its cost is the answer's, not report-only.
    assert item.cost_usd == approx(2 * FAKE_CALL_USD) and item.report_only_cost_usd == 0


def test_flags_trigger_one_revision_and_a_confirmed_optimum_is_kept(tmp_path):
    [item], client = run(tmp_path, GAS_REPLY, FLAGGING, REVISED_REPLY)
    assert (item.revised, item.revision_kept, item.attempts) == (True, True, 2)
    assert item.status == "optimal" and item.objective != 251  # the revised model's optimum
    assert [f["kind"] for f in item.checklist_flags] == ["integrality"]
    assert item.cost_usd == approx(3 * FAKE_CALL_USD)
    [revised] = log(tmp_path, "checklist_revision")
    assert revised["kept"] is True


def test_the_revision_request_carries_the_flags_and_nothing_from_the_solver(tmp_path):
    _, client = run(tmp_path, GAS_REPLY, FLAGGING, REVISED_REPLY)
    sent = client.requests[2]["messages"][0]["content"]
    assert GAS.document in sent and GAS_REPLY in sent  # self-contained, like self-correction
    assert feedback.CHECKLIST_INTRO in sent and "integrality:" in sent
    assert "solver" not in sent.lower() and "251" not in sent.replace(GAS_REPLY, "")


@pytest.mark.parametrize("revision", [INFEASIBLE_REPLY, "not json at all"])
def test_a_revision_that_isnt_a_confirmed_optimum_leaves_the_original(tmp_path, revision):
    [item], _ = run(tmp_path, GAS_REPLY, FLAGGING, revision)
    assert (item.status, item.objective) == ("optimal", 251)
    assert (item.revised, item.revision_kept) == (True, False)
    assert item.revision_reason.startswith("the original answer stands")
    assert item.attempts == 2 and item.cost_usd == approx(3 * FAKE_CALL_USD)  # still paid for


def test_no_confirmed_optimum_means_no_checklist_and_no_revision(tmp_path):
    [item], client = run(tmp_path, INFEASIBLE_REPLY)  # a second call would fail the fake
    assert item.status == "infeasible" and item.revised is False
    assert item.checklist_flags is None and len(client.requests) == 1


@pytest.mark.parametrize("failing", ["checklist", "revision"])
def test_an_api_error_in_its_calls_makes_the_pair_errored(tmp_path, failing):
    replies = [GAS_REPLY, status_error(400)] if failing == "checklist" else [
        GAS_REPLY, FLAGGING, status_error(400)]  # fmt: skip
    [item], _ = run(tmp_path, *replies)
    assert item.outcome == "errored"  # Amendment 1: re-run, not scored


def test_its_first_reply_is_single_shots(tmp_path):
    items, client = run(tmp_path, GAS_REPLY, GAS_CHECKLIST_REPLY,
                        conditions=("single-shot", "checklist-revision"))  # fmt: skip
    assert len(client.requests) == 2  # the formulation replays from the cache
    assert items[1].cached_calls == 1


def test_it_has_its_own_settings_hash():
    # single-shot and self-correction share one (their requests are the same); this differs
    hashes = {c: settings_sha256(c, "claude-haiku-5-5") for c in evaluate.FOLLOWUP_CONDITIONS}
    others = {h for c, h in hashes.items() if c != "checklist-revision"}
    assert hashes["checklist-revision"] not in others


def test_the_plan_counts_its_checklist_and_revision():
    model = "claude-haiku-5-5"
    alone, _ = worst_case_plan([GAS], ("checklist-revision",), set(), model)
    paired, _ = worst_case_plan([GAS], ("single-shot", "checklist-revision"), set(), model)
    assert alone == 3 and paired == 3  # its first call replays single-shot's
    extras, _ = worst_case_plan([GAS], ("checklist-revision",), set(), model,
                                ("estimate", "checklist"))  # fmt: skip
    assert extras == 4  # the checklist extra is its own checklist: not counted twice


def test_the_feedback_lists_each_flag():
    flags = [ChecklistFlag(kind="missing", detail="no row for the budget", quote="at most $500"),
             ChecklistFlag(kind="extra", detail="the text states no such limit",
                           constraint="cap: x <= 4")]  # fmt: skip
    text = feedback.for_checklist(flags)
    assert text.startswith(feedback.CHECKLIST_INTRO) and text.endswith(feedback.CHECKLIST_OUTRO)
    assert '- missing: no row for the budget (the text: "at most $500")' in text
    assert "- extra: the text states no such limit (your row: cap: x <= 4)" in text
