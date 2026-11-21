# The checker's blind labels on ADR-0009's regenerated explanations: results

**Exploratory, dev only, one sample per problem.** The labels are Claude's, an LLM's, not a
person's: four Claude subagents, one batch each, blind, by the first labeling's rules and
sheets (2026-11-21; how they were kept blind is in
[`limits_claims.md`](../../docs/analysis/limits_claims.md), last section). The numbers below
are written by `python scripts/explanation_checker.py score --after` from
[`limits_checker.json`](../../docs/analysis/limits_checker.json). No API call.

**One label per explanation: a false claim,** any sentence that says something false about the
solution or the problem while its numbers are right
([`explanation_checker.md`](../../docs/analysis/explanation_checker.md), "The labels"). There
is no "not limiting" label of its own: the first labeling's 22 counts any false claim in all 88
explanations, 21 of them in the 73 integer programs. The rule (`scripts/limits_claims.py`,
ADR-0009's 13 → 4) flags only false "not limiting" claims, so its recall is against every
false claim, as in [`ip_slack_check.md`](../../docs/analysis/ip_slack_check.md). Its precision
and recall were added after the labels were in (the owner's request), so they're post hoc.

<!-- results: written by scripts/explanation_checker.py score --after -->

**The consistency rule:** 15 of the 15 LP entries both sheets share got the first labeling's labels (13 needed), so the before/after comparison is **comparable**.

| over the 73 integer programs | first explanations | regenerated |
|---|---:|---:|
| labeled with a false claim (any kind) | 21 | 10 |
| flagged by the rule (a false "not limiting" claim) | 13 | 4 |
| the rule's precision (labeled false, of those flagged) | 13 of 13, 100.0% (77.2 to 100.0) | 1 of 4, 25.0% (4.6 to 69.9) |
| the rule's recall (flagged, of those labeled false) | 13 of 21, 61.9% (40.9 to 79.2) | 1 of 10, 10.0% (1.8 to 40.4) |

Of all 88 explanations, LPs included, 22 were labeled with a false claim before and 11 after. Regenerated explanations the rule flags but the labels call fine: -920265113, -1633326119, -654999513; labeled false but not flagged: 368302984, 690843809, 471112257, -1211890581, -1829385566, 1738481857, -537539268, -594806556, 709701618.

<!-- end of results -->

## Notes (post hoc; Claude's reading of the labelers' notes, an LLM's, not a person's)

- **Complete; nothing relabeled.** All 88 explanations had their labels before this note
  (every number label on its sheet's number, one false-claim label each), so none was added
  or changed. Each labeler saw its sheet's entries in the first sheets' order, as the first
  labelers had, not shuffled.
- **The rule and the labels share no "not limiting" claim.** The rule's one hit, 1947901559,
  is a different claim. The rule read "the minimum of 3 XYZ servings do not limit the result"
  as naming the XYZ share cap too (by its word "XYZ"), a cap the explanation calls limiting;
  the labeler's false claim is that cap's slack, in servings, worded as a share gap, and the
  labeler found its other claims true. The other three flags (-920265113, -1633326119,
  -654999513) are labeled fine. So the blind labels bear out the post hoc note in
  `limits_claims.md`: the rule's 4 are its own misattributions.
- **No false claim the labelers give is a limiting constraint said not to limit,** the error
  in 16 of the first labeling's 21 (Claude's grouping then, in `explanation_checker.md`).
  Four (368302984, 471112257, -1829385566, -594806556, all batch 4's) say a constraint limits
  but that loosening it wouldn't help: true for one unit, false for a larger loosening. They
  state `loosened_improves`, a one-unit test, without its "one unit" (ADR-0009 lists this to
  revisit), and the rule's phrasings don't include "wouldn't help", so it finds none of them.
  The other six reverse a change's direction (a tightening said to improve the answer:
  690843809, 709701618; dropping a limit said to worsen it: 1738481857), misstate what's
  fully used (a ratio called the only fully used constraint while a variable bound is too:
  -1211890581; a binding rule called not fully used: -537539268), or word a slack as a share
  gap (1947901559).
- **What it means.** Both counts fall, the rule's flags and the labels' false claims (the
  table), but by these labels the rule's after count isn't the false claims left: none of its
  4 is one, and the ones the labels find are of kinds it doesn't read. The caveats in
  `limits_claims.md` hold: Claude's labels, one labeler per batch, dev only, one sample.
