# The second-model study's power (design information)

Written by `scripts/second_model_power.py`: the exact chance that the primary test (a
two-sided exact McNemar test, alpha 0.05, on 121 pairs) comes out supported (p below
alpha, with Sonnet right on more of the problems only one model gets right), if Sonnet's
accuracy is higher than Haiku's by each difference and Haiku alone is right on each share
of the problems (p01). Exact, so there's no seed. Not a threshold: the study is reported
whatever it finds.

Haiku's sample 0, the pair of every Sonnet answer, is right on 95 of the 121 problems, so
Sonnet can be right alone on at most 26 of them ("can't happen" below). Two of Haiku's
own samples disagree (one right, one wrong) on 7 to 11 problems (samples 0 and 1 on 11, 0 and 2 on 8, 1 and 2 on 7);
a different model should disagree with it at least that often.

| Haiku alone right (p01) | +5 points | +8 points | +10 points | +15 points | 80% power from |
|---|---:|---:|---:|---:|---:|
| 2% | 0.34 | 0.68 | 0.83 | 0.98 | +10.0 points |
| 4% | 0.25 | 0.53 | 0.70 | 0.93 | +12.0 points |
| 6% | 0.20 | 0.43 | 0.59 | 0.88 | +13.5 points |
| 8% | 0.16 | 0.36 | 0.51 | can't happen | never |
