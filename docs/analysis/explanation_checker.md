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

88 explanations, 565 numbers. Labels by Claude (an LLM, not a person) from sheets without the checker's flags. Exploratory.

| numbers | count |
|---|---:|
| flagged by the checker | 5 |
| labeled wrong | 0 |
| flagged and wrong (caught) | 0 |
| flagged but correct (false alarms) | 5 |
| wrong but not flagged (missed) | 0 |

Precision (caught over flagged): 0 of 5, 0.0% (0.0 to 43.4). Recall (caught over wrong): 0 of 0.

| explanations | count |
|---|---:|
| with an error (a wrong number or a false claim) | 22 of 88, 25.0% (17.1 to 35.0) |
| with a wrong number | 0 |
| with a false claim, every number correct | 22 |
| flagged by the checker | 3 |
| errors the checker flags | 1 of 22, 4.5% (0.8 to 21.8) |
| errors with no wrong number flagged (invisible to it) | 22 |
| flagged without an error | 2 |

<!-- end of results -->

## Labeling decisions (made while labeling, before scoring)

Four Claude subagents labeled one batch each, from the sheets alone. Three raised the same
question, and every batch was labeled by the answer below (batch 1 got it by message before
it finished); none of the labelers saw the checker's flags.

- **"Doesn't limit," in an integer program.** A sentence saying a constraint with slack "isn't
  what limits" the answer is a false claim only if dropping or loosening that constraint
  changes the optimum, checked by enumerating the integer variables. In an LP a constraint
  with slack never limits; in an integer program it can.
- **A slack in the constraint's own units, worded as a share gap** ("0.8 below the 10% cap"
  when 0.8 is cups) is a false claim when the share reading is false; the number itself stays
  correct. Where both readings happen to be true, it isn't one.
- **A statement the explanation takes back** ("devote all 120 acres ... no, plant 50") still
  counts: a reader meets the false version first.
- Borderline calls are written in the notes column of `review/explain_dev/claims-*.csv`.

## Reading it (written after the scoring)

- **No wrong number, so nothing for the checker to catch.** By these labels, Claude Haiku
  5.5 never put a wrong number in a dev explanation: every one of the 565 numbers was a solver
  fact, an input, or correctly computed from them. The checker's 5 flags were all computed
  numbers (a constraint's left-hand side, its right-hand side plus or minus its slack):
  correct, and flagged by design, since it can't tell a correct computation from an invented
  one.
- **One explanation in four was wrong anyway.** 22 of the 88 make a false claim with every
  number correct, which the checker can't see. Post hoc (Claude's grouping of the labelers'
  notes, not part of the declared report): 16 say a constraint with slack doesn't limit an
  integer program's answer when dropping or loosening it does change the optimum; the other 6
  misdescribe a minimum as a cap, give a wrong reason for missing shadow prices, read a
  slack as a share gap, compare limits across units, or state a plan and then take it back.
  21 of the 22 are integer programs, which are 73 of the 88.
- **Checked by hand, in part:** three of the 16 integer-program claims were re-solved with the
  project's own solver, with the named constraint dropped; each optimum changed as the
  labeler said (13 to 0, 18 to 14, $9,975 to $20,700).
- **What it means for the README's claim.** "Every number in the explanation is traced to the
  solver" held on dev, and the checker is the reason it can be said, but it's the narrow half
  of explaining an answer: the errors these explanations do make are reasoning errors (LP
  intuition about slack applied to integer programs), which no number check sees.
- **Weak evidence, as the status says.** Claude labeled Claude's explanations; each batch had
  one labeler and agreement between labelers wasn't measured; dev only, one sample each.
