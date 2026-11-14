"""For a given problem and sample, single-shot, self-correction and checklist-triggered
revision share one first reply (follow-up pre-registration, section 3): their first request is
byte-identical, so the cache serves the one reply to all three, and H1 compares runs that
differ only in the revision. Different samples ask again. Mocked; never calls the API."""

import json

from fakes import GAS_CHECKLIST, GAS_PROBLEM, GAS_REPLY, FakeClient

from opt_agent import api, evaluate, followup, formulate

SOLVER_CONDITIONS = ("single-shot", "self-correction", "checklist-revision")
SAMPLES = (0, 1, 2)
GAS = followup.Problem(id="19", document=GAS_PROBLEM, answer=251)


def formulation_for(sample: int) -> str:
    """A different (still optimal) model per sample, so a reply served across samples shows."""
    model = json.loads(GAS_REPLY)
    model["constraints"][0]["rhs"] = 1_000_000 + 100_000 * sample
    return json.dumps(model)


def checklist_for(sample: int) -> str:
    """A checklist that matches that sample's model: no flags, so no revision call."""
    checklist = json.loads(json.dumps(GAS_CHECKLIST))
    checklist["requirements"][0]["rhs"] = 1_000_000 + 100_000 * sample
    return json.dumps(checklist)


def run(tmp_path):
    replies = []
    for s in SAMPLES:  # what the API is asked, in the order the runner asks it
        replies += [json.dumps({"status": "optimal", "objective": 251}),  # baseline
                    formulation_for(s),  # single-shot; the other two replay it
                    checklist_for(s)]  # checklist-revision's checklist  # fmt: skip
    client = FakeClient(*replies)
    items = evaluate.evaluate([GAS], ("baseline", *SOLVER_CONDITIONS), client, tmp_path,
                              "complexlp-dev", sample=SAMPLES)  # fmt: skip
    return items, client


def first_attempts(tmp_path) -> list[dict]:
    lines = [json.loads(x) for x in (tmp_path / "attempts.jsonl").read_text().splitlines()]
    return [x for x in lines if x["kind"] == "attempt" and x["attempt"] == 1]


def test_one_paid_formulation_per_sample(tmp_path):
    _, client = run(tmp_path)
    formulations = [r for r in client.requests if r["system"] == formulate.SYSTEM_PROMPT]
    assert len(formulations) == len(SAMPLES)  # not 3 conditions x 3 samples
    assert len(client.requests) == 3 * len(SAMPLES)


def test_the_three_conditions_send_the_same_first_request_and_get_the_same_reply(tmp_path):
    run(tmp_path)
    by_sample: dict[int, list[dict]] = {}
    for line in first_attempts(tmp_path):
        by_sample.setdefault(line["request_sha256"], []).append(line)
    assert len(by_sample) == 1  # the same request in every condition and sample...
    lines = next(iter(by_sample.values()))
    assert sorted(line["condition"] for line in lines) == sorted(SOLVER_CONDITIONS * 3)
    # ...and per sample one reply, served from the cache to the second and third condition
    replies = [line["reply"] for line in lines]
    assert len(set(replies)) == len(SAMPLES)
    assert [line["call"]["cached"] for line in lines].count(False) == len(SAMPLES)


def test_answers_match_within_a_sample_and_differ_between_samples(tmp_path):
    items, _ = run(tmp_path)
    answers = {(i.sample, i.condition): i.objective for i in items if i.condition != "baseline"}
    for s in SAMPLES:
        assert len({answers[(s, c)] for c in SOLVER_CONDITIONS}) == 1
    assert len({answers[(s, "single-shot")] for s in SAMPLES}) == len(SAMPLES)
    shared = [i for i in items if i.condition in SOLVER_CONDITIONS[1:]]
    assert all(i.cached_calls >= 1 for i in shared)


def test_the_same_holds_whichever_condition_runs_first(tmp_path):
    # A resume can leave any condition to go first; the reply is still the one it gets.
    client = FakeClient(formulation_for(0), checklist_for(0))
    first = evaluate.evaluate([GAS], ("checklist-revision",), client, tmp_path, "complexlp-dev")
    # single-shot's request, asked of the same cache and sample afterwards, gets that reply
    cache = api.Cache(tmp_path / "cache", 0)
    request = formulate.build_request(GAS_PROBLEM, "claude-haiku-5-5")
    response, info = api.call(FakeClient(), request, cache)  # no reply queued: must be cached
    assert info.cached and api.reply_text(response) == formulation_for(0)
    assert first[0].objective is not None
