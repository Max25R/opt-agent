"""Is each NL4Opt problem about whole things or divisible quantities?

The annotations never say. Every problem where requiring whole numbers changes the answer
has a hand label (data/nl4opt/integrality.json). Everywhere else a simple rule labels it;
there the label can't change the ground-truth answer, so a mistake by the rule costs little.
"""

import re
from typing import Literal, Self

from pydantic import BaseModel, model_validator


class Integrality(BaseModel):
    # `either` (Amendment 2): the text supports both readings, so both optima are accepted.
    kind: Literal["integer", "continuous", "either"]
    source: Literal["owner", "claude", "rule", "judge"]  # who decided; judge: Amendment 2
    note: str | None = None
    # The label a judges' label replaced, kept for the agreement statistic (Amendment 2).
    replaced: Literal["integer", "continuous"] | None = None

    @model_validator(mode="after")
    def _judges_label_keeps_what_it_replaced(self) -> Self:
        # The agreement statistic compares the judges with the label they replaced
        # (packets.claude_label); without it, that comparison would quietly count a None.
        if self.source == "judge" and self.replaced is None:
            raise ValueError("a judges' label must keep the label it replaced (`replaced`)")
        return self


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
