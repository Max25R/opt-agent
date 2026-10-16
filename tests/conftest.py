import os

from hypothesis import settings

# In CI, Hypothesis replays the same examples every run, so a red build always means a code
# change broke something. Local runs explore fresh random examples to find new bugs.
settings.register_profile("ci", derandomize=True)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))
