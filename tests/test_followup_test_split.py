"""The follow-up test run's split (followup.TEST_SPLIT): both sealed benchmarks in one run
directory, keyed by labels, and the key-parsing rule (pre-registration, section 4). The run
itself uses made-up problems and a mocked freeze; the one test on the real sealed data checks
ids and hashes only. Never calls the API."""

import hashlib
import json

import pytest
from fakes import GAS_PROBLEM, FakeClient
from test_shared_first_reply import checklist_for, formulation_for

from opt_agent import evaluate, followup, followup_freeze
from opt_agent import followup_report as fr
from opt_agent.followup import Problem, parse_key
from opt_agent.freeze import FreezeError
from opt_agent.solver import Status

TEST = followup.TEST_SPLIT
SAMPLES = (0, 1, 2)

# ---- the key rule -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "status", "value"),
    [
        ("14.0", Status.OPTIMAL, 14.0),
        (57, Status.OPTIMAL, 57.0),
        (-3.25, Status.OPTIMAL, -3.25),
        ("1,234.5", Status.OPTIMAL, 1234.5),  # thousands separators
        ("1 234 567", Status.OPTIMAL, 1234567.0),
        ("  42  ", Status.OPTIMAL, 42.0),  # whitespace
        ("$1,200", Status.OPTIMAL, 1200.0),  # a currency sign
        ("-3.5 dollars", Status.OPTIMAL, -3.5),  # units
        ("150 kg/day", Status.OPTIMAL, 150.0),
        ("12%", Status.OPTIMAL, 12.0),
        ("1.5e3", Status.OPTIMAL, 1500.0),
        ("Infeasible", Status.INFEASIBLE, None),  # explicit wording
        ("No feasible solution", Status.INFEASIBLE, None),
        ("The problem is unbounded.", Status.UNBOUNDED, None),
    ],
)
def test_a_key_is_read_by_its_format(raw, status, value):
    assert parse_key(raw) == (status, value)


@pytest.mark.parametrize(
    "raw",
    [
        "No Best Solution",  # no explicit wording: not "no optimum"
        "infeasible or unbounded",  # both
        "Max: 99",  # a label, not a unit
        "12 or 13",
        "1,23",  # not a thousands separator
        "nan", "inf", float("inf"), float("nan"),
        "", None, True, [1], {"value": 1},
    ],
)  # fmt: skip
def test_anything_else_is_unparseable_never_no_optimum(raw):
    assert parse_key(raw) == (None, None)
    problem = Problem.from_key("x", "", raw)
    assert not problem.scorable and problem.key_status is None


def test_an_unscorable_problem_is_never_scored():
    with pytest.raises(ValueError, match="unparseable key"):
        followup.is_correct(Problem.from_key("x", "", "No Best Solution"), "infeasible", None)


def test_an_optimal_key_needs_its_value():
    with pytest.raises(ValueError):
        Problem(id="x", document="", answer=None)  # used to mean "no optimum"
    with pytest.raises(ValueError):
        Problem(id="x", document="", answer=3.0, key_status=Status.INFEASIBLE)


# ---- the run, keyed by labels -----------------------------------------------------------

FAKE = [
    Problem.from_key("complexlp:1", GAS_PROBLEM, "251"),
    Problem.from_key("industryor:1", GAS_PROBLEM + " Answer in dollars.", "251"),
    Problem.from_key("industryor:2", GAS_PROBLEM + " (unscorable key)", "No Best Solution"),
]
SCORABLE = FAKE[:2]


@pytest.fixture
def frozen(monkeypatch):
    """Made-up problems as the test split, and a freeze that passes."""
    monkeypatch.setattr(followup, "load_test", lambda: list(FAKE))
    monkeypatch.setattr(followup_freeze, "check", lambda: "frozen")


def replies() -> FakeClient:
    """What each problem asks, per sample: baseline, one formulation (the other two solver
    conditions replay it), and a checklist with no flags (so no revision)."""
    per_problem = []
    for s in SAMPLES:
        per_problem += [json.dumps({"status": "optimal", "objective": 251}),
                        formulation_for(s), checklist_for(s)]  # fmt: skip
    return FakeClient(*(per_problem * len(SCORABLE)))


def run(out, records=None, conditions=evaluate.FOLLOWUP_CONDITIONS, samples=SAMPLES, client=None):
    records = records if records is not None else evaluate.scorable_records(TEST)
    return evaluate.evaluate(records, conditions, client or replies(), out, TEST, sample=samples)


def order_hash(label: str) -> str:
    return hashlib.sha256(f"order:{followup.ORDER_SEED}:{label}".encode()).hexdigest()


def test_unscorable_keys_are_left_out_before_the_run(frozen):
    assert [p.id for p in evaluate.scorable_records(TEST)] == ["complexlp:1", "industryor:1"]


def test_results_manifest_and_order_use_labels(frozen, tmp_path):
    items = run(tmp_path)
    assert len(items) == len(SCORABLE) * 4 * len(SAMPLES)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    expected = sorted(["complexlp:1", "industryor:1"], key=order_hash)  # the label's hash
    assert manifest["split"] == TEST and manifest["problem_ids"] == expected
    lines = [json.loads(x) for x in (tmp_path / "results.jsonl").read_text().splitlines()]
    assert {x["problem_id"] for x in lines} == set(expected)
    assert [x["problem_id"] for x in lines[:: 4 * len(SAMPLES)]] == expected  # problem by problem
    assert all(i.outcome == "done" and i.objective is not None for i in items)


def test_the_hash_is_the_same_as_each_benchmarks_own_label():
    # "complexlp:1" in the joint split sorts by the same string as "1" in complexlp-test
    assert followup.label(TEST, "complexlp:1") == followup.label("complexlp-test", "1")
    assert followup.label(TEST, "industryor:1") == "industryor:1"


def test_a_resume_skips_done_pairs_by_label(frozen, tmp_path):
    run(tmp_path)
    assert run(tmp_path, client=FakeClient()) == []  # nothing to ask: every pair is done
    done = evaluate.done_pairs(tmp_path / "results.jsonl", "claude-haiku-5-5")
    assert ("industryor:1", "checklist-revision", 2) in done
    assert ("1", "checklist-revision", 2) not in done


def test_the_report_uses_labels_and_lists_unscorable_keys(frozen, tmp_path):
    run(tmp_path)
    report = fr.report_run(tmp_path)
    assert report["unscorable_keys"] == {"n": 1, "problems": ["industryor:2"]}
    assert report["complete_problems"] == 2 and report["incomplete_problems"] == []
    assert report["rows"]["sensitivity (all)"]["problems"] == 2
    # both were seen before the split (5c), so the primary row is empty: it must still build
    assert report["exposed_left_out"] == ["complexlp:1", "industryor:1"]
    assert report["rows"]["primary (unexposed)"]["problems"] == 0
    json.dumps(report, allow_nan=False)


def test_a_problem_with_no_line_yet_is_incomplete(frozen, tmp_path):
    run(tmp_path)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    results = tmp_path / "results.jsonl"
    keep = [x for x in results.read_text().splitlines()
            if json.loads(x).get("problem_id") != manifest["problem_ids"][-1]]  # fmt: skip
    results.write_text("\n".join(keep) + "\n")
    report = fr.report_run(tmp_path)
    assert report["incomplete_problems"] == [manifest["problem_ids"][-1]]


def test_nothing_runs_or_is_written_without_the_freeze(monkeypatch, tmp_path):
    monkeypatch.setattr(followup, "load_test", lambda: list(FAKE))
    out = tmp_path / "run"
    with pytest.raises(FreezeError):
        run(out, records=SCORABLE, client=FakeClient())
    assert not out.exists()


def test_without_the_freeze_the_problems_dont_even_load(tmp_path):
    with pytest.raises(FreezeError):
        evaluate.scorable_records(TEST)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"records": SCORABLE[:1]}, "covers all 2 scorable problems"),
        ({"conditions": evaluate.CONDITIONS}, "covers every condition"),
        ({"samples": (0,)}, "samples 0 1 2"),
    ],
)
def test_only_the_whole_experiment_runs(frozen, tmp_path, kwargs, message):
    with pytest.raises(ValueError, match=message):
        run(tmp_path / "run", client=FakeClient(), **kwargs)
    assert not (tmp_path / "run").exists()


def test_the_order_is_the_pre_registered_one(frozen):
    # evaluate() sorts the records itself; the check refuses any other order it's handed
    reversed_order = followup.in_run_order(TEST, SCORABLE)[::-1]
    with pytest.raises(ValueError, match="pre-registered order"):
        evaluate.require_whole_followup(reversed_order, evaluate.FOLLOWUP_CONDITIONS, SAMPLES)


def test_the_cli_refuses_a_subset(frozen, tmp_path):
    with pytest.raises(SystemExit, match="use --all"):
        evaluate.main(["--split", TEST, "complexlp:1", "--out", str(tmp_path), "--plan"])


def test_the_cli_plan_needs_the_freeze(tmp_path):
    with pytest.raises(SystemExit, match="REFUSED"):
        evaluate.main(["--split", TEST, "--all", "--out", str(tmp_path), "--plan"])


# ---- the real sealed data: ids and hashes only ------------------------------------------


@pytest.mark.skipif(not all(p.exists() for p in followup_freeze.data_files()),
                    reason="LLM4OR data not downloaded")  # fmt: skip
def test_load_test_gives_the_128_labels_of_section_2(monkeypatch, capsys):
    monkeypatch.setattr(followup_freeze, "check", lambda: "ok")
    problems = followup.load_test()
    labels = [p.id for p in problems]
    assert labels == followup_freeze.sealed_labels()
    text = "".join(f"{label}\n" for label in labels)
    assert hashlib.sha256(text.encode()).hexdigest() == followup_freeze.IDS_SHA256
    every_key_parses = all(p.scorable for p in problems)
    assert every_key_parses  # the aggregate check of 2026-11-12: all 128 are numbers
    assert capsys.readouterr() == ("", "")


# ---- the rounding clause (section 4) ----------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "decimals"),
    [("4.53", 2), ("$1,234.50", 2), ("-0.125", 3), (4.53, 2), ("12.5 units", 1),
     ("14.0", None), ("14", None), (14, None), ("1.5e3", None), ("Infeasible", None),
     ("No Best Solution", None)],
)  # fmt: skip
def test_only_a_non_whole_key_written_with_decimals_gets_the_clause(raw, decimals):
    assert followup.written_decimals(raw) == decimals


@pytest.mark.parametrize(
    ("key", "objective", "why"),
    [
        ("4.53", 4.53, "tolerance"),
        ("4.53", 4.5333, "rounding"),  # off by 7e-4 relative: right only by rounding
        ("4.53", 4.525, "rounding"),  # a tie rounds either way
        ("4.53", 4.5351, None),  # rounds to 4.54
        ("4.53", 4.52, None),
        ("-0.125", -0.12549, "rounding"),
        ("12.5", 12.54, "rounding"),
        ("12.5", 12.56, None),
        ("1234.5", 1234.54, "tolerance"),  # within 1e-4 relative already
        ("12", 12.4, None),  # a whole key stays at 1e-4: a missed integrality still fails
        ("14.0", 14.04, None),  # written with a decimal, but a whole number
        ("12", 12.0009, "tolerance"),
    ],
)
def test_an_optimum_is_right_within_1e_4_or_by_rounding_to_the_key(key, objective, why):
    problem = Problem.from_key("x", "", key)
    assert followup.right_by(problem, "optimal", objective) == why
    assert followup.is_correct(problem, "optimal", objective) is (why is not None)


def test_the_rounding_clause_needs_an_optimum():
    problem = Problem.from_key("x", "", "4.53")
    assert followup.right_by(problem, "infeasible", None) is None


def test_the_report_counts_answers_right_only_by_rounding():
    problems = {"complexlp:1": Problem.from_key("1", "", "4.53"),
                "complexlp:2": Problem.from_key("2", "", "100")}  # fmt: skip

    def item(pid, condition, sample, objective):
        return evaluate.Item(problem_id=str(pid), split="complexlp-dev", condition=condition,
                             outcome="done", sample=sample, model_id="m", settings_sha256="s",
                             status="optimal", objective=objective)  # fmt: skip

    items = [item(1, c, s, 4.5333 if c == "baseline" or s == 0 else 4.53)
             for c in evaluate.FOLLOWUP_CONDITIONS for s in SAMPLES]  # fmt: skip
    items += [item(2, c, s, 100.0) for c in evaluate.FOLLOWUP_CONDITIONS for s in SAMPLES]
    report = fr.build(items, list(evaluate.FOLLOWUP_CONDITIONS), list(SAMPLES), problems, set())
    counts = report["right_only_by_rounding"]
    assert counts["baseline"] == {"answers": 3, "problems": ["complexlp:1"]}
    assert counts["single-shot"] == {"answers": 1, "problems": ["complexlp:1"]}
    accuracy = report["rows"]["sensitivity (all)"]["accuracy"]
    assert all(a["mean_score"] == 1.0 for a in accuracy.values())  # all right, either way
