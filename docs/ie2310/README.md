# IE 2310 kit: the agent side

Everything here is about the software half of the project, and every number comes from
`results/eval.json` or `results/followup.json`.

| file | what it is |
|---|---|
| [`summary.md`](summary.md) | A plain-English summary for a non-CS audience (about a page and a half): what the agent does, how it was tested, what we found, speed and cost, and what it means for an engineer. |
| [`figures/accuracy.png`](figures/accuracy.png) | Accuracy by condition with 95% intervals, both studies. |
| [`figures/failures.png`](figures/failures.png) | Silent (passed every check) and loud (no answer reported) failures by condition. |
| [`figures/cost.png`](figures/cost.png) | API cost by condition. |
| [`numbers.md`](numbers.md), [`numbers.csv`](numbers.csv) | Every number to cite, each with the JSON field it comes from (derived ones say how). |

**Not here, on purpose:** Vitor's parts (the hand-solving time study, the flow charts, and the
summary). The agent's time per problem, which the time study compares with hand solving, is
in `numbers.md` ("time per answer").

**Regenerate** (no API calls; the figures need matplotlib, from the optional
`requirements-docs.lock`):

```bash
pip install -r requirements-docs.lock -c requirements.lock
python scripts/ie2310.py
```

`tests/test_ie2310.py` checks that `numbers.md` and `numbers.csv` match the results files, and
`tests/test_readme_numbers.py` checks every number in `summary.md` against them.
