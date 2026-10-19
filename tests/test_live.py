"""Calls the real Claude API, so it costs money (a fraction of a cent per run). It's excluded
from the default test run and from CI. Run it with:  python -m pytest -m live
"""

import anthropic
import pytest
from problems import FISHERY
from pytest import approx

from opt_agent.agent import run
from opt_agent.config import get_api_key

pytestmark = pytest.mark.live


def test_fishery_with_the_real_api():
    client = anthropic.Anthropic(api_key=get_api_key())
    result = run(FISHERY["document"], client)
    assert result.formulation.error is None, result.formulation.error
    assert result.verified
    assert result.solution.objective == approx(3000)
    assert result.explanation.unsupported_numbers == [], result.explanation.text
