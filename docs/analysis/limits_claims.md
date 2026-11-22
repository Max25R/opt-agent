# ADR-0009 on dev: claims about what limits an integer program, before and after (exploratory)

**Status.** Exploratory and post hoc, on the dev split, one sample per problem: nothing here
is a result of record. It measures [ADR-0009](../adr/0009-what-limits-an-integer-program.md),
which gives the explainer the solver's own test of what limits an integer program. The script
(`scripts/limits_claims.py`) was written before its first run, and the new explanations
weren't read before the counts were. No person labeled anything: the claims are found by a
rule Claude (an LLM) wrote, and judged by the solver's facts. The reading after the results
was written once they were in, and is Claude's.

**Headline (since 2026-11-21, the owner's call): 21 → 10,** by the explanation checker's blind
labels: the integer programs' explanations with a false claim of any kind (of 73; the last
section, and [ADR-0009's update](../adr/0009-what-limits-an-integer-program.md#update-2026-11-21-blind-relabeling)).
The rule's own count, below, was the headline until then; against those labels it doesn't
measure the regenerated explanations
([`review/explain_dev_limits/RESULTS.md`](../../review/explain_dev_limits/RESULTS.md)).

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

- **The rule's count went 13 → 4** (the headline until the blind relabeling, which replaced
  it), and each of the 13 from before is fine after. The before count is the IP slack-claim
  check's 13 flags, which the explanation checker's labels all confirmed.
- **Post hoc note: in this reading, the 4 left are the rule's mistakes, not the explainer's.**
  It doesn't change the rule's count. Each new explanation says, in
  one sentence, which constraints limit the answer and which don't ("the worker supply is the
  real limit"; "the two minimum-count rules do not limit it"). The rule pins a "do not limit"
  on every constraint named before it in the clause, so it also pinned it on the one the
  sentence had just called limiting. In all 4, the constraints the sentence calls not limiting
  have `dropped_improves` false, so by this reading the after run has no false "not limiting"
  claim among those the rule found.
- **What could still hide:** pinning a claim on an extra constraint can only add a flag, so a
  false claim slips through only if the rule misses its phrasing or the name of its
  constraint. That recall was 13 of 16 on the first run's text (the IP check's reading) and
  wasn't measured on the new text, which words things differently: of the rule's phrase
  matches, more name several constraints after (24 of 88) than before (17 of 46). It has been
  since, against the explanation checker's blind labels below (post hoc:
  [`review/explain_dev_limits/RESULTS.md`](../../review/explain_dev_limits/RESULTS.md)).
- **The new facts are used.** The after run makes more claims the rule finds (72 "not
  limiting" claims against 60), and they're true more often (67 against 47); several
  explanations now say that a constraint limits the result even with slack left, or that one
  more unit of a limit wouldn't help while dropping it would. The number check flags no more
  numbers than before (3 against 5).
- **Weak evidence:** dev only, one sample per problem, the rule written on the first run's
  text, and one reader. It says ADR-0009 helps on dev; a test would need fresh problems and a
  person's labels.

## The explanation checker's own labels on the regenerated run (run 2026-11-21)

The counts above come from a rule. The first run's 22 false claims came from the explanation
checker's evaluation ([`explanation_checker.md`](explanation_checker.md)): four Claude
subagents, one batch each, labeled sheets by written rules, in a session, with no API call.
To compare like with like, the regenerated explanations get the same checker:

- **The sheets:** `python scripts/explanation_checker.py sheet --after` wrote
  `review/explain_dev_limits/` (committed blank, before any label): the same format and
  batches, the same facts (not the new limits, which the first sheets didn't have), and none
  of the checker's flags. The 15 LP entries are the first sheets' own, word for word, so
  their labels also show how consistent the labelers are.
- **The labelers:** four Claude subagents again, one batch each, given only the rules
  ("The labels" and "Labeling decisions" in `explanation_checker.md`, word for word), not the
  first run's labels, explanations or results, and not ADR-0009's facts. Blind as the owner
  asked (2026-11-21): each gets a copy of its sheet and its two blank label files in a neutral
  folder, and nothing else: not ADR-0009, the folder's name, the first labels, the limit facts
  or the checker's flags. The copies' first paragraph points to the rules in the prompt
  instead of `explanation_checker.md` (which now holds the first run's results, which the
  first labelers never saw); the rest of each sheet is unchanged. No API calls.
- **The score:** the same rule as before, false claims among the 88, reported against the
  first run's 22 whatever it shows, paired by problem, labeled exploratory and Claude's.
- **The consistency rule (the owner's, 2026-11-21, fixed before any label):** the 15 LP entries
  are identical in both sheets. An entry's labels **match** when its false-claim label and
  every one of its number labels equal the first labeling's. If fewer than 13 of the 15 match,
  the before/after comparison is **inconclusive**, and is reported as that, with its counts.

A paid API call can't stand in for this checker: a model labeling through the API, without
the subagents' tools to enumerate integer solutions, would be a different checker, and its
before count wouldn't be 22.

<!-- checker results: written by scripts/explanation_checker.py score --after -->

### The checker's labels, before and after

Exploratory, dev only, one sample per problem; labels by Claude (four Claude subagents per run, an LLM's, not a person's), blind, by the same rules and sheets.

**The consistency rule:** on the 15 LP entries both sheets share word for word, the new labels match the first labeling's on 15 (every label alike; on the false-claim label alone, 15); 13 were needed, so the before/after comparison is comparable.

| | before | after |
|---|---:|---:|
| explanations with a false claim (of 88) | 22 | 11 |
| ... of the 73 integer programs | 21 | 10 |
| numbers labeled wrong | 0 | 0 |

Paired by problem: 17 explanations had a false claim before and none after, 6 the reverse, 5 had one in both, and 60 in neither.

<!-- end of checker results -->

**Notes (written after the labels; Claude's, an LLM's, not a person's).**

- **It counts, by the owner's rule:** all 15 LP entries the two sheets share got the same labels
  as the first time, so the before/after comparison is comparable. By the same checker,
  explanations with a false claim went 22 → 11 (21 → 10 among the integer programs, the
  headline since the owner's call of 2026-11-21, in place of the rule's count above).
  Exploratory: dev only, one sample per problem, Claude's labels.
- **The labelers:** four Claude subagents on this session's model (Claude Opus 5.5; the first
  labelers' model isn't recorded), each with its copy of the sheet and the rules only; each
  said it opened nothing else. They enumerated integer solutions with their own code, as the
  first ones did. No API call.
- **A judgment call, kept as labeled (post hoc):** batch 4's labeler read unqualified
  sentences such as "loosening the orders rule would not help" as general claims, false when
  a larger loosening helps, and noted that under a one-unit reading 3 of its 6 would be no
  (`471112257`, `-1829385566`, `-594806556`), which would make the 11 an 8. The other way,
  batch 1's labeler noted one borderline no (`-458048177`) that a stricter share-cap reading
  would make yes (12). No label was changed after the labels were seen.
- **What the new false claims are (Claude's post hoc grouping):** of the 6 explanations with
  a false claim only after, 4 misuse the new facts about dropping or loosening a constraint (a
  change's direction reversed, or one unit's result said of any loosening); one gives a share
  cap's slack in its own units as a share gap, and one calls a ratio the only fully used
  constraint while a variable bound is too. ADR-0009 cleared most of the old false claims
  (17 of the 22) and brought a few of its own.
