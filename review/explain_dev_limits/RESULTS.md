# The checker's blind labels on ADR-0009's regenerated explanations: results

**Exploratory, dev only, one sample per problem.** The labels are Claude's, an LLM's, not a
person's: four Claude subagents, one batch each, blind, by the first labeling's rules and
sheets (2026-11-21; how they were kept blind is in
[`limits_claims.md`](../../docs/analysis/limits_claims.md), last section). The numbers below
are written by `python scripts/explanation_checker.py score --after` from
[`limits_checker.json`](../../docs/analysis/limits_checker.json), and so are those of
[ADR-0009's update](../../docs/adr/0009-what-limits-an-integer-program.md#update-2026-11-21-blind-relabeling),
which makes the labels' count the headline (the owner's call). No API call.

**One label per explanation: a false claim,** any sentence that says something false about the
solution or the problem while its numbers are right
([`explanation_checker.md`](../../docs/analysis/explanation_checker.md), "The labels"). There
is no "not limiting" label of its own, so the headline counts false claims of any kind. The
rule (`scripts/limits_claims.py`) flags only false "not limiting" claims, so its recall is
against every false claim, as in [`ip_slack_check.md`](../../docs/analysis/ip_slack_check.md).
Its precision and recall, the pairs and the kinds were added after the labels were in (the
owner's requests), so they're post hoc.

<!-- results: written by scripts/explanation_checker.py score --after -->

**The consistency rule:** 15 of the 15 LP entries both sheets share got the first labeling's labels (13 needed), so by the pre-set rule the result is **conclusive**.

**Headline:** by the blind labels, the integer programs' explanations with a false claim, of any kind, went 21 → 10 of 73 (22 → 11 of all 88, LPs included). Exploratory, dev only, one sample per problem.

| over the 73 integer programs | first explanations | regenerated |
|---|---:|---:|
| labeled with a false claim (any kind) | 21 | 10 |
| flagged by the rule (a false "not limiting" claim) | 13 | 4 |
| the rule's precision (labeled false, of those flagged) | 13 of 13, 100.0% (77.2 to 100.0) | 1 of 4, 25.0% (4.6 to 69.9) |
| the rule's recall (flagged, of those labeled false) | 13 of 21, 61.9% (40.9 to 79.2) | 1 of 10, 10.0% (1.8 to 40.4) |

Paired by problem over the 73 integer programs, descriptive counts only: 17 fixed (a false claim before, none after), 6 newly false, 4 stayed false, and 46 fine in both.

Post hoc (Claude's reading of the labelers' notes, an LLM's, not a person's): the rule's 3 false positives are 3 misattributions (a "does not limit" pinned on a constraint the explanation calls limiting), and its 9 misses are 4 "loosening wouldn't help" claims (true for one unit, false for a larger loosening); 3 changes whose effect is stated the wrong way round; and 2 misstatements of what's fully used, none of them a claim its phrasings cover.

The rule flags, but the labels call fine: -920265113, -1633326119, -654999513. Labeled false, but not flagged: 368302984, 690843809, 471112257, -1211890581, -1829385566, 1738481857, -537539268, -594806556, 709701618.

<!-- end of results -->

## Notes (post hoc; Claude's reading of the labelers' notes, an LLM's, not a person's)

- **Complete; nothing relabeled.** All 88 explanations had their labels before this note
  (every number label on its sheet's number, one false-claim label each), so none was added
  or changed. Each labeler saw its sheet's entries in the first sheets' order, as the first
  labelers had, not shuffled.
- **The rule's one hit is a different claim.** In 1947901559 the rule read "the minimum of 3
  XYZ servings do not limit the result" as naming the XYZ share cap too (by its word "XYZ"), a
  cap the explanation calls limiting; the labeler's false claim is that cap's slack, in
  servings, worded as a share gap, and the labeler found its other claims true. With the
  three false positives, that bears out the post hoc note in `limits_claims.md`: what the rule
  flags in the regenerated explanations is its own misattributions.
- **No false claim the labelers give is a limiting constraint said not to limit,** the error
  in 16 of the first labeling's 21 (Claude's grouping then, in `explanation_checker.md`). The
  "loosening wouldn't help" claims (368302984, 471112257, -1829385566, -594806556, all batch
  4's, each called borderline in its note) say a constraint limits, but that loosening it
  wouldn't help: true for one unit, false for a larger loosening. They state
  `loosened_improves`, a one-unit test, without its "one unit", which ADR-0009 lists to
  revisit.
