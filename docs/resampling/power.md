# The resampling study's power (design information)

Written by `scripts/resampling_power.py` (seed 20261119, 4000 simulations each): the chance that the primary test (one-sided Fisher exact, alpha 0.05) finds a flagged answer more often wrong than an unflagged one, for each scenario. Not a threshold: the study is reported whatever it finds.

| scenario | units | base rate | flags on silent failures | flags on right answers | power |
|---|---:|---:|---:|---:|---:|
| as seen on samples 0 to 2 | 120 | 16.3% | 61.3% | 18.2% | 0.96 |
| as seen, without the 13 disputed problems | 107 | 7.8% | 85.2% | 18.0% | 0.96 |
| weaker: flags 45% of silent failures, 25% of right answers | 120 | 16.3% | 45.0% | 25.0% | 0.44 |
| weak: flags 35% of silent failures, 25% of right answers | 120 | 16.3% | 35.0% | 25.0% | 0.17 |
