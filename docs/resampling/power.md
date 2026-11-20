# The resampling study's power (design information)

Written by `scripts/resampling_power.py` (seed 20261119, 4000 simulations each; units: verified sample-3 answers, expected 120 of 121, since 98.9% of the follow-up's single-shot answers on these problems were verified): the chance that the primary test (one-sided Fisher exact, alpha 0.05) finds a flagged answer more often wrong than an unflagged one, for each scenario. Not a threshold: the study is reported whatever it finds.

| scenario | units | base rate | flags on silent failures | flags on right answers | power |
|---|---:|---:|---:|---:|---:|
| as seen on samples 0 to 2 | 120 | 17.0% | 60.7% | 17.8% | 0.97 |
| as seen, without the 13 disputed problems | 107 | 8.0% | 84.6% | 17.5% | 0.97 |
| weaker: flags 45% of silent failures, 25% of right answers | 120 | 17.0% | 45.0% | 25.0% | 0.46 |
| weak: flags 35% of silent failures, 25% of right answers | 120 | 17.0% | 35.0% | 25.0% | 0.17 |
