# The IP slack-claim check, on dev (exploratory)

**Status.** Exploratory and post hoc: neither study pre-registered it, and nothing here is a
result of record. The rule (`scripts/ip_slack_check.py`) and its flags (`ip_slack_check.json`,
written by its `flags` step, which reads no label) were committed and pushed on 2026-11-19
(`4b6acd0`) before its `score` step read the labels; the results section below is that one
step's output, and the reading after it was written once the results were in. **The
labels are Claude's (an LLM's), not a person's**: the explanation checker's evaluation
(`explanation_checker.md`), and Claude wrote the explanations and this rule too.

**Written on the same 88 explanations it's scored on.** The phrasings and the naming rule
below were written from the explanations' text (not their labels), so the numbers will be
better here than on new explanations. What Claude knew of the labels when it wrote the rule:
the explanation checker's published summary (22 of the 88 make a false claim; by Claude's
grouping, 16 of those call a constraint with slack "not limiting" in an integer program) and
its three hand re-solved examples; and, by accident while reading the label files' header,
the first two rows of `review/explain_dev/claims-1.csv` (one false claim, the budget example
below, and one explanation without).

## Why

The explanation checker found no wrong number on dev, but about one explanation in four made
a false claim with every number right, nearly all of them LP intuition applied to an integer
program: a constraint with slack called "not limiting" when dropping it changes the integer
optimum (`explanation_checker.md`; open item 16 in `docs/HANDOFF.md`). For example: "The $200
budget is not the bottleneck, since $2 of it stays unspent" (without the budget, that model
is unbounded). No number check can see that. This check tests each such claim the way the
labelers did, by solving the model again without the constraint. It takes the claims from the
saved explanations only (`runs/explain-dev/explanations.jsonl`, which holds each one's model
and solver facts): no API call, no new explanation.

## The rule

1. **Claims.** Each explanation is cut into sentences, and each sentence into clauses at a
   semicolon or at "while", "but" or "whereas" (a contrast usually turns from one constraint
   to another: "the budget isn't the limit; the trips are"). A clause makes a claim where one
   of five phrasings denies that a constraint limits the answer: "not the bottleneck / limit /
   constraint / limiting factor", "not binding"; "not what limits / holds ... back /
   restricts"; "does not limit / restrict / hold back", "isn't limiting"; "neither (one) is
   limiting / holding ... / the main constraint", "none of those rules restrict"; and
   "non-binding". "No constraint is fully used" isn't a claim: it's a fact about slack, and the
   solver's facts make it true.
2. **Which constraints.** Those the clause names before the phrase ("the budget isn't the
   limit"), or, if it names none there, those it names after it ("the other rules are not
   holding it back: the manual-use cap has 2 spare, ..."). A clause names a constraint by its
   name as a phrase (without "limit", "rule", "requirement", "constraint" or "cap" at either
   end, which the text may word differently), or by every distinctive word of the name (not
   words such as limit, minimum, total, time or hours, which say what kind of constraint it is
   rather than which one), unless those words are only part of what another named constraint
   matched. Names, text and plurals are compared in lower case, without possessives or numbers.
3. **The re-solve.** Integer programs only (73 of the 88): in an LP a constraint with slack
   never limits, since the optimum stays optimal without it. The model without the named
   constraint is solved with CBC, cross-checked by HiGHS and the arithmetic checks
   (`ground_truth.solve_checked`). A claim is **flagged** when the optimum changes: a
   different objective at the ground truth's tolerance (1e-6, relative and absolute), or none
   (unbounded). It's **undetermined** when the solvers disagree or a check fails on either
   solve. Dropping is the labelers' "dropping or loosening" at its strongest: a loosening that
   changes the optimum enlarges the feasible set, and dropping enlarges it further.
4. **An explanation is flagged** when any of its claims is.

## What's reported

- Explanation by explanation, flagged against labeled with a false claim (any false claim:
  the labels as they are, including the few that aren't about slack, which this rule can't
  see): **precision** (labeled false, of those flagged) and **recall** (flagged, of those
  labeled false), and recall among integer programs, each with its 95% Wilson interval
  (`opt_agent.stats.wilson`), whatever they show.
- Claims found, re-solved, flagged and undetermined, by wording: "limit" or "binding" (the
  owner asked about both "not limiting" and "non-binding" claims).
- Each flagged explanation the labels call fine, and each labeled false claim it doesn't flag,
  by problem.

<!-- results: added by the score step -->

## Results

88 explanations (73 of them integer programs). Labels by Claude (an LLM, not a person). Exploratory.

| claims found | limit wording | binding wording |
|---|---:|---:|
| in all explanations | 70 | 5 |
| in integer programs (re-solved) | 60 | 5 |
| flagged: the optimum changes without the constraint | 13 | 0 |
| undetermined (the solvers disagree or a check fails) | 0 | 0 |

Explanations flagged: 13; labeled with a false claim: 22.

- **Precision** (labeled false, of those flagged): 13 of 13, 100.0% (77.2 to 100.0).
- **Recall** (flagged, of those labeled false): 13 of 22, 59.1% (38.7 to 76.7).
- **Recall in integer programs:** 13 of 21, 61.9% (40.9 to 79.2).
- Flagged but labeled fine: none.
- Labeled false but not flagged: -1091195781, -1362864316, -1603423876, -1910834629, -279354943, -668544637, -927748635, 709701618, 892653388.

<!-- end of results -->

## Reading it (written after the scoring)

Post hoc, Claude's reading of the labelers' notes (an LLM's, not a person's), recorded under
`post_hoc` in the JSON; none of it is part of the declared report.

- **Every flag was a false claim the labelers found.** In all 13 flagged explanations the
  flagged constraint is the one the labeler's note names, and where the note gives the
  optimum without it (found by enumeration), the re-solve finds the same one: unbounded
  twice, $25,000, 202 people, 0 lines, 2,500 g of protein, 46 units. Where a sentence made two
  claims and the note says one half is true, the re-solve holds that half too. That agreement
  is expected: the labelers settled slack claims by the same test, dropping the constraint, so
  what this measures is mostly whether the rule finds the claim.
- **It found 13 of the 16 slack claims** (81.2%, 57.0 to 93.4), on the text it was written
  from. Two misses name the constraint in other words ("the rule that at least 750 units be
  shipped" is `units transported`; "the goods requirement" is `goods_transported`), and one
  makes the claim without a denying phrase (after listing the slack, it says the whole-number
  requirement "is what limits the result most"; dropping the capital limit takes the optimum
  from $9,975 to $20,700).
- **The other 6 false claims aren't about slack**, so no re-solve can see them: two describe a
  binding minimum as a cap, and one each gives a wrong reason for the missing shadow prices,
  reads a slack as a share gap, compares limits across units, or states a plan and takes it
  back (the one LP).
- **"Not binding" claims were all true here** (5, none flagged): every flag came from "not
  limiting" wording. In the solver's sense a constraint with slack isn't binding, so the
  wording that misleads is the one about what limits the answer.
- **What it suggests.** Re-solving settles a slack claim, but finding the claim in free text
  is the weak part: a check like this one misses claims worded in ways its rule didn't
  foresee, and it was tuned on these very explanations. Giving the explainer each constraint's
  computed effect before it writes (open item 16's other options) avoids parsing altogether.
- **Weak evidence, as the status says:** one sample per problem, dev only, the labels an LLM's
  with one labeler per batch, and the rule written on the same text it's scored on.
