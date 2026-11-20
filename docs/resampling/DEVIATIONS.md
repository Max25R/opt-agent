# The resampling study: deviations from the pre-registration

Section 7 of `docs/RESAMPLING_PREREGISTRATION.md`: anything that runs differently from what's
written there is recorded here, with what was planned, what happened, and what it changes.
The results: [`RESULTS.md`](RESULTS.md), from `results/resampling.json`.

## 1. Writing the results file (2026-11-20, found on the analysis's first run)

**Planned.** Section 7: the results are reported in `results/resampling.json`, which "the
analysis writes": `python -m opt_agent.resampling_report`, the analysis whose hash the freeze
records.

**What happened.** The frozen analysis computed its report, and then its `main()` stopped at
`json.dumps` with `TypeError: Object of type bool is not JSON serializable`, so it wrote no
file. The value was R2's `detected`, a numpy bool: `stats.mcnemar_exact` returns a numpy
float whenever its p-value is below 1, and comparing a numpy float with `ALPHA` gives a numpy
bool. The analysis's tests, on synthetic answers, check `build()`'s report and never wrote it
as JSON, so they didn't catch this.

**What's done instead.** `scripts/resampling_results.py` calls the frozen `build()`
unchanged, on the same run and the same problems, and writes its report as `main()` does
(`json.dumps`, indent 1, a newline at the end), with json's `default` writing each numpy
scalar as the Python value it holds. The frozen code isn't edited: `scripts/reproduce.py`
runs the script in `resampling-freeze`'s own tree, so the report comes from the tag's
package, and rebuilds the file byte for byte.

**What it changes.** No number. json calls `default` only for what it can't write itself,
and here that is this one value, written `true`. The p-value beside it is a numpy float too,
but a numpy float is a Python float, so json wrote it unaided, with the same digits.

## Notes on the run (not deviations)

- **One pass, nothing re-run.** The owner started the run on 2026-11-19 at 22:23 local time
  (03:23 UTC on the 20th), from their terminal, at commit `c783ac0` with a clean tree and the
  freeze's fingerprint (the run line in `runs/resampling/attempts.jsonl` records all three).
  All 726 calls ended with a reply: no API error outlasted the retries, so no cell needed
  Amendment 1's resume passes.
- **Paid: $1.4884** (`runs/resampling/spend.jsonl`), against the $3.00 hard cap and about
  $1.44 expected (section 6).
- **Commits during the run.** At the owner's request, three commits landed in this checkout
  while the run went (`4b6acd0`, `1fd7c85`, `63b1b13`: the IP slack-claim check, and the
  README's headline figure and table). They touched only `scripts/`, `tests/`, `docs/`,
  `results/headline.json`, the README, `CLAUDE.md` and the CI workflow: no file the runner
  reads and no input the freeze fingerprints (`src/opt_agent/`, `requirements.lock`, the
  data, the pre-registration and the freeze were untouched).
- **119 units, against the 120 expected** (section 4). Sample 3 of `complexlp:112` and of
  `complexlp:128` gave no usable model (a constraint, or the objective, uses a variable the
  model never declares), so those two problems have no unit and count as wrong (loud) in R2,
  as section 4 says.
