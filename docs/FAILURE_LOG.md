# Failure log (dev split)

Failures worth keeping as examples, for milestone 6's hand-labeled error taxonomy and the
README's limitations. Dev problems only. An entry records what happened; it is **not** a
to-do list for prompt changes. The owner labels the categories.

## 1. Dev 793774916 (bakery): a misread limit that self-correction can't catch

**Logged 2026-10-28, from the step 1 smoke test** (`runs/smoke`, git-ignored; code as in
commit `ea1d02a`, which was uncommitted on top of `f4f92c2` during the run). Single-shot
and self-correction answered with the same reply (self-correction replayed it from the
cache). Its request hash, the cache key, is
`2d3cf39447a623229eb79d4c266d4fd388696c5125a23514f34694a0533f8994`.

- **The text:** "The bakery is short staffed and can make a maximum of 50 cakes of either
  type per day." It also gives demand caps of 50 chocolate and 30 vanilla cakes.
- **The annotation reads it as one combined limit:** chocolate + vanilla <= 50. The
  optimum is 20 chocolate and 30 vanilla cakes, for a profit of 530.
- **Claude read it as a limit per type:** chocolate <= 50 and vanilla <= 50, which
  repeats the demand caps and allows 50 + 30 cakes. The optimum is 830.
- **A silent failure.** CBC and HiGHS agree, and the arithmetic checks pass, so the wrong
  answer is confirmed (`Result.confirmed`) and nothing flags it.
- **Why self-correction can't catch it.** The loop revises only a reply it can't use, or
  a model that's infeasible or unbounded. This model is feasible and optimal, so attempt 1
  stops the loop ("optimal"). No feedback is sent, and self-correction's answer is
  single-shot's. Any misreading that leaves the model solvable gets through the same way.
- **The no-solver baseline answered 530**, the annotated reading.
- **Side note:** Claude made both variables integer, but the problem's label is
  continuous. That's harmless here, since integrality doesn't change either optimum.
- **Owner's decision (2026-10-28):** don't tune prompts to fix this problem. Whether the
  sentence is ambiguous enough for an `ambiguous-text` review is left open; the ground
  truth is unchanged.
