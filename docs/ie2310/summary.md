# The agent side: what it does and how well it works

*For IE 2310. A plain-English summary of the software half of the project. Every number here
comes from the project's results files and is listed, with its source, in
[`numbers.md`](numbers.md); a test checks that they match.*

## What it does

The agent takes an operations problem written in ordinary English, the kind of word problem
an industrial engineer turns into a linear program by hand, and does the same steps:

1. **Formulate.** Claude, an AI language model made by Anthropic, reads the problem and
   writes the model: the decision variables, the objective, and the constraints.
2. **Solve.** CBC, a standard open-source optimization solver, finds the optimal solution of
   that model.
3. **Check.** A second, independent solver (HiGHS) solves the same model, and plain
   arithmetic checks every constraint. If the two solvers disagree, or a check fails, the
   agent reports no answer at all. We call that a *loud* failure: you know something went
   wrong.
4. **Fix.** If the model has no feasible solution or is unbounded, the agent tells Claude
   which constraints conflict and asks for a revised model, up to three tries.
5. **Explain.** Claude explains the optimal plan in plain words, using only the solver's
   numbers; any number that can't be traced to the solver is flagged.

The demo page shows all five steps on four sample problems (a paint production mix, café
staffing, shipping crates from warehouses to stores, and a cattle-feed blend).

## How it was tested

The testing rules were written down and frozen before the agent was run on the test
problems, so the results couldn't be tuned to look good. Each test compared the agent with a
**no-solver baseline**: Claude answering directly, the way a person might estimate an answer
in their head. Two sets of problems were used:

- **Textbook-style problems** (NL4Opt, a public benchmark): 274 test problems.
- **Harder problems** (ComplexLP and IndustryOR, two other public benchmarks): 128 problems,
  each answered 3 times per method, because the AI doesn't give the same answer every time.
  The main analysis uses the 121 problems the project hadn't seen before the test.

## What we found

**On textbook-style problems, everything scored the same: 96.4% right (264 of 274).** The
baseline, with no solver, did as well as the agent. These problems are easy enough that
Claude can do the arithmetic itself, so this set can't show what a solver adds.

**On harder problems, the solver helped a little.** The agent (one formulation, solved and
checked: "single-shot") averaged 82.1% right against the baseline's 75.8%: a gain of
+6.3 percentage points, which the pre-registered test
detected (Holm p 0.0445). Two cautions: a second, stricter test didn't find it significant
(Holm p 0.24), and 1.38 points of the gain come from 8 baseline answers that ran out of room
before finishing. Letting Claude revise its model against a checklist of what the problem
requires didn't measurably help (+0.6 points, inconclusive).

**Most failures were silent, and that's the main lesson.** A silent failure is a wrong answer
that passes every check: the solvers agree and the arithmetic is right, but the model doesn't
say what the problem says (a stated preference treated as a requirement, a missing limit, a
wrong coefficient). On textbook problems, all 10 failures per method were silent. On harder
problems, single-shot's failures were 62 silent to 4 loud.

In IE terms, the agent automates **verification** (did we solve the model correctly?) but not
**validation** (did we build the right model?). The checks catch solver and arithmetic
errors; they can't catch a misread problem. A person still has to compare the model with the
real situation, exactly as with a model built by hand.

## Speed and cost

- **Time** (single-shot): on textbook problems, a median of 3.6 s per problem (6.7 s at the
  95th percentile); on harder problems, a median of 11.8 s (29.0 s at the 95th percentile).
  Most of that is waiting for the AI's reply. The hand-solving time study in the other half
  of the project compares these with solving by hand; the other methods' times are in
  [`numbers.md`](numbers.md).
- **Cost** (single-shot): all 274 textbook answers cost $0.150 in AI fees, and the harder
  set's 384 answers cost $0.7903. Per-answer costs are in [`numbers.md`](numbers.md).

## What this means for an engineer

- Use the agent as a fast first draft of a model, not as a final answer.
- Trust its arithmetic: when it reports an answer, that answer really is optimal for the
  model it wrote.
- Check its model against the problem: every constraint, every coefficient, and whether each
  "must" in the model is really a "must" in the problem.

## Limitations

- One AI model (Claude Haiku 5.5) was tested, and the harder set is small.
- The benchmarks' answer keys contain some errors, and some of the "failures" above may be
  key errors rather than the agent's.
- Some of the grading was done by AI judges, not people.
