# A disagreement detector, tested once (exploratory)

**Status.** The rules below, with their code (`scripts/disagreement_detector.py`) and its tests,
were committed on 2026-11-19 before the detector ran on any answer
(`git log -- docs/analysis/disagreement_detector.md`). It then runs **once** over the two
studies' committed answers, with no API call and no tuning after the results are seen: the
script refuses to run again. Exploratory: neither study pre-registered it, and nothing here is
a result of record. The rules are Claude's, written to the owner's outline.

**What was known before the run**, so a reader can judge what the rules could have been fitted
to: the follow-up's descriptive sample agreement (90.9% of single-shot sample pairs agree;
[`docs/followup/RESULTS.md`](../followup/RESULTS.md)) and the silent-failure counts (62 of the
follow-up's 380 single-shot answers, 10 of NL4Opt's 274). How any signal below relates to
whether an answer is right was not computed or looked at.

**The idea** (the owner's): a model that misreads a problem needn't misread it the same way
twice, and an answer from Claude alone, with no solver, needn't share a wrong model's mistake.
So a verified answer that an independent attempt contradicts is suspect. The other detector,
[number coverage](silent_detector.md), asks whether the model holds every number of the text;
this one asks whether independent attempts agree.

## The rules, exactly

1. **The unit** is one single-shot answer that reported an answer (a status, and an objective
   if optimal). Loud failures are left out: there's no answer to flag, as for the number-coverage
   detector.
   - **Follow-up:** every sample (0, 1, 2) of all 128 problems of `runs/followup-test`.
   - **NL4Opt:** the 274 scorable problems of the main test run, `runs/test` (one sample each).
2. **The truth.** A **silent failure** is an answer that's wrong by its study's frozen grader;
   a **right answer** is one that's right. Follow-up: `followup_report.is_right` at the
   `followup-freeze` tag (the raw key, as in `runs/followup-test/followup_report.json`).
   NL4Opt: `scoring.score` at the `m6-freeze` tag, the pre-registered strict scoring (the result
   of record).
3. **The same answer**, with the grader's own rule and tolerance: the same status and, for an
   optimum, objectives within the tolerance, relative and absolute (`math.isclose` with
   `rel_tol` = `abs_tol`). Follow-up: `followup_report.same_answer` at its tag, 1e-4. NL4Opt: the
   same status and `ground_truth.same_value` at its tag, 1e-6. An attempt with no answer (a loud
   failure) differs from any answer.
4. **The signals**, for the single-shot answer to problem p, sample s:
   - **(a) the samples disagree** (follow-up only): the three single-shot samples of p don't
     all give the same answer. It's one flag per problem, shared by its samples.
   - **(b) the checklist disagrees** (follow-up only): checklist revision's answer to (p, s)
     differs from single-shot's. Checklist revision starts from the same first reply, so this
     means its revision was kept with another answer.
   - **(c) the baseline disagrees** (both studies): the no-solver baseline's answer to (p, s)
     differs from single-shot's.
   - **(d) any of them:** (a), (b) or (c) on the follow-up; on NL4Opt, which has neither
     samples nor a checklist condition, (d) is (c).
5. **The populations.** Each study on all its problems, and without its disputed problems:
   those whose wrong answers the failure-type analysis labeled "answer-key dispute"
   ([`failure_types.csv`](failure_types.csv), primary type; Claude's labels, an LLM's, not
   verified by a person). Follow-up: the 13 problems (of the 35 with a wrong answer)
   `complexlp:63`, `complexlp:78`, `complexlp:81`, `complexlp:83`, `complexlp:94`,
   `industryor:17`, `industryor:22`, `industryor:24`, `industryor:26`, `industryor:27`,
   `industryor:28`, `industryor:30`, `industryor:41`. NL4Opt: the 5 problems of the main test run
   (of its 10 with a wrong answer) `-1540907330`, `-2138755435`, `-926961422`, `1605420061`,
   `2078392466` (the analysis's "8 of M6's 18" counts the perturbed run's problems apart).
6. **Reported**, for each study, population and signal: the answers; the **base rate** (silent
   failures over answers); the **flag rate** (flagged answers over answers); **precision**
   (flagged silent failures over flagged answers); **recall** (flagged silent failures over
   silent failures); each with a 95% Wilson interval (`opt_agent.stats.wilson`); and how many
   distinct problems the flagged answers come from. Next to them, the number-coverage
   detector's single-shot answers on the same populations, counted from its committed rows
   (`silent_detector.json`; it ran on the follow-up only), and its pooled figure (precision 19.6%
   against a 16.3% base rate).
7. **Real signal**, decided now: a signal shows real signal if, on the follow-up, the lower end
   of its precision's 95% Wilson interval is above the base rate, both on all 128 problems and
   without the 13 disputed ones. The intervals treat answers as independent, which they
   aren't (three samples share a problem, and (a) is one flag per problem), so they're too
   narrow: passing is a reason for a pre-registered follow-up, not a finding. NL4Opt, with 10
   silent failures, is reported and not tested.
8. **Once.** The results are written to `disagreement_detector.json` and summarized below,
   whatever they are; a weak result is reported as weak.

<!-- results: written by `python scripts/disagreement_detector.py --report` -->

## Results (the one run)

Run once, at `50b30f2` (2026-11-19T20:33:40+00:00). Exploratory; Wilson intervals treat answers as independent, so they're too narrow (rule 7).

**Follow-up, all 128 problems.**

| signal | answers | silent: base rate (95% CI) | flagged: flag rate (95% CI) | precision (95% CI) | recall (95% CI) | flagged problems |
|---|---:|---:|---:|---:|---:|---:|
| (a) the samples disagree | 380 | 62: 16.3% (12.9 to 20.4) | 50: 13.2% (10.1 to 16.9) | 52.0% (38.5 to 65.2) | 41.9% (30.5 to 54.3) | 17 |
| (b) the checklist disagrees | 380 | 62: 16.3% (12.9 to 20.4) | 25: 6.6% (4.5 to 9.5) | 68.0% (48.4 to 82.8) | 27.4% (17.9 to 39.6) | 17 |
| (c) the baseline disagrees | 380 | 62: 16.3% (12.9 to 20.4) | 77: 20.3% (16.5 to 24.6) | 42.9% (32.4 to 54.0) | 53.2% (41.0 to 65.1) | 41 |
| (d) any of them | 380 | 62: 16.3% (12.9 to 20.4) | 101: 26.6% (22.4 to 31.2) | 38.6% (29.7 to 48.4) | 62.9% (50.5 to 73.8) | 47 |
| number coverage (single-shot) | 380 | 62: 16.3% (12.9 to 20.4) | 164: 43.2% (38.3 to 48.2) | 19.5% (14.2 to 26.2) | 51.6% (39.4 to 63.6) | 56 |

**Follow-up, without the 13 disputed problems.**

| signal | answers | silent: base rate (95% CI) | flagged: flag rate (95% CI) | precision (95% CI) | recall (95% CI) | flagged problems |
|---|---:|---:|---:|---:|---:|---:|
| (a) the samples disagree | 344 | 27: 7.8% (5.5 to 11.2) | 38: 11.0% (8.2 to 14.8) | 39.5% (25.6 to 55.3) | 55.6% (37.3 to 72.4) | 13 |
| (b) the checklist disagrees | 344 | 27: 7.8% (5.5 to 11.2) | 19: 5.5% (3.6 to 8.5) | 57.9% (36.3 to 76.9) | 40.7% (24.5 to 59.3) | 14 |
| (c) the baseline disagrees | 344 | 27: 7.8% (5.5 to 11.2) | 63: 18.3% (14.6 to 22.7) | 31.7% (21.6 to 44.0) | 74.1% (55.3 to 86.8) | 35 |
| (d) any of them | 344 | 27: 7.8% (5.5 to 11.2) | 85: 24.7% (20.4 to 29.5) | 28.2% (19.8 to 38.6) | 88.9% (71.9 to 96.1) | 41 |
| number coverage (single-shot) | 344 | 27: 7.8% (5.5 to 11.2) | 142: 41.3% (36.2 to 46.6) | 7.7% (4.4 to 13.3) | 40.7% (24.5 to 59.3) | 48 |

**NL4Opt, all 274 problems.**

| signal | answers | silent: base rate (95% CI) | flagged: flag rate (95% CI) | precision (95% CI) | recall (95% CI) | flagged problems |
|---|---:|---:|---:|---:|---:|---:|
| (c) the baseline disagrees | 274 | 10: 3.6% (2.0 to 6.6) | 8: 2.9% (1.5 to 5.7) | 37.5% (13.7 to 69.4) | 30.0% (10.8 to 60.3) | 8 |
| (d) any of them | 274 | 10: 3.6% (2.0 to 6.6) | 8: 2.9% (1.5 to 5.7) | 37.5% (13.7 to 69.4) | 30.0% (10.8 to 60.3) | 8 |

**NL4Opt, without the 5 disputed.**

| signal | answers | silent: base rate (95% CI) | flagged: flag rate (95% CI) | precision (95% CI) | recall (95% CI) | flagged problems |
|---|---:|---:|---:|---:|---:|---:|
| (c) the baseline disagrees | 269 | 5: 1.9% (0.8 to 4.3) | 8: 3.0% (1.5 to 5.8) | 37.5% (13.7 to 69.4) | 60.0% (23.1 to 88.2) | 8 |
| (d) any of them | 269 | 5: 1.9% (0.8 to 4.3) | 8: 3.0% (1.5 to 5.8) | 37.5% (13.7 to 69.4) | 60.0% (23.1 to 88.2) | 8 |

The number-coverage detector's pooled figure (three conditions): precision 19.6% against a 16.3% base rate.

**Rule 7** (decided before the run): real signal for (a) the samples disagree, (b) the checklist disagrees, (c) the baseline disagrees, (d) any of them.

<!-- end of results -->

## Reading it (written after the run)

- **Real signal, by the rule fixed in advance.** On the follow-up, every signal's precision
  is well above the base rate, with and without the 13 disputed problems, where number
  coverage barely beats it (19.5% against 16.3%) and, without the disputes, doesn't (7.7%
  against 7.8%). The sharpest flag is (b): when the checklist revision changed the answer,
  single-shot's was wrong in 17 of 25 answers. The widest is (d): it flags 101 of the 380
  answers and catches 39 of the 62 silent failures (without the disputed problems, 24 of 27,
  while flagging 85 of 344).
- **What it costs.** None of these signals is free: (a) needs two more samples, (c) one
  no-solver call, (b) a checklist call and a revision. A flag is a warning, not a fix: it says
  which answers a person should check.
- **Too narrow, and one study.** Answers share problems, and (a) is one flag per problem (its
  50 flagged answers come from 17 problems), so the intervals overstate the evidence. Post hoc
  (not part of the declared report): 16 of those 17 problems have a silent single-shot answer,
  but of the 15 problems whose every answered sample is a silent failure, (a) flags only 3. A
  model that misreads a problem the same way every time agrees with itself.
- **The disputed problems behave like key errors.** Post hoc: on the 13 disputed problems, (d)
  flags 15 of their 35 silent failures; on the rest, 24 of 27. Independent attempts agreeing
  on an answer the key rejects is what an answer-key error would look like, but this is
  consistent with the LLM judge's flags, not evidence for them. On NL4Opt, the baseline agreed
  with single-shot on all 5 disputed problems.
- **NL4Opt says little:** with 10 silent failures, (c) flags 8 answers, 3 of them silent.
- **The README's claims stand.** Its limitations say verification can't see a wrong model and
  most failures pass every check; none of these signals is part of the pipeline the studies
  evaluated, so no claim changes and no limitations line was added.

## Proposed next: a pre-registered resampling study (not run)

Rule 7 passed, so this is the confirmatory step it calls for. It's a proposal: nothing is
pre-registered or run, and the paid run is the owner's.

- **Problems and samples.** The follow-up's 121 unexposed test problems, with fresh samples
  only (single-shot samples 3 to 7, baseline sample 3, through the salted cache), so nothing
  this run saw is reused. It replicates across samples, not problems: a set of new problems
  would need its own data review first.
- **Unit:** single-shot sample 3, one per problem, so the units are independent and the
  intervals honest. **Signal:** the five fresh single-shot samples don't all agree, or the
  fresh baseline disagrees with sample 3 (rule 3's "same answer"); the checklist signal (b)
  only if the owner adds its cost below.
- **Primary hypothesis:** a flagged answer is more often a silent failure than an unflagged
  one (one-sided Fisher exact test, alpha 0.05, on all 121 problems; without the 13 disputed
  ones as the secondary analysis). Secondary: majority-of-five versus one sample (the
  follow-up's sign-flip test), and what abstaining on a flag would do (silent failures made
  loud, right answers lost). Power from the follow-up's rates, before the freeze.
- **Cost.** At the follow-up's mean cost per answer ($0.00206 single-shot, $0.00163 baseline,
  $0.00543 checklist revision; `runs/followup-test/results.jsonl`): 121 × (5 × $0.00206 +
  $0.00163) ≈ **$1.44**, or about **$2.10** with one checklist revision per problem. **Hard
  cap: $3.00** (`budget.BudgetedClient`; the run stops cleanly before any call whose worst case
  could cross it, and resumes). Had every answer cost the follow-up's most expensive one, it
  would be $7.58, and the cap would stop it first.
