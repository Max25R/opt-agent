import os

import pytest
from hypothesis import settings

# In CI, Hypothesis replays the same examples every run, so a red build always means a code
# change broke something. Local runs explore fresh random examples to find new bugs.
settings.register_profile("ci", derandomize=True)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))


def pytest_collection_modifyitems(config, items):
    """A `live` test calls the real Claude API, so it runs only with OPT_AGENT_LIVE=1, whatever
    -m says: pyproject.toml's `-m 'not live'` is replaced by any other -m (such as
    `-m "not slow"`), which would otherwise select the live tests too."""
    if os.getenv("OPT_AGENT_LIVE") == "1":
        return
    skip = pytest.mark.skip(reason="calls the real Claude API: runs only with OPT_AGENT_LIVE=1")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)
