"""The low-confidence flag (audit, finding 2): Claude's direct estimate of the answer, from
the no-solver baseline's own request, compared with the solver's confirmed answer at the
scoring tolerance. Report-only: it changes no answer, score or revision. Never calls the
API (fakes, or M6's cache read-only)."""

import json
from pathlib import Path

import pytest
from fakes import GAS_PROBLEM, GAS_REPLY, INFEASIBLE_REPLY, FakeClient

from opt_agent.agent import render, run
from opt_agent.api import Cache
from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records
from opt_agent.runs import Run

ROOT = Path(__file__).resolve().parents[1]


def estimate(status: str, objective: float | None = None) -> str:
    return json.dumps({"status": status, "objective": objective})


def gas(estimate_reply: str):
    client = FakeClient(GAS_REPLY, estimate_reply)
    return run(GAS_PROBLEM, client, with_explanation=False, max_attempts=1, estimate=True)


def test_an_estimate_that_disagrees_flags_low_confidence():
    """249, not 250: 250 is the model's LP relaxation, which is a note (revision 1)."""
    result = gas(estimate("optimal", 249))
    assert result.low_confidence is True
    assert "249" in result.low_confidence_reason and "251" in result.low_confidence_reason


def test_an_estimate_that_agrees_doesnt():
    result = gas(estimate("optimal", 251.0000001))  # within the scoring tolerance, 1e-6
    assert result.low_confidence is False


def test_a_status_the_estimate_disagrees_on_flags_it():
    result = gas(estimate("infeasible"))
    assert result.low_confidence is True and "infeasible" in result.low_confidence_reason


def test_an_unusable_estimate_gives_no_verdict():
    result = gas("not json")
    assert result.low_confidence is None and "estimate" in result.low_confidence_reason


def test_without_an_estimate_there_is_no_flag_and_no_extra_call():
    client = FakeClient(GAS_REPLY)
    result = run(GAS_PROBLEM, client, with_explanation=False, max_attempts=1)
    assert result.low_confidence is None and len(client.requests) == 1


def test_the_flag_changes_no_answer_and_no_revision():
    """Same replies, with and without the estimate: same answer, same loop, same requests."""
    plain = FakeClient(INFEASIBLE_REPLY, INFEASIBLE_REPLY)
    flagged = FakeClient(INFEASIBLE_REPLY, INFEASIBLE_REPLY, estimate("optimal", 10))
    a = run("...", plain, with_explanation=False)
    b = run("...", flagged, with_explanation=False, estimate=True)
    assert b.low_confidence is True
    assert (a.outcome.stopped, len(a.outcome.attempts)) == (
        b.outcome.stopped,
        len(b.outcome.attempts),
    )
    assert a.solution == b.solution and a.confirmed == b.confirmed
    assert flagged.requests[:2] == plain.requests  # the estimate comes last, apart


def test_the_command_line_shows_it():
    assert "LOW CONFIDENCE" in render(gas(estimate("optimal", 249)))
    assert "LOW CONFIDENCE" not in render(gas(estimate("optimal", 251)))


class NoCalls:
    def with_options(self, **options):
        raise AssertionError("a request missed the cache")


M6_CACHE = ROOT / "runs" / "test" / "cache"


@pytest.mark.skipif(not M6_CACHE.exists(), reason="needs the committed test run")
@pytest.mark.parametrize(("problem_id", "flagged"), [("1344881875", True), ("-1008324134", False)])
def test_the_flag_replays_from_the_m6_cache(tmp_path, problem_id, flagged):
    """1344881875: single-shot's 66500 (a "prefers" sentence made a constraint) against the
    direct estimate 59500. The estimate is the baseline condition's request, so it's cached."""
    (record,) = [r for r in load_records(GROUND_TRUTH_DIR / "test.json") if r.id == problem_id]
    session = Run(log_path=tmp_path / "log.jsonl", cache=Cache(M6_CACHE))
    result = run(record.document, NoCalls(), with_explanation=False, max_attempts=1,
                 session=session, estimate=True)  # fmt: skip
    assert result.low_confidence is flagged
