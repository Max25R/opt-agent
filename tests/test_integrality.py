import pytest

from opt_agent.ground_truth import GROUND_TRUTH_DIR, load_records
from opt_agent.integrality import guess


@pytest.mark.parametrize(
    ("document", "mentions", "kind"),
    [
        ("How much of each paint should be made?", set(), "continuous"),
        ("He has $100000 to invest in telecom and healthcare.", set(), "continuous"),
        ("How many kilograms of each candy mix should be made?", set(), "continuous"),
        ("The profit per acre of potatoes is $500.", {"potatoes"}, "continuous"),
        ("How many trucks and vans should be used?", {"trucks", "vans"}, "integer"),
        ("How many servings of each should she eat?", {"cashews"}, "integer"),
    ],
)
def test_rule(document, mentions, kind):
    assert guess(document, mentions).kind == kind


def test_rule_agrees_with_every_owner_label():
    labeled = [
        r for r in load_records(GROUND_TRUTH_DIR / "dev.json") if r.integrality.source == "owner"
    ]
    assert len(labeled) == 9
    for r in labeled:
        assert guess(r.document, {v.name for v in r.model.variables}).kind == r.integrality.kind, (
            r.id
        )
