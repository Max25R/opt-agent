"""Hand-written problems with answers known from textbooks or worked out by hand."""

from opt_agent.schema import LPModel


def terms(coefs: dict[str, float]) -> list[dict]:
    """{"x": 3} -> [{"var": "x", "coef": 3}], to keep the problems below readable."""
    return [{"var": name, "coef": coef} for name, coef in coefs.items()]


# Wyndor Glass (Hillier & Lieberman). Weekly batches of doors and windows; profit in $1000s.
# Optimum: doors=2, windows=6, profit=36. Shadow prices of plant hours: 0, 1.5, 1.
WYNDOR = LPModel.model_validate(
    {
        "variables": [{"name": "doors"}, {"name": "windows"}],
        "objective": {"sense": "max", "terms": terms({"doors": 3, "windows": 5})},
        "constraints": [
            {"name": "plant_1_hours", "terms": terms({"doors": 1}), "sense": "<=", "rhs": 4},
            {"name": "plant_2_hours", "terms": terms({"windows": 2}), "sense": "<=", "rhs": 12},
            {
                "name": "plant_3_hours",
                "terms": terms({"doors": 3, "windows": 2}),
                "sense": "<=",
                "rhs": 18,
            },
        ],
    }
)

# Feed blend: grain costs $2/kg, protein $3/kg. Need at least 10 kg, and the recipe needs
# exactly 2 kg more grain than protein. By hand: grain = protein + 2 and the demand binds,
# so protein = 4, grain = 6, cost = 24. Duals (solve 2 = y1 + y2, 3 = y1 - y2):
# demand 2.5, recipe -0.5.
BLEND = LPModel.model_validate(
    {
        "variables": [{"name": "grain"}, {"name": "protein"}],
        "objective": {"sense": "min", "terms": terms({"grain": 2, "protein": 3})},
        "constraints": [
            {
                "name": "demand",
                "terms": terms({"grain": 1, "protein": 1}),
                "sense": ">=",
                "rhs": 10,
            },
            {
                "name": "recipe",
                "terms": terms({"grain": 1, "protein": -1}),
                "sense": "==",
                "rhs": 2,
            },
        ],
    }
)

# Reddy Mikks (Taha), with whole tons of paint required. The LP relaxation's optimum is
# exterior=3, interior=1.5, profit=21. Enumerating interior in {0, 1, 2} by hand gives the
# integer optimum exterior=4, interior=0, profit=20. Rounding the LP answer to (3, 1) gives
# only 19.
REDDY_MIKKS = LPModel.model_validate(
    {
        "variables": [
            {"name": "exterior", "integer": True},
            {"name": "interior", "integer": True},
        ],
        "objective": {"sense": "max", "terms": terms({"exterior": 5, "interior": 4})},
        "constraints": [
            {
                "name": "raw_m1",
                "terms": terms({"exterior": 6, "interior": 4}),
                "sense": "<=",
                "rhs": 24,
            },
            {
                "name": "raw_m2",
                "terms": terms({"exterior": 1, "interior": 2}),
                "sense": "<=",
                "rhs": 6,
            },
            {
                "name": "market",
                "terms": terms({"exterior": -1, "interior": 1}),
                "sense": "<=",
                "rhs": 1,
            },
            {"name": "demand", "terms": terms({"interior": 1}), "sense": "<=", "rhs": 2},
        ],
    }
)

INFEASIBLE = LPModel.model_validate(
    {
        "variables": [{"name": "x"}],
        "objective": {"sense": "min", "terms": terms({"x": 1})},
        "constraints": [
            {"name": "at_least_5", "terms": terms({"x": 1}), "sense": ">=", "rhs": 5},
            {"name": "at_most_3", "terms": terms({"x": 1}), "sense": "<=", "rhs": 3},
        ],
    }
)


def unbounded(integer: bool) -> LPModel:
    """max x + y subject to x - y <= 1: y can grow forever."""
    return LPModel.model_validate(
        {
            "variables": [{"name": "x", "integer": integer}, {"name": "y", "integer": integer}],
            "objective": {"sense": "max", "terms": terms({"x": 1, "y": 1})},
            "constraints": [
                {"name": "gap", "terms": terms({"x": 1, "y": -1}), "sense": "<=", "rhs": 1}
            ],
        }
    )


# Found by Hypothesis. Eliminating x0 from the two equalities leaves
# 27*x3 - 33*x2 + 9*x1 = -61, which has no integer solution: the left side is always a
# multiple of 3. HiGHS's presolve proves this instantly. CBC's branch-and-bound over the
# unbounded integers x2, x3 never finishes.
HARD_INTEGER_INFEASIBLE = LPModel.model_validate(
    {
        "variables": [
            {"name": "x0", "lower": None, "upper": 4},
            {"name": "x1", "upper": 3, "integer": True},
            {"name": "x2", "integer": True},
            {"name": "x3", "integer": True},
        ],
        "objective": {"sense": "min", "terms": terms({"x0": -5, "x1": -3, "x2": -5, "x3": -2})},
        "constraints": [
            {
                "name": "c0",
                "terms": terms({"x3": -3, "x0": 4, "x2": 5, "x1": -5}),
                "sense": "==",
                "rhs": 5,
            },
            {
                "name": "c1",
                "terms": terms({"x2": -2, "x0": 5, "x1": -4, "x3": 3}),
                "sense": "==",
                "rhs": -9,
            },
        ],
    }
)

# Found by Hypothesis: with integer preprocessing on, CBC reports "Optimal" at 0
# (x1=1, x2=2), but the optimum is 0.2. By hand: x0 only hurts, so x0 = 0. Then for
# x2 = 0, 1, 2 the best x1 is min(1, 3*x2/5) = 0, 0.6, 1, giving objectives 0, 0.2, 0.
CBC_PREPROCESS_BUG = LPModel.model_validate(
    {
        "variables": [
            {"name": "x0"},
            {"name": "x1", "upper": 1},
            {"name": "x2", "upper": 2, "integer": True},
        ],
        "objective": {"sense": "max", "terms": terms({"x0": -5, "x1": 2, "x2": -1})},
        "constraints": [
            {"name": "c0", "terms": terms({"x0": -5, "x2": 3, "x1": -5}), "sense": ">=", "rhs": 0}
        ],
    }
)

# Feasible as an LP (x = 0.5) but not with x integer.
INTEGER_INFEASIBLE = LPModel.model_validate(
    {
        "variables": [{"name": "x", "integer": True}],
        "objective": {"sense": "min", "terms": terms({"x": 1})},
        "constraints": [{"name": "half", "terms": terms({"x": 2}), "sense": "==", "rhs": 1}],
    }
)


# Two real problems from the NL4Opt test split (MIT License), trimmed to the fields we use.
FISHERY = {
    "document": (
        "A fishery wants to transport their catch. They can either use local sled dogs or "
        "trucks. Local sled dogs can take 100 fish per trip while trucks can take 300 fish per "
        "trip. The cost per trip for sled dogs is $50 while the cost per trip for a truck is "
        "$100. The budget is at most $1000 and the number of sled dog trips must be less than "
        "the number of truck trips. Formulate an LP to maximize the number of fish that can be "
        "transported."
    ),
    "vars": ["sled dogs", "trucks"],
    "order_mapping": {"sled dogs": 0, "trucks": 1, "truck": 1, "sled dog": 0},
    "obj_declaration": {
        "type": "objective",
        "direction": "maximize",
        "name": "number of fish",
        "terms": {"sled dogs": "100", "trucks": "300"},
    },
    "const_declarations": [
        {
            "type": "linear",
            "direction": "budget",
            "limit": "1000",
            "terms": {"sled dogs": "50", "truck": "100"},
            "operator": "LESS_OR_EQUAL",
        },
        {
            "type": "xy",
            "x_var": "sled dog",
            "direction": "less than",
            "y_var": "truck",
            "operator": "LESS_OR_EQUAL",
        },
    ],
}

DUCKS = {
    "document": (
        "There has been an oil spill in the ocean and ducks need to be taken to shore to be "
        "cleaned either by boat or by canoe. A boat can take 10 ducks per trip while a canoe "
        "can take 8 ducks per trip. Since the boats are motor powered, they take 20 minutes per "
        "trip while the canoes take 40 minutes per trip. In order to avoid further "
        "environmental damage, there can be at most 12 boat trips and at least 60% of the trips "
        "should be by canoe. If at least 300 ducks need to be taken to shore, how many of each "
        "transportation method should be used to minimize the total amount of time needed to "
        "transport the ducks?"
    ),
    "vars": ["boat", "canoe"],
    "order_mapping": {"boat": 0, "canoe": 1, "boats": 0, "canoes": 1},
    "obj_declaration": {
        "type": "objective",
        "direction": "minimize",
        "name": "amount of time",
        "terms": {"boats": "20", "canoes": "40"},
    },
    "const_declarations": [
        {
            "type": "upperbound",
            "direction": "at most",
            "limit": "12",
            "var": "boat",
            "operator": "LESS_OR_EQUAL",
        },
        {
            "type": "ratio",
            "direction": "at least",
            "limit": "60%",
            "var": "canoe",
            "operator": "GREATER_OR_EQUAL",
        },
        {
            "type": "linear",
            "direction": "at least",
            "limit": "300",
            "terms": {"boat": "10", "canoe": "8"},
            "operator": "GREATER_OR_EQUAL",
        },
    ],
}
