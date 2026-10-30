"""The report: scoring a run's answers, Amendment 1's passes, and the pre-registered
statistics, on runs built with FakeClient. Every expected number is worked out by hand in
the comments. Never calls the API."""

import json

import pytest
from fakes import GAS_MODEL, GAS_REPLY, INFEASIBLE_REPLY, FakeClient, model, status_error
from pytest import approx

from opt_agent import api, evaluate, freeze, packets, report
from opt_agent.api import RunStopped
from opt_agent.budget import Budget, BudgetedClient
from opt_agent.evaluate import CONDITIONS
from opt_agent.ground_truth import GROUND_TRUTH_DIR, answer, load_records, scorable

DEV = {r.id: r for r in load_records(GROUND_TRUTH_DIR / "dev.json")}
GAS = DEV["439170086"]  # integer optimum 251 (LP 250); integrality-sensitive
NEW_GAS = {r.id: r for r in load_records(GROUND_TRUTH_DIR / "dev-perturbed.json")}[GAS.id]
LOTION = DEV["-1028228232"]  # infeasible as written
TRIPS = DEV["-640645082"]  # says LP, labeled integer: IP 880, LP 888.89
FAKE_CALL_USD = (1200 * 0.10 + 300 * 0.50) / 1e6
CONTINUOUS_GAS = json.dumps({**GAS_MODEL, "variables": [
    {**v, "integer": False} for v in GAS_MODEL["variables"]]})  # fmt: skip
DROPPED = model([("at least 5", ">=", 5)])  # the infeasible model with "at most 3" deleted


def says(status: str, objective: float | None = None) -> str:
    return json.dumps({"status": status, "objective": objective})


def run(out, *replies, records=(GAS,), conditions=CONDITIONS, cap=1.00, split="dev"):
    client = BudgetedClient(FakeClient(*replies), Budget(cap, out / "spend.jsonl"))
    return evaluate.evaluate(list(records), conditions, client, out, split)


@pytest.fixture(autouse=True)
def no_waiting(monkeypatch):
    monkeypatch.setattr(api.time, "sleep", lambda s: None)


@pytest.fixture
def mixed_run(tmp_path):
    """Gas: the baseline says 251 (right); single-shot makes the trips continuous, 250
    (wrong, silent), and self-correction replays it. Lotion: the baseline and single-shot
    say infeasible (right); self-correction revises, drops a constraint, and claims an
    optimum (wrong, silent, flagged). Five paid calls."""
    run(tmp_path, says("optimal", 251), CONTINUOUS_GAS,
        says("infeasible"), INFEASIBLE_REPLY, DROPPED, records=[GAS, LOTION])  # fmt: skip
    return tmp_path


def test_a_hand_checked_run(mixed_run):
    r = report.build(mixed_run)
    assert r["complete"] and r["open"] == {"errored": 0, "pending": 0}
    accuracy = {c: r["conditions"][c]["accuracy"] for c in CONDITIONS}
    assert [accuracy[c]["all"]["right"] for c in CONDITIONS] == [2, 1, 0]
    # 0 of 1: the 95% Wilson interval is [0, z^2 / (1 + z^2)] = [0, 0.7935].
    wilson = [0.0, approx(0.7935, abs=1e-4)]
    assert accuracy["single-shot"]["has an optimum"] == {
        "right": 0, "n": 1, "accuracy": 0.0, "wilson95": wilson}  # fmt: skip
    assert accuracy["single-shot"]["is a status"]["right"] == 1
    single, selfc = r["conditions"]["single-shot"], r["conditions"]["self-correction"]
    assert single["failures"]["silent"] == [GAS.id]
    assert selfc["failures"]["silent"] == sorted([GAS.id, LOTION.id])
    assert selfc["is a status: claimed an optimum"] == {"problems": 1, "with revision flags": 1}
    assert single["is a status: claimed an optimum"] == {"problems": 0, "with revision flags": 0}
    assert r["paid_usd"] == approx(5 * FAKE_CALL_USD)
    assert selfc["cost_usd"] == approx(3 * FAKE_CALL_USD)  # its replayed first call counts


def test_lenient_accuracy_accepts_the_lp_optimum_on_sensitive_problems(mixed_run):
    single = report.build(mixed_run)["conditions"]["single-shot"]
    assert single["accuracy"]["integrality-sensitive"]["right"] == 0  # gas: 250, not 251
    assert single["lenient accuracy, integrality-sensitive"]["right"] == 1


def test_comparisons_use_discordant_pairs_and_holm(mixed_run):
    rows = {(c["a"], c["b"], c["subset"]): c for c in report.build(mixed_run)["comparisons"]}
    assert len(rows) == 6
    status = rows[("single-shot", "self-correction", "is a status")]
    assert (status["n"], status["only a right"], status["only b right"]) == (1, 1, 0)
    assert status["p"] == 1.0  # one discordant pair: as likely as a coin flip
    gas = rows[("baseline", "single-shot", "has an optimum")]
    assert (gas["only a right"], gas["only b right"]) == (1, 0)
    assert all(c["p_holm"] >= c["p"] and not c["significant"] for c in rows.values())


def test_a_pair_errored_in_every_pass_counts_as_wrong_and_is_listed(tmp_path):
    """Amendment 1: the first pass and 3 resume passes."""
    for passes in range(1, 4):
        run(tmp_path, status_error(400), conditions=("baseline",))
        r = report.build(tmp_path)
        assert not r["complete"] and r["open"]["errored"] == 1, passes
    run(tmp_path, status_error(400), conditions=("baseline",))
    r = report.build(tmp_path)
    assert r["complete"]
    failures = r["conditions"]["baseline"]["failures"]
    assert failures["loud"] == {"api error": 1}
    assert failures["api errors after every pass"] == [GAS.id]


def test_a_pair_that_succeeds_on_resume_is_scored_and_counted_as_a_re_run(tmp_path):
    run(tmp_path, status_error(400), conditions=("baseline",))
    run(tmp_path, status_error(400), conditions=("baseline",))
    run(tmp_path, says("optimal", 251), conditions=("baseline",))
    baseline = report.build(tmp_path)["conditions"]["baseline"]
    assert baseline["accuracy"]["all"]["right"] == 1
    assert baseline["re-runs"] == {"pairs": 1, "by passes needed": {"3": 1}}


def test_pending_pairs_make_the_report_incomplete(tmp_path):
    with pytest.raises(RunStopped):
        run(tmp_path, says("optimal", 251), cap=0.001)  # stopped before the first call
    r = report.build(tmp_path)
    assert not r["complete"] and r["open"] == {"errored": 0, "pending": 3}
    assert r["conditions"]["baseline"]["accuracy"]["all"]["n"] == 0


def test_the_1e_4_sensitivity_counts_answers_that_would_flip(tmp_path):
    run(tmp_path, says("optimal", 251 * (1 + 5e-5)), conditions=("baseline",))
    baseline = report.build(tmp_path)["conditions"]["baseline"]
    assert baseline["accuracy"]["all"]["right"] == 0
    assert baseline["flips at 1e-4"] == {"wrong to right": 1, "right to wrong": 0}


def test_says_lp_problems_count_answers_with_the_lp_optimum(tmp_path):
    run(tmp_path, says("optimal", TRIPS.lp.objective), records=[TRIPS], conditions=("baseline",))
    baseline = report.build(tmp_path)["conditions"]["baseline"]
    assert baseline["says LP: answered with the LP optimum"] == 1
    assert baseline["accuracy"]["says LP, labeled integer"]["right"] == 0  # the label decides


def test_the_report_is_the_same_for_the_same_inputs(mixed_run):
    first = json.dumps(report.build(mixed_run))
    assert json.dumps(report.build(mixed_run)) == first


def test_provenance_names_the_inputs_and_settings(mixed_run, monkeypatch):
    monkeypatch.setattr(freeze, "FREEZE_PATH", mixed_run / "no-approval.json")
    p = report.build(mixed_run)["provenance"]
    assert set(p["inputs_sha256"]) == {"dev.json", "reviews.json"}
    assert p["manifest"]["problem_ids"] == [GAS.id, LOTION.id]
    assert len(p["passes"]) == 1 and p["passes"][0]["git_sha"]
    assert (p["tolerance"], p["sensitivity_tolerance"], p["resume_passes"]) == (1e-6, 1e-4, 3)
    assert p["passes"][0]["fingerprint"] == freeze.digest(freeze.fingerprint())
    assert p["approved_fingerprint"] is None and not p["every pass on the approved inputs"]


def test_the_subsets_are_the_pre_registered_ones():
    test = [r for r in load_records(GROUND_TRUTH_DIR / "test.json") if scorable(r)]
    sizes = {name: len(ids) for name, ids in report.subsets(test).items()}
    assert sizes == {"all": 276, "has an optimum": 256, "is a status": 20,
                     "integrality-insensitive": 145, "integrality-sensitive": 131,
                     "do-nothing": 14, "strict wording": 25, "ambiguous": 3,
                     "says LP, labeled integer": 4}  # fmt: skip


def test_the_integrality_agreement_waits_for_the_owners_labels(tmp_path, monkeypatch):
    (tmp_path / "labels.csv").write_text("number,problem_id,variable,label\n1,x,trains,\n")
    monkeypatch.setattr(packets, "BLIND_DIR", tmp_path)
    assert "pending" in report.integrality_agreement([])


def test_the_command_line_writes_json_and_prints_a_summary(mixed_run, capsys):
    report.main([str(mixed_run)])
    printed = capsys.readouterr().out
    assert "Run report (complete)" in printed and "| all | 2 |" in printed
    assert json.loads((mixed_run / "report.json").read_text())["complete"]


def test_a_replayed_run_reports_the_same(mixed_run, tmp_path):
    """Scoring comes from the recorded answers alone: a second pass over a finished run
    adds nothing and changes nothing."""
    before = report.build(mixed_run)["conditions"]
    run(mixed_run, records=[GAS, LOTION])  # FakeClient() fails on any call
    assert report.build(mixed_run)["conditions"] == before


@pytest.fixture
def original_and_perturbed(tmp_path):
    """On the original gas problem, every condition is right (251). On the perturbed one,
    the baseline states the new answer (right), while single-shot sends the original's
    model, as if it hadn't read the new numbers: it's solved to 251, wrong here. Self-
    correction replays it."""
    original, perturbed = tmp_path / "original", tmp_path / "perturbed"
    run(original, says("optimal", 251), GAS_REPLY)
    run(perturbed, says("optimal", answer(NEW_GAS).objective), GAS_REPLY, records=[NEW_GAS],
        split="dev-perturbed")  # fmt: skip
    return original, perturbed


def test_a_perturbed_run_lists_answers_that_are_the_originals(original_and_perturbed):
    _, perturbed = original_and_perturbed
    assert answer(NEW_GAS).objective != 251  # the perturbation changed the answer
    r = report.build(perturbed)
    accuracy = {c: r["conditions"][c]["accuracy"]["all"]["right"] for c in CONDITIONS}
    assert accuracy == {"baseline": 1, "single-shot": 0, "self-correction": 0}
    assert r["perturbed"]["gave the original answer"] == {
        "baseline": [], "single-shot": [GAS.id], "self-correction": [GAS.id]}  # fmt: skip
    assert r["comparisons"] == []  # outside the McNemar family (section 4)
    assert set(r["provenance"]["inputs_sha256"]) == {
        "dev-perturbed.json", "dev.json", "reviews.json"}  # fmt: skip


def test_a_perturbed_run_pairs_with_the_original_run(original_and_perturbed):
    original, perturbed = original_and_perturbed
    moved = report.build(perturbed, original)["perturbed"]["against the original run"]
    assert moved["baseline"]["right on both"] == 1
    single = moved["single-shot"]
    assert (single["n"], single["right on the original only"], single["wrong on both"]) == (1, 1, 0)
    assert single["original"]["accuracy"] == 1.0 and single["perturbed"]["accuracy"] == 0.0


def test_only_a_matching_run_pairs_with_a_perturbed_one(original_and_perturbed, tmp_path):
    original, perturbed = original_and_perturbed
    with pytest.raises(ValueError, match="same model and prompts on dev"):
        report.build(perturbed, perturbed)  # not a run on the originals
    with pytest.raises(ValueError, match="only goes with a run on a perturbed split"):
        report.build(original, original)
    other = tmp_path / "other"
    other.mkdir()
    manifest = json.loads((original / "manifest.json").read_text())
    manifest["settings"]["baseline"] = "000000000000"  # another prompt version
    (other / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="same model and prompts"):
        report.build(perturbed, other)


def test_the_command_line_shows_the_perturbed_comparison(original_and_perturbed, capsys):
    original, perturbed = original_and_perturbed
    report.main([str(perturbed), "--original", str(original)])
    printed = capsys.readouterr().out
    assert "single-shot: gave the original problem's answer 1 times" in printed
    assert "| single-shot | 1 | 1/1 (100%" in printed and "| comparison |" not in printed


def test_gas_reply_fixture_is_right_for_every_condition(tmp_path):
    run(tmp_path, says("optimal", 251), GAS_REPLY)
    r = report.build(tmp_path)
    assert all(r["conditions"][c]["accuracy"]["all"]["right"] == 1 for c in CONDITIONS)
    assert r["conditions"]["self-correction"]["correct by reading"] == {"annotated": 1}
