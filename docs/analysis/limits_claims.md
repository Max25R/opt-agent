# ADR-0009 on dev: claims about what limits an integer program, before and after (exploratory)

**Status.** Exploratory and post hoc, on the dev split, one sample per problem: nothing here
is a result of record. It measures [ADR-0009](../adr/0009-what-limits-an-integer-program.md),
which gives the explainer the solver's own test of what limits an integer program. The script
(`scripts/limits_claims.py`) was written before its first run, and the new explanations
weren't read before the counts were. No person labeled anything: the claims are found by a
rule Claude (an LLM) wrote, and judged by the solver's facts. The reading after the results
was written once they were in, and is Claude's.

**Headline: 13 → 4.** By the same rule, judged by the solver's facts, the integer programs'
explanations with a false "not limiting" claim went from 13 to 4 (of 73). What the 4 are is a
post hoc note, below.

## The two runs

- **Before:** `runs/explain-dev` (2026-11-19), the explanation checker's run
  ([`explanation_checker.md`](explanation_checker.md)): the explainer saw the values, the
  objective, the binding constraints, the slack and shadow prices.
- **After:** `runs/explain-dev-limits` (the owner's paid run of 2026-11-20,
  `scripts/paid_explain_limits.py`): the same answers explained again, and for an integer
  program the explainer also saw, for each constraint, whether the optimum would be better
  without it or with its limit one unit further out (`src/opt_agent/limits.py`).

Both runs explain the same models (the formulations replayed from one cache; checked), and an
LP's request didn't change, so its explanation is the same text in both (checked). The
comparison is over the integer programs.

## The rule

- **Claims:** `scripts/ip_slack_check.py`'s rule, unchanged
  ([`ip_slack_check.md`](ip_slack_check.md)): each clause that says a constraint doesn't
  limit the answer ("not the bottleneck", "isn't limiting", "not what holds it back", ...) or
  isn't binding, and the constraints it names. It was written on the first run's text, so it
  can miss wording only the new text uses; on that text it found most slack claims, not all.
- **Verdicts,** from the after run's facts (the same models): "X doesn't limit the answer" is
  **false** when the optimum is better without X (`dropped_improves`), **unknown** when the
  solvers couldn't tell, and true otherwise; "X isn't binding" is false when X binds.
- **Reported:** per run, the explanations with a false claim and the claims by wording and
  verdict; the paired change by problem; and the numbers the number check flags, to see
  whether the new facts brought unbacked numbers. Counts only.
- `python scripts/limits_claims.py --verify` also re-solves every integer program's limits
  and requires the run's recorded ones.

<!-- results: written by scripts/limits_claims.py -->

## Results

Dev split, exploratory: 73 integer programs, one explanation each per run; the 15 LP explanations are the same text in both runs. 44 of the 73 have a constraint with slack that still limits the answer (the trap ADR-0009 is about).

| over the integer programs | before | after |
|---|---:|---:|
| explanations with a claim the rule finds | 42 | 53 |
| **explanations with a false claim** | 13 | 4 |
| "not limiting" claims found | 60 | 72 |
| ... false (better without the constraint) | 13 | 5 |
| ... true | 47 | 67 |
| ... unknown (the solvers couldn't tell) | 0 | 0 |
| "not binding" claims found | 5 | 0 |
| ... false (the constraint binds) | 0 | 0 |
| numbers the number check flags | 5 | 3 |

Paired, by problem: 13 explanations made a false claim before and none after, 4 the reverse, 0 made one in both runs, and 56 in neither.

<!-- end of results -->

## Reading it (written after the counts; Claude's reading, an LLM's, not a person's)

- **The headline, 13 → 4, is the rule's count,** and each of the 13 from before is fine
  after. The before count is the IP slack-claim check's 13 flags, which the
  explanation checker's labels all confirmed.
- **Post hoc note: in this reading, the 4 left are the rule's mistakes, not the explainer's.**
  It doesn't change the headline, which is the rule's count. Each new explanation says, in
  one sentence, which constraints limit the answer and which don't ("the worker supply is the
  real limit"; "the two minimum-count rules do not limit it"). The rule pins a "do not limit"
  on every constraint named before it in the clause, so it also pinned it on the one the
  sentence had just called limiting. In all 4, the constraints the sentence calls not limiting
  have `dropped_improves` false, so by this reading the after run has no false "not limiting"
  claim among those the rule found.
- **What could still hide:** pinning a claim on an extra constraint can only add a flag, so a
  false claim slips through only if the rule misses its phrasing or the name of its
  constraint. That recall was 13 of 16 on the first run's text (the IP check's reading) and
  isn't measured on the new text, which words things differently: of the rule's phrase
  matches, more name several constraints after (24 of 88) than before (17 of 46).
- **The new facts are used.** The after run makes more claims the rule finds (72 "not
  limiting" claims against 60), and they're true more often (67 against 47); several
  explanations now say that a constraint limits the result even with slack left, or that one
  more unit of a limit wouldn't help while dropping it would. The number check flags no more
  numbers than before (3 against 5).
- **Weak evidence:** dev only, one sample per problem, the rule written on the first run's
  text, and one reader. It says ADR-0009 helps on dev; a test would need fresh problems and a
  person's labels.
