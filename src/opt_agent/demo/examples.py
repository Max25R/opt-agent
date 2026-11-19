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
"""

from pydantic import BaseModel


class Example(BaseModel):
    id: str
    kind: str
    title: str
    text: str
    reference_objective: float
    reference_note: str  # the hand-worked optimum, in words
    integer: bool  # whether integrality changes the answer


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
]

# Candidates for a fifth example that shows self-correction (ADR-0007, action item 2): each
# hides a units or percentage trap whose literal misreading makes the model infeasible, so
# the solver's feedback (the conflicting constraints) has something to fix. Not shown yet:
# scripts/paid_dev_and_demo.py tries them (the owner's paid run), and the first whose first
# model fails and whose revision is verified and matches its hand-checked answer joins
# EXAMPLES, labeled as chosen to show the loop. Each answer is checked like the others'
# (tests/test_demo.py).
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
