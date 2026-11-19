# The explanation checker, evaluated on dev (exploratory)

**Status.** This protocol was committed on 2026-11-19 before any of the explanations it
labels existed: the owner's paid run (`scripts/paid_dev_and_demo.py`, part 1) writes them;
then Claude labels them by the rules below and the results are added here. Exploratory:
neither study pre-registered it, and nothing here is a result of record. **The labels are
Claude's, an LLM's, not a person's, and Claude wrote the explanations too** (the same family
of model), so this is a weak check of the checker, not a measurement of truth.

**What the checker claims** (`explain.py`): every number in an explanation is a correct
rounding of a solver fact (the objective, a value, a slack, a shadow price) or of an input (a
coefficient, a right-hand side or a bound of the model, or a number in the problem's text),
or it's flagged; a refused, cut-off or empty explanation is flagged too. It checks where each
number comes from, not whether the sentence using it is true. The README says this was never
evaluated; this is that evaluation, on dev only, as the project's rules require.

## The data

NL4Opt's 92 scorable dev problems, single-shot (one formulation, as in M6), replayed from the
cached replies of the M6 dev run `runs/dev-1` (a formulation not found there would be a paid
call), and one explanation for each verified answer, with HEAD's prompt and Claude Haiku 5.5.
The checker runs on each. Everything is saved in `runs/explain-dev/` (NL4Opt is MIT).

## The labels (Claude's)

From a sheet that shows each explanation with its problem, its model and its solver facts,
and **not** the checker's output, Claude labels:

1. **Each number** the checker reads (its own regular expression, so both see the same
   tokens): **correct** (a fact or an input as the sentence uses it, or a number correctly
   computed from them, such as a difference or a total) or **wrong** (any other value, or a
   right value attached to the wrong thing, such as one constraint's slack given as
   another's).
2. **Each explanation:** whether any sentence says something false about the solution or the
   problem while every number in it is correct (for example, that a constraint binds when it
   has slack, or that more of a resource would lower a maximum): a **false claim**, which by
   design the checker can't see.

## What's reported

- **Numbers:** flagged and wrong (caught), flagged and correct (a false alarm, usually a
  number computed correctly), not flagged and wrong (missed), with the checker's precision
  (caught over flagged) and recall (caught over wrong).
- **Explanations:** how many have an error (a wrong number or a false claim), how many of
  those the checker flags, and how many have only errors it can't see; and how many it flags
  with no error at all.
- Counts with their denominators and 95% Wilson intervals (`opt_agent.stats.wilson`),
  whatever they show. A weak result is reported as weak.

<!-- results: added after the labels -->

## Results

Not run yet: the explanations come from the owner's paid run.

<!-- end of results -->
