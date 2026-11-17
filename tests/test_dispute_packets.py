"""Section 5b's packets and judge prompts (scripts/historical/dispute_packets.py): what goes in, and
nothing else. Made-up text; no API calls."""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "historical" / "dispute_packets.py"
spec = importlib.util.spec_from_file_location("dispute_packets", SCRIPT)
packets = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packets)


def test_the_labels_come_from_the_report_without_keys_or_answers(tmp_path):
    report = tmp_path / "followup_report.json"
    report.write_text(json.dumps({"disputes": [
        {"problem": "industryor:2", "key": 99.0, "answer": ["optimal", 7.0], "conditions": []},
        {"problem": "complexlp:14", "key": 14.0, "answer": ["optimal", 13.4], "conditions": []},
    ]}))  # fmt: skip
    assert packets.disputed_labels(report) == ["complexlp:14", "industryor:2"]


def test_a_packet_is_the_instructions_and_the_text():
    text = packets.packet("complexlp:14", "  A made-up problem: maximize profit.  ")
    assert text.startswith("# Encoding packet: complexlp:14\n")
    assert packets.ENCODER_INSTRUCTIONS in text
    assert text.endswith("## The problem\n\nA made-up problem: maximize profit.\n")


def test_the_judge_prompt_is_judge_prompt_md_filled_in():
    filled = packets.judge_prompt("Made-up problem text.", "x >= 0, integer\nmax x")
    template = packets.prompt_template()
    assert "{{" not in filled
    assert filled.startswith(template.split("{{PROBLEM_TEXT}}")[0])
    assert "PROBLEM TEXT:\nMade-up problem text.\n\nMODEL:\nx >= 0, integer\nmax x\n" in filled
    # only the prompt itself: none of judge_prompt.md's notes for the person pasting it
    assert "Prompt starts" not in filled and "Reading the reply" not in filled


def test_file_names():
    assert packets.file_name("complexlp:14") == "complexlp-14.md"


# ---- the encoder's reply: the project's model format, solved as written -------------------


def example_reply() -> str:
    """The example in the packet's own instructions."""
    text = packets.ENCODER_INSTRUCTIONS
    return text[text.index("{\n") : text.index("\n}\n") + 2]


def test_the_packets_example_validates_and_solves_as_written():
    from opt_agent.solver import Status, solve

    model = packets.encoding_model(example_reply())
    s = solve(model)  # max 3.5 trucks, 2 trucks <= 100, trucks integer: 50 trucks
    assert s.status is Status.OPTIMAL and s.objective == pytest.approx(175)
    assert packets.objective_constant(example_reply()) == 0


def test_a_fenced_reply_is_read_and_a_constant_is_kept():
    reply = example_reply().replace('"objective_constant": 0', '"objective_constant": 12.5')
    assert packets.objective_constant(f"```json\n{reply}\n```") == 12.5


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d.pop("meanings"), "with model and meanings"),
        (lambda d: d.update(answer=175), "keys must be"),
        (lambda d: d["meanings"].update(extra="not a variable"), "exactly the model's variables"),
        (lambda d: d["model"]["constraints"][0]["terms"][0].update(var="cars"), "undeclared"),
        (lambda d: d["model"]["constraints"][0].update(sense="="), "sense"),
        (lambda d: d.update(objective_constant="12"), "must be a number"),
    ],
)
def test_a_malformed_reply_is_refused_with_its_reason(change, message):
    data = json.loads(example_reply())
    change(data)
    with pytest.raises(ValueError, match=message):
        packets.read_encoding(json.dumps(data))


def test_not_linear_is_an_answer_but_not_a_model():
    reply = '{"not_linear": "the cost is a product of two decisions"}'
    assert packets.read_encoding(reply) == {"not_linear": "the cost is a product of two decisions"}
    with pytest.raises(ValueError, match="no linear model"):
        packets.encoding_model(reply)
