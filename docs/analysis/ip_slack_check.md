# The IP slack-claim check, on dev (exploratory)

**Status.** Exploratory and post hoc: neither study pre-registered it, and nothing here is a
result of record. The rule (`scripts/ip_slack_check.py`) and its flags (`ip_slack_check.json`,
written by its `flags` step, which reads no label) were committed on 2026-11-19 before its
`score` step read the labels; the results section below is that one step's output. **The
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

<!-- end of results -->
