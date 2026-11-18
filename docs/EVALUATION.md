# Evaluation on NL4Opt (milestone 6)

The study's full write-up. It was the README's Evaluation section until the README was
rewritten for a short read on 2026-11-15, and moved here unchanged. The final review the same
day added the pre-registered rows it had left out, the integrality rule's bug, and links to
Amendments 4 and 5. `tests/test_readme_numbers.py` checks every number here against
`results/eval.json`, as the pre-registration's section 7 asks of the README. `python scripts/reproduce.py` rebuilds that
file from the committed runs with the frozen code.

The NL4Opt test split has 274 scorable problems, and every condition used Claude Haiku 5.5.
The inputs (prompts, code, data and ground truth) were frozen before the run, and the
analysis was pre-registered ([`docs/PREREGISTRATION.md`](PREREGISTRATION.md)). An
answer is correct if its status and objective match the answer key (relative tolerance
1e-6), or match one of the other readings the pre-registration accepts: the strict reading of
"more than", the "=" reading of a ratio such as "twice as many", or the other optimum of a
problem labeled `either` (integer or continuous). Every hand check below (the failure labels,
the blind grading) was done by LLM judges, not a person. Every number in this section comes from [`results/eval.json`](../results/eval.json),
and a test checks it.

| condition | accuracy (95% Wilson) | silent / loud failures | perturbed set (n = 240) | cost | latency p50 / p95 |
|---|---|---|---|---|---|
| no-solver baseline | 96.4% (93.4–98.0%) | 10 / 0 | 97.1% | $0.124 | 3.8 s / 8.1 s |
| single-shot | 96.4% (93.4–98.0%) | 10 / 0 | 96.7% | $0.150 | 3.6 s / 6.7 s |
| self-correction | 96.4% (93.4–98.0%) | 10 / 0 | 97.1% | $0.167 | 3.7 s / 9.5 s |
| *exploratory, post hoc:* the failures LLM judges flagged as key errors (not verified by a person) counted as correct | 98.5% (96.3–99.4%) in each | | | | |

**No detectable difference on NL4Opt.** All three conditions got 264 of 274 right. None of
the 6 pre-registered McNemar tests comes close (every p = 1, with at most 3 discordant
pairs in any comparison). That isn't evidence that the conditions are equivalent. But the
baseline, which answers directly with no solver, matched the solver conditions. That
suggests NL4Opt is saturated as a test of what a solver adds.

**The other pre-registered rows** (Amendment 2). The first write-up left them out, and
[Amendment 4](amendments/amendment-4.md) reports them. Neither replaces the result of
record.

| condition | lenient: integrality not graded | without the 8 disputed reviews (n = 266) |
|---|---|---|
| no-solver baseline | 96.4% (93.4–98.0%), 264/274 | 97.7% (95.2–99.0%), 260/266 |
| single-shot | 97.1% (94.3–98.5%), 266/274 | 97.7% (95.2–99.0%), 260/266 |
| self-correction | 97.1% (94.3–98.5%), 266/274 | 97.7% (95.2–99.0%), 260/266 |

Lenient scoring accepts the optimum under either integrality (LP or integer), with nothing
else changed. It moves both solver conditions to 266 and leaves the baseline at 264. Its
McNemar tests, exploratory and without Holm, give p = 1 in every comparison too.

**Two LLM judges flagged most shared failures as answer-key errors, not verified by a
person (exploratory, post hoc).** 8 problems were wrong in all three conditions. Two LLM
judges labeled each failure on its own, and both flagged 6 of the 8 as answer-key errors:
a key that is wrong, or that rejects a reading the text supports. No person has checked
those flags. Counting those 6 as correct gives 98.5% in every condition, which would leave
4 failures per condition. This row was added after the results were seen, and it is
not a pre-registered result.

**The integrality rule's bug (exploratory, post hoc).** 4 of those 6 flagged keys come from
one bug: the rule that labels integrality read wording such as "units of chicken meat" as
continuous, which also switched off the strict reading of "must be larger than" and cost 4
answers per condition ([deviations](amendments/DEVIATIONS.md), section 3). Relabeling those
4 problems gives 268/274, 97.8% (95.3–99.0%), in every condition (Amendment 4). 264/274
stays the result of record.

**Same score, different failures.** By the judge of record's labels, the baseline's 4
remaining failures are 2 missing constraints, 1 arithmetic slip and 1 wrong coefficient.
The solver conditions' 4 are 2 integrality errors, 1 invented constraint (a stated
preference, "prefers", made a requirement) and the same wrong coefficient. With 4 failures
per condition, this is a description, not a finding.

**0 loud failures, and why that's not reassuring.** Every answer from the solver
conditions was confirmed: CBC and HiGHS agreed, and the arithmetic checks passed. But
verification checks the solution of Claude's own formulation, not whether that formulation
matches the text. So every modeling error passed every check, and all 10 failures per
condition were silent.

**No sign of memorization.** On 240 problems with their numbers changed and their answers
recomputed, accuracy held (96.7–97.1%). No condition gave the original problem's answer to
any changed problem.

**Self-correction barely mattered.** It revised 23 answers across both runs and changed 1
outcome. It cost 7% more than single-shot across both runs (11% on the test run).

**Limitations.**
- **The judges aren't independent proof.** The judge of record is Claude, the same model
  family as the agent, and both judges saw the same inputs and row-pairing hints, so their
  20/20 agreement isn't independent proof.
- **One answer counted as correct has a bug.** Of the 6 answers that count as correct,
  `431521997`'s model has an error that doesn't change its answer (an upper limit
  replaced by a trivial constraint), and blind grading graded it wrong.
- **The answer key can be wrong without the score showing it.** On `-2001553884` the
  reference model leaves out a land limit. The limit doesn't bind, so the score can't see
  the error.
- **"Prefers" is a systematic weakness.** Reading a stated preference as a requirement
  cost one problem in both solver conditions. The same mistake turned up in a model
  that was scored right, because there the constraint doesn't bind.
- **Blind grading, by an LLM judge.** The grader was Claude Opus 5.5 in a claude.ai chat,
  not a person. It agreed with the automatic score on 29 of 30 models scored right and 5 of
  10 scored wrong. All 5 wrong-side disagreements are the answer-key
  errors above; the 1 right-side disagreement is a correct answer from a model with a
  non-binding bug.

**Cost.** Both test runs together (the main one and the perturbed one) cost $0.52 in API
calls.

**The rules.**
- Amendments 1 and 2 are at the end of the
  [pre-registration](PREREGISTRATION.md#amendments).
- [Amendment 3](amendments/AMENDMENT_3.md): the exploratory row and blinded judge prompts.
- [Amendment 4](amendments/amendment-4.md): the pre-registered rows the first write-up left
  out, and the corrected-labels row.
- [Amendment 5](amendments/amendment-5.md): our answers against an outside answer key
  (LLM4OR's cleaned NL4Opt), exploratory.
- The [note on deviations](amendments/DEVIATIONS.md), including the integrality rule's bug.
