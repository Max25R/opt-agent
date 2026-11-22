# ADR-0009: The solver's own test of what limits an integer program, given to the explainer

- **Status:** Accepted
- **Date:** 2026-11-20
- **Deciders:** Max asked for a deterministic constraint status, computed by the solver and
  passed to the explainer; Claude Code chose how (logged in [`HANDOFF.md`](../HANDOFF.md))

## Context

[ADR-0004](0004-explanations-from-solver-numbers.md) limits explanations to the solver's
numbers, and a check catches any number that isn't one of them. Its dev evaluation
(exploratory, Claude's labels, not a person's:
[`explanation_checker.md`](../analysis/explanation_checker.md)) found no wrong number to
catch, but about a quarter of the explanations made a false claim with every number right,
nearly all of one kind: a constraint with slack called "not limiting" in an integer program,
when dropping it changes the optimum. The facts invited it. Binding, slack and shadow prices
are an LP's vocabulary: in an LP, slack means the constraint doesn't limit the optimum, and a
shadow price says what one more unit of a binding one is worth. In an integer program neither
holds (the rickshaw problem leaves $2 of a $200 budget, and without the budget the plan is
unbounded), and a MIP has no duals. The IP slack-claim check
([`ip_slack_check.md`](../analysis/ip_slack_check.md)) showed that solving again settles each
claim; finding the claims in free text was its weak part.

## Decision

For a verified integer optimum about to be explained, `limits.constraint_limits` solves the
model again once without each constraint and once with its limit one unit further out (`<=`:
rhs + 1; `>=`: rhs - 1; an equation is only dropped). A re-solve counts only as the agent's own
answer does ([ADR-0003](0003-two-solvers-and-arithmetic.md)): CBC and HiGHS agree on it and
the arithmetic checks pass; otherwise it's null, "couldn't tell". The explainer's facts carry
`limits` (`dropped_improves` and `loosened_improves` for each constraint), and the system
prompt gets one paragraph: say a constraint doesn't limit the result only if dropping it
wouldn't improve the objective, and say nothing where a value is null.

An LP gets nothing new, and a request without limits is byte for byte the one from before, so
LP explanations and replays of earlier runs keep their cached replies. `agent.run` gives the
limits by default (`explain_limits=True`); the demo turns them off (`pipeline.EXPLAIN_LIMITS`)
until its cached replies are refreshed, since a replay has to send the request it cached.

## Options Considered

### Option A: Re-solved facts, given to the explainer (chosen)

| Dimension | Assessment |
|---|---|
| Complexity | Low: one module of re-solves, one field of the facts, one paragraph of the prompt |
| API cost | None per explanation (the request grows by a few lines); the dev explanations need regenerating once to measure it |
| Verifiability | High: each fact is a re-solve two solvers agree on, tested on small models solved by hand |
| Reproducibility | High: deterministic, and the facts are in the logged request |

**Pros:** it fixes the cause, the missing facts, before anything is written, and needs no
parsing of free text. **Cons:** the explainer can still ignore the facts, and up to four solves
per constraint for every explained integer program.

### Option B: Check the claims afterwards (the IP slack-claim check)

| Dimension | Assessment |
|---|---|
| Complexity | Medium: a rule to find claims and the constraints they name in free text |
| API cost | None |
| Verifiability | Medium: the re-solve is sound, but the rule finds only the phrasings it foresaw, and it was written on the very text it was scored on |
| Reproducibility | High |

**Pros:** it catches a false claim whatever the explainer was told. **Cons:** it flags after
the fact, and misses what its rule can't parse.

### Option C: A prompt line only ("slack doesn't mean not limiting in an integer program")

| Dimension | Assessment |
|---|---|
| Complexity | Lowest |
| API cost | None, besides the same regeneration |
| Verifiability | Low: the explainer is told to be careful but not which constraints limit |
| Reproducibility | High |

**Pros:** one sentence. **Cons:** the explainer would have to guess, or compute, what the
solver can just answer.

### Option D: Placeholders instead of free text (ADR-0004's revisit)

| Dimension | Assessment |
|---|---|
| Complexity | High: templates for every kind of statement, and a new page and CLI layout |
| API cost | Lower per explanation |
| Verifiability | Highest: every claim is a filled slot |
| Reproducibility | High |

**Pros:** no claim the facts don't make. **Cons:** stilted text, and the largest change.

## Trade-off Analysis

Option A answers the question the explainer was getting wrong with the tool the project
already trusts for answers, and leaves the prose free; B and A combine well later (a claim can
now be checked against `dropped_improves` directly, without a re-solve). One unit of loosening
is a choice of scale: it says whether one more unit of the limit, as the model writes it, is
worth anything, which can differ from dropping (the rickshaw budget: dropping it helps, $201
buys nothing whole), so both are given, and dropping is what decides "limits the answer".
Variable bounds aren't tested, only constraints.

## Consequences

- Easier: the explainer is told, for each constraint of an integer program, whether it limits
  the answer, as a fact the solvers settled.
- Harder: explaining an integer program costs up to four extra solves per constraint. Every
  integer program's explanation request changed, so their replies cached before this decision
  don't replay with it: the demo explains without limits until its two integer examples'
  replies are refreshed, and measuring the change means regenerating the dev explanations
  (`scripts/paid_explain_limits.py`, a paid run, the owner's).
- Unchanged: the number check, LP explanations, and every study (none of them explained an
  answer). The three studies' tags still verify; each study's `check()` refuses at HEAD, as it
  does after any change under `src/opt_agent/`.
- Revisit: if the regenerated explanations still call a limiting constraint "not limiting",
  check each claim against `dropped_improves` (Option B without its re-solve), or Option D.
  And if the new false claims about loosening last (its direction reversed, or one unit's
  result said of any loosening), say in the prompt that `loosened_improves` is about one unit
  further out.

## Action Items

1. [x] `limits.py`, the facts' `limits` and the prompt paragraph, `agent.run`'s switch, the
   tests (`tests/test_limits.py`), and the dry run (2026-11-20).
2. [x] The owner's paid run: `scripts/paid_explain_limits.py` (2026-11-20,
   `runs/explain-dev-limits`).
3. [x] Then compare the new explanations' claims about slack with the first run's
   (2026-11-20, exploratory, dev only: [`limits_claims.md`](../analysis/limits_claims.md)).
   By the same rule, the integer programs' explanations with a false "not limiting" claim
   went 13 → 4 (of 73). A post hoc note (Claude's reading): the 4 are the rule's own
   misreadings. The rule's recall on the new wording, and the headline that replaced this
   count: [Update (2026-11-21)](#update-2026-11-21-blind-relabeling).
4. [x] Refresh the demo's two integer examples' replies (baristas, crates; the owner's paid
   run, 2026-11-21) and turn `pipeline.EXPLAIN_LIMITS` on (with `pipeline.REFRESHED`).
5. [ ] The Agent Skill (`skills/opt-agent/`) explains from slack and binding constraints too:
   give it the same test.
6. [x] The explanation checker's own blind labels on the regenerated explanations
   (2026-11-21, exploratory, Claude's labels): explanations with a false claim went 22 → 11 of
   88, comparable by the owner's rule (all 15 shared LP entries labeled alike). In Claude's
   post hoc grouping, 4 of the 6 newly false misuse the new facts (the revisit above).

## Update (2026-11-21): blind relabeling

Exploratory, dev only, and Claude's labels (an LLM's, not a person's). Max asked for this
section after the labels were in; the text above stands as written.

Four Claude subagents labeled the regenerated explanations blind, by the first labeling's
rules and sheets: the results are in
[`review/explain_dev_limits/RESULTS.md`](../../review/explain_dev_limits/RESULTS.md), and how
the labelers were kept blind is in the last section of
[`limits_claims.md`](../analysis/limits_claims.md). Each explanation gets one false-claim
label, which covers false claims of any kind, not only "not limiting" ones. The numbers below
are written by `python scripts/explanation_checker.py score --after` from
[`limits_checker.json`](../analysis/limits_checker.json).

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

<!-- end of results -->

**What changes.** On the first explanations the rule (`scripts/limits_claims.py`) found its
false claims where the labels did. On the regenerated ones it misses most of what the labels
find, and most of what it flags isn't false, so its count doesn't measure the regenerated
explanations. The headline of this decision's measurement is now the blind labels' count above
(Max's call), not the rule's (Action Item 3). Among the misses are the one-unit loosening
claims that the Consequences' revisit names.
