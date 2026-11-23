# The second-model study: deviations from the pre-registration

Section 7 of [`docs/SECOND_MODEL_PREREGISTRATION.md`](../SECOND_MODEL_PREREGISTRATION.md):
anything that runs differently from what's written there, with its Amendment 1, is recorded
here, with what was planned, what happened and what it changes. The results:
[`RESULTS.md`](RESULTS.md), from `results/second_model.json`. Claude (an LLM) checked the run
and the report against the pre-registration on 2026-11-22, after the owner's run; these two are
everything it found that differs, and neither changes a number in the report.

## 1. Stage 2's cut-off replies aren't in the report (2026-11-22, found checking it)

**Planned.** Section 3's declared differences say that "output tokens (thinking included) and
cut-off replies are reported for each model", and Amendment 1 says section 3's declared
differences apply to stage 2 too.

**What happened.** The frozen analysis counts cut-off replies only in stage 1 (its
`failures`, where both models have none). For stage 2 it reports each model's output tokens,
but no count of cut-off replies or of any other reply without an answer. Its tests, written
before the freeze, don't ask for them, so this wasn't caught before the run.

**What's done instead.** They're counted here, from the reason each item records, with the
frozen analysis untouched: Sonnet's from `runs/second-model/results.jsonl`, Haiku's from its
pairing record's sample-0 items for the same 121 problems (`runs/followup-test/results.jsonl`,
the latest line per pair).

| no-solver replies, of the 121 | Claude Sonnet 5.5 | Claude Haiku 5.5, sample 0 |
|---|---:|---:|
| cut off at `max_tokens` (16,000) | 12 | 4 |
| "optimal" with no objective value (unusable) | 6 | 1 |
| an answer | 103 | 116 |
| refusals | 0 | 0 |

Each of Sonnet's 18 counts as wrong, as section 4 says of any reply with no answer, and the
report's stage-2 comparison already counts them so. In stage 1 neither model had a cut-off
reply (the report's own count): Sonnet's 3 loud failures are unusable models (twice a
variable used but never declared, once an objective listing variables more than once), and
Haiku's 1 is an objective with no nonzero terms.

**What it changes.** No number in the report. For scale (post hoc, Claude's arithmetic, not
pre-registered): had all 18 been right answers, Sonnet's no-solver count would be 68 of 121,
still below its 88 single-shot, so the replies with no answer don't account for stage 2's
difference by themselves.

The count, from the repository's root:

```bash
python - <<'EOF'
import collections, json
run = [json.loads(line) for line in open("runs/second-model/results.jsonl")]
problems = set(json.load(open("runs/second-model/manifest.json"))["problems"])
haiku = {}
for line in open("runs/followup-test/results.jsonl"):  # the latest line per pair
    e = json.loads(line)
    if e["kind"] == "item" and e["sample"] == 0 and e["problem_id"] in problems:
        haiku[e["problem_id"], e["condition"]] = e
for model, items in (("sonnet", [e for e in run if e["kind"] == "item"]),
                     ("haiku", list(haiku.values()))):
    for condition in ("single-shot", "baseline"):
        found = [e for e in items if e["condition"] == condition]
        reasons = collections.Counter(e["reason"] for e in found if e["status"] is None)
        print(model, condition, len(found), dict(reasons))
EOF
```

Refusals: no reply in `runs/second-model/cache` has `stop_reason` "refusal" (230 ended with
`end_turn`, 12 with `max_tokens`), and none in `runs/followup-test/cache` does either.

## 2. A number of this study in the README is checked against another record (2026-11-22)

**Planned.** Section 7: "any number of this study in the README is checked by a test against
`results/second_model.json`".

**What happened.** The owner asked for Sonnet's rows in the README's cost and latency table,
whose columns are the cost per answer, the median latency and the 90th percentile (p90). The
report has the first two for each condition, but no p90.

**What's done instead.** `scripts/headline.py` computes Sonnet's two rows from the run's log
(`runs/second-model/results.jsonl`) the way it computes Haiku's: the cost per answer, and the
median and p90 by numpy's linear percentile, and only after each condition's total cost and
median latency come out equal to `results/second_model.json`'s, so the rows come from the same
answers, counted the same way. The README test checks the whole table against
`results/headline.json`, as it does for Haiku's rows (the owner's rule for that table,
2026-11-19), and `tests/test_headline.py` checks Sonnet's totals and medians there against
`results/second_model.json`.

**What it changes.** No number in the report. Two numbers in the README, Sonnet's p90
latencies, are checked against `results/headline.json` only; every other number of this
study in the README is a value in `results/second_model.json`.

## Notes on the run (not deviations)

- **One command, both stages, nothing re-run.** The owner ran it from their terminal at tag
  `second-model-freeze-2` (commit `b9d3e20`), with a clean tree and the freeze's fingerprint
  (the run lines in `runs/second-model/attempts.jsonl` record all three). Stage 1 ran on
  2026-11-22 from 21:59 to 22:16 Eastern time (02:59 to 03:16 UTC on the 23rd), and stage 2,
  which started because stage 1 had settled all 121 problems, from 22:16 to 22:51. Both took
  the problems in the follow-up's run order. All 242 calls ended with a reply: no API error, no
  retry wait, no resume pass.
- **Paid: $5.7177** (`runs/second-model/spend.jsonl`: 242 calls, every one
  `claude-sonnet-5-5`): $2.4154 in stage 1, against its $11.00 cap, and $3.3023 in stage 2,
  with $13.50 the cap for both. Amendment 1 expected about $5.18 and $4.14, at Haiku's token
  counts; Sonnet wrote fewer output tokens than Haiku in both stages. The most expensive call,
  $0.1635, was a no-solver reply cut off at 16,000 output tokens.
- **The checkpoints** (the two checkpoint lines in `runs/second-model/results.jsonl`): stage
  1's first 10 problems projected $1.92 for stage 1, 0.80 of what it cost, and stage 2's
  projected $4.22 for both stages, its own part ($1.80) 0.55 of what stage 2 cost. Both
  continued. As Amendment 1 says, the checkpoint is a noisy early stop and the hard caps are
  the guarantee; the spend never came near either cap.
- **The same environment as Haiku's run:** Python 3.13.7 on macOS 26.6.2 (arm64), and the
  pipeline's packages at the versions section 3 lists (both runs' `attempts.jsonl` record
  them).
- **When:** Amendment 1 moved the run from December to "now", so it ran on 2026-11-22, not in
  December as section 3's declared differences and section 6 first said. Haiku's answers are
  from the follow-up's run, 2026-11-13 and 14 (Eastern time).
- **The report and the commit.** The frozen analysis wrote `results/second_model.json` at the
  tag (`python -m opt_agent.second_model_report`), and the owner committed it with the run in
  `a78a2af`, which adds only `runs/second-model/` and that file. With no API key,
  `scripts/reproduce.py` replays all 242 answers from the run's cache through the tag's code,
  every recorded field back, and rebuilds the file byte for byte (checked on 2026-11-22, here
  and in CI's reproduce job).
