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

## Results

Not run yet.

<!-- end of results -->
