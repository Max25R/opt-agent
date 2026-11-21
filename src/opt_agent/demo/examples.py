"""Four example problems for the demo, written for this project (no benchmark text, so no
license questions), one per classic kind: production mix, staffing, transportation and
blending.

Each carries a reference answer worked out by hand and checked by
tests/test_demo.py::test_each_reference_answer_is_its_hand_written_models_optimum, which
solves the reference model below with both solvers. The page shows whether Claude's verified
answer matches it: verification checks the solution of Claude's model, not whether that
model is the right reading of the text, so the reference is the part only a person supplies.

Integrality: the staffing problem is the one where it matters (its LP relaxation is 15.4
baristas, the integer optimum 16). The transportation problem counts crates, but its LP
optimum is whole anyway, and the other two are in litres and kilograms.

A fifth example (FREIGHT) is none of the four kinds: it's benchmark text, chosen to show the
disagreement badge's warning, which the four never trigger (the owner's request,
2026-11-20). See its comment.
"""

from typing import Literal

from pydantic import BaseModel


class Example(BaseModel):
    id: str
    kind: str
    title: str
    text: str
    reference_objective: float
    reference_note: str  # the hand-worked optimum, in words
    integer: bool  # whether integrality changes the answer
    replay: Literal["demo", "resampling"] = "demo"  # whose replies it replays (pipeline.PROFILES)
    reference_kind: str = "hand-checked"  # who worked out reference_objective
    source: str | None = None  # a benchmark problem's origin and license
    chosen: str | None = None  # why an example that's none of the four kinds is here


EXAMPLES = [
    Example(
        id="paint",
        kind="production mix",
        title="Paint production",
        text=(
            "A paint company makes two products from the same base: Interior paint and "
            "Exterior paint. Each litre of Interior paint takes 0.5 hours of mixing time and "
            "0.2 kg of pigment, and earns a profit of $4. Each litre of Exterior paint takes "
            "0.25 hours of mixing time and 0.4 kg of pigment, and earns a profit of $5. This "
            "week the company has 125 hours of mixing time and 110 kg of pigment, and it can "
            "sell at most 250 litres of Exterior paint. How many litres of each paint should "
            "it make to maximize profit?"
        ),
        reference_objective=1600,
        reference_note="150 litres of Interior and 200 of Exterior: $1,600 profit; mixing "
        "time and pigment are both used up, and the Exterior limit has 50 litres to spare.",
        integer=False,
    ),
    Example(
        id="baristas",
        kind="staffing",
        title="Café staffing",
        text=(
            "A café is open every day and needs at least this many baristas on duty: 10 on "
            "Monday, 8 on Tuesday, 9 on Wednesday, 9 on Thursday, 12 on Friday, 15 on "
            "Saturday and 14 on Sunday. Each barista works five consecutive days and then "
            "has two days off, and the schedule repeats every week, so a barista can start "
            "their five-day stretch on any day. How many baristas should start on each day "
            "so that every day is covered with as few baristas as possible in total?"
        ),
        reference_objective=16,
        reference_note="16 baristas (whole people; the LP relaxation would say 15.4). One "
        "optimal schedule starts 1 on Monday, 1 on Tuesday, 3 on Wednesday, 4 on Thursday, "
        "3 on Friday and 4 on Saturday.",
        integer=True,
    ),
    Example(
        id="crates",
        kind="transportation",
        title="Produce shipping",
        text=(
            "A grocery distributor ships crates of produce from two warehouses to three "
            "stores. Warehouse A has 300 crates and Warehouse B has 250 crates. The North "
            "store needs at least 180 crates, the Central store at least 200, and the South "
            "store at least 150. Shipping one crate costs $4 from A to North, $6 from A to "
            "Central, $9 from A to South, $7 from B to North, $3 from B to Central, and $5 "
            "from B to South. How many crates should go from each warehouse to each store to "
            "meet every store's needs at the lowest total shipping cost?"
        ),
        reference_objective=2370,
        reference_note="$2,370: A sends 180 to North and 100 to Central; B sends 100 to "
        "Central and 150 to South. Warehouse A keeps 20 crates.",
        integer=False,
    ),
    Example(
        id="feed",
        kind="blending",
        title="Cattle feed blend",
        text=(
            "A farm co-op mixes 1,000 kg of cattle feed from corn, soybean meal and oats. "
            "Corn costs $0.30 per kg and is 10% protein and 3% fiber. Soybean meal costs "
            "$0.80 per kg and is 45% protein and 6% fiber. Oats cost $0.20 per kg and are 10% "
            "protein and 11% fiber. The feed must be at least 17% protein and at most 6% "
            "fiber by weight. How many kilograms of each ingredient should go into the feed "
            "to make it as cheaply as possible?"
        ),
        reference_objective=370,
        reference_note="500 kg of corn, 200 kg of soybean meal and 300 kg of oats: $370; "
        "the protein minimum and the fiber maximum are both exactly met.",
        integer=False,
    ),
    # Chosen to show the disagreement badge's warning (the owner's request, 2026-11-20): the
    # four above all agree. This is benchmark text, the follow-up's test problem
    # complexlp:195 (ComplexLP, CC BY-SA 4.0; DATA_NOTICE.md), so it breaks the rule that
    # demos use dev problems only, on the owner's request; the resampling study it comes from
    # is analyzed, so no result changes, but a future study on those problems should count it
    # as exposed. It replays that study's own recorded replies (pipeline.PROFILES
    # ["resampling"]): sample 3, its unit, which passed every check and was wrong (it left out
    # the two surplus regions' limits), four other samples and the no-solver answer.
    Example(
        id="freight",
        kind="chosen to show the warning",
        title="Freight cars",
        text=(
            "The China Railroad Ministry is in the process of planning relocations of freight "
            "cars among 5 regions of the country to get ready for the fall harvest. The "
            "following presents the costs of moving a car between each pair of regions. The "
            "costs are as follows: moving a car from region 1 to region 2 costs 10 units, to "
            "region 3 costs 12 units, to region 4 costs 17 units, and to region 5 costs 34 "
            "units. From region 2 to region 1 costs 10 units, to region 3 costs 18 units, to "
            "region 4 costs 8 units, and to region 5 costs 46 units. From region 3, moving a car "
            "to region 1 costs 12 units, to region 2 costs 18 units, to region 4 costs 9 units, "
            "and to region 5 costs 27 units. From region 4, the cost to move a car to region 1 "
            "is 17 units, to region 2 is 8 units, to region 3 is 9 units, and to region 5 is 20 "
            "units. Lastly, from region 5 to region 1 the cost is 34 units, to region 2 is 46 "
            "units, to region 3 is 27 units, and to region 4 is 20 units. The following displays "
            "the current number of cars and the number needed for harvest shipping in each "
            "region. Region 1 currently has 115 cars but needs 200. Region 2 has 385 cars "
            "available but requires 500. Region 3 has 410 cars against a need of 800. Region 4 "
            "is currently equipped with 480 cars, yet the need is only for 200. Finally, region "
            "5 has 610 cars available, with a need for 300 cars. Minimize the cost to move the "
            "cars such as the need is met. Provide your answer rounded to the nearest dollar."
        ),
        reference_objective=11370,
        reference_note="11,370: the benchmark's answer key, as the follow-up scored it; not "
        "worked out by hand.",
        integer=False,
        replay="resampling",
        reference_kind="benchmark's",
        source="complexlp:195 from ComplexLP (the Mamo benchmark, Huang et al. 2024, CC BY-SA "
        "4.0), as cleaned by LLM4OR (commit 75962df); the text is unchanged.",
        chosen="Chosen to show the warning: in the pre-registered resampling study, this "
        "answer passed every check and was wrong, and Claude's other samples and its "
        "no-solver answer disagreed with it. Its replies are that run's own.",
    ),
]

# Candidates for an example that shows self-correction (ADR-0007, action item 2): each
# hides a units or percentage trap whose literal misreading makes the model infeasible, so
# the solver's feedback (the conflicting constraints) would have something to fix. The
# owner's paid run (scripts/paid_dev_and_demo.py, 2026-11-19) tried five fresh samples of
# each: all 15 first models were right (docs/analysis/fix_step_tries.json), so none showed
# the loop and none joined EXAMPLES. Each answer is checked like the others' (tests/test_demo.py).
FIX_STEP_CANDIDATES = [
    Example(
        id="bakery",
        kind="production mix",
        title="Bakery oven",
        text=(
            "A bakery bakes sourdough and rye bread in one oven. A sourdough loaf needs 20 "
            "minutes of oven time and 500 grams of flour, and earns $3. A rye loaf needs 15 "
            "minutes of oven time and 400 grams of flour, and earns $2.50. The oven is free "
            "for 8 hours a day, and the bakery has 30 kilograms of flour a day. A café "
            "contract needs at least 10 rye loaves a day, and the bakery can sell at most 24 "
            "rye loaves a day. How many loaves of each kind should it bake each day to "
            "maximize profit?"
        ),
        reference_objective=78,
        reference_note="6 sourdough and 24 rye loaves: $78 a day. The oven's 8 hours (480 "
        "minutes) are used up and rye is at its sales limit; 12.6 of the 30 kg of flour are "
        "used.",
        integer=False,
    ),
    Example(
        id="fleet",
        kind="fleet purchase",
        title="Delivery vans",
        text=(
            "A delivery company is buying new vans. An electric van costs $40,000 and a "
            "diesel van costs $30,000, and the company can spend at most $1,200,000. It needs "
            "at least 35 new vans, and a city rule says at least 40% of the new vans must be "
            "electric. How many vans of each kind should it buy to spend as little as "
            "possible?"
        ),
        reference_objective=1_190_000,
        reference_note="14 electric and 21 diesel vans: $1,190,000. Exactly 35 vans, exactly "
        "40% of them electric, and $10,000 of the budget left.",
        integer=False,
    ),
    Example(
        id="furniture",
        kind="production mix",
        title="Furniture workshop",
        text=(
            "A furniture workshop makes tables and chairs. A table takes 90 minutes of "
            "carpentry and 20 minutes of finishing, and earns $120. A chair takes 30 minutes "
            "of carpentry and 15 minutes of finishing, and earns $45. This week three "
            "carpenters can each work 40 hours, one finisher can work 40 hours, and a school "
            "has ordered at least 20 chairs. How many tables and chairs should the workshop "
            "make this week to maximize its earnings?"
        ),
        reference_objective=10_080,
        reference_note="48 tables and 96 chairs: $10,080. All 120 carpentry hours and all 40 "
        "finishing hours are used, and the school's order is more than met.",
        integer=False,
    ),
]

BY_ID = {e.id: e for e in EXAMPLES}
BY_TEXT = {e.text: e for e in EXAMPLES}
