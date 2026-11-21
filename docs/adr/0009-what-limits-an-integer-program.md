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

## Action Items

1. [x] `limits.py`, the facts' `limits` and the prompt paragraph, `agent.run`'s switch, the
   tests (`tests/test_limits.py`), and the dry run (2026-11-20).
2. [x] The owner's paid run: `scripts/paid_explain_limits.py` (2026-11-20,
   `runs/explain-dev-limits`).
3. [x] Then compare the new explanations' claims about slack with the first run's
   (2026-11-20, exploratory, dev only: [`limits_claims.md`](../analysis/limits_claims.md)).
   By the same rule, the integer programs' explanations with a false "not limiting" claim
   went 13 → 4 (of 73). A post hoc note (Claude's reading): the 4 are the rule's own
   misreadings. The rule's recall on the new wording isn't measured.
4. [ ] Refresh the demo's two integer examples' replies (baristas, crates; the owner's paid
   step) and turn `pipeline.EXPLAIN_LIMITS` on.
5. [ ] The Agent Skill (`skills/opt-agent/`) explains from slack and binding constraints too:
   give it the same test.
