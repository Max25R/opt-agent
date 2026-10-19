"""Is each NL4Opt problem about whole things or divisible quantities?

The annotations never say. Every problem where requiring whole numbers changes the answer
has a hand label (data/nl4opt/integrality.json). Everywhere else a simple rule labels it;
there the label can't change the ground-truth answer, so a mistake by the rule costs little.
"""

import re
from typing import Literal

from pydantic import BaseModel


class Integrality(BaseModel):
    kind: Literal["integer", "continuous"]
    source: Literal["owner", "claude", "rule"]  # who decided
    note: str | None = None


# Divisible quantities: "kilograms of rice", "how many acres". Servings and cups are counted
# as whole things.
_DIVISIBLE = (
    r"(acres?|kg|kilograms?|grams?|pounds?|lbs?|tons?|tonnes?|lit(?:er|re)s?|ml|"
    r"millilit(?:er|re)s?|gallons?|ounces?|oz|square (?:feet|foot)|sq\.? ?ft|cubic \w+|"
    r"hours?|units?|dollars?)"
)


def guess(document: str, mentions: set[str]) -> Integrality:
    """The rule: continuous if the text asks "how much", is about investing, or measures a
    variable in a divisible unit ("how many kilograms", "acres of potatoes"); else integer.

    It agrees with all 9 of the owner's hand labels on the dev split.
    """
    text = document.lower()
    if "how much" in text or re.search(r"\binvest", text):
        return _continuous("asks how much, or is about investing")
    if match := re.search(rf"how many {_DIVISIBLE}\b", text):
        return _continuous(f"asks how many {match.group(1)}")
    for mention in sorted(mentions, key=len, reverse=True):  # longest first: most specific
        pattern = rf"\b{_DIVISIBLE} of (?:the |each |a )?{re.escape(mention.lower())}"
        if match := re.search(pattern, text):
            return _continuous(f"says {match.group(0)!r}")
    return Integrality(kind="integer", source="rule", note="counts whole things")


def _continuous(why: str) -> Integrality:
    return Integrality(kind="continuous", source="rule", note=why)
