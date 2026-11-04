# Amendment 3: an exploratory answer-key row, and blinded hand-check prompts

**Status: approved when the owner commits this file (tag `amendment-3`).** Drafted by Claude
on 2026-11-04, and decided by the owner the same day. That commit is the **timestamp of
record**, and it's made before either judge sees a prompt.

**Post hoc.** This amendment was written after both test runs finished and their reports
were read. It adds one exploratory row and changes how the 5a prompts are given to the
judges. The primary analysis doesn't change. Sections 1 to 5a, Amendments 1 and 2, the
frozen ground truth, every score, the McNemar family and every pre-registered row stay as
they are.

**Why a separate file.** `docs/PREREGISTRATION.md` says amendments go at its bottom. But that
file is frozen (`docs/FREEZE.json` hashes it), so this amendment lives here.

## Why

- **The 8 shared failures.** In the main test run (`runs/test`), 8 problems are wrong in all
  three conditions: `431521997`, `1605420061`, `-1540907330`, `2078392466`, `-926961422`,
  `-2138755435`, `1344881875` and `181608358`.
  - In 7 of the 8, all three conditions give the same wrong answer, including the
    baseline, which has no solver.
  - 4 of the 8 are reviews that Amendment 2, part 6 left disputed (`431521997`, `1605420061`,
    `-1540907330`, `2078392466`). In each, the second judge disagreed with the review.
  - These 4 are also every failure in the do-nothing subset (3b), in every condition.
- **One passed the cross-check only by coincidence.** `-2138755435` was kept by the
  edited-text rule (Amendment 2, part 5: "graded against our text; no action, it already
  agrees").
  - The benchmark changed "4000 customer interactions" to "400". Its 95 is the optimum of
    its text read as "at least 400".
  - For our text, 95 is the optimum only under the annotation's "at most 4000". That plan
    gives 745 interactions.
  - The rule compared the two answers, not the two texts.
  - The only other problem the rule kept, `-756853497` (the benchmark inserted "at least"),
    holds for our text. "Needs to transport 80 people" reads as at least 80 seats, and "=
    80" is infeasible.
- **Why the scores can't settle it.** Agreement this strong across conditions can mean two
  things: a model error every condition shares, or an answer key that rejects a reading the
  text supports. The scores can't tell which. The taxonomy's `reference` category (5a) is
  the pre-registered place to say which.
- **What prompted this amendment.** After seeing the results, Claude read several of the 8
  as answer-key problems. That's why this amendment exists, but it isn't evidence. The
  judges decide, and their prompts don't carry that reading.

## 1. One exploratory row

**The row:** "all scorable, with the shared failures both judges call answer-key errors
counted as correct".
- It gives strict accuracy per condition, with its Wilson interval, next to the primary
  strict accuracy.
- Wherever it's shown, it's labeled exploratory and post hoc.
- It has no tests: it's outside the Holm family, and gets no McNemar test of its own.

**The covered problems** are the 8 shared failures above, and only those. They're fixed here,
before any judge has labeled the test taxonomy. The cross-check audit flagged only
`-2138755435`, which is already one of the 8.

**When a failure counts as correct.** A condition's failure on a covered problem counts as
correct only if **both** judges give the category `reference` to the taxonomy row that holds
that condition's answer.
- On all 8, single-shot and self-correction gave the same model, so they share one row.
  The baseline's answer has a row of its own.
- Anything else leaves the failure wrong: another category from either judge, or a missing
  label.
- Nothing else changes. No answer key is edited, and the ground truth stays frozen.

**`reference`, for this rule,** means: **the answer key is wrong for this text, or fails to
accept a valid reading of it.**
- It's the pre-registered category, which the judges see with its pre-registered meaning:
  "the system's reading is one the text supports but no accepted reading allows, or the
  reference is wrong".
- The two definitions say the same thing in other words.

**The second judge labels the taxonomy too, for this row only.**
- Amendment 2 gives the taxonomy to the judge of record only, and this row needs both
  judges.
- So the second judge (the free version of ChatGPT) gets the same prompt as the judge of
  record (part 2), in a conversation of its own.
- It labels all 20 rows, not only the covered ones, so a judge can't tell which rows this
  amendment counts.
- The pre-registered taxonomy counts (5a) stay the judge of record's.
- The second judge does **no blind grading**, since that isn't pre-registered for it.

## 2. Blinded prompts (a deviation from Amendment 2, part 1)

Amendment 2, part 1 gives a judge "the generated prompt, byte for byte". This part changes
that for the test run's two 5a checks.
- **Why it's acceptable:** blinding only removes information. The one blind-grading
  addition is a reply format, which adds nothing about the models. And neither check
  affects any score: 5a reports agreement and counts, with no tests.
- **The exception:** this amendment's exploratory row, which rests on the taxonomy (part 1).

**The taxonomy prompt** is `review/taxonomy/test/BLIND_PROMPT.md`, written by
`scripts/blind_taxonomy.py` (outside the frozen code, so it's reproducible).
- **It starts from the frozen rows** (`taxonomy.failures`): all 20 distinct silent failures,
  with the pre-registered category table.
- **It removes:**
  - each row's problem id;
  - its condition names (also from the instructions, and from the line for an answer with
    no model);
  - its key;
  - Claude's review reasons;
  - revision flags (the test run's failures have none).
- **It adds nothing.** The rows are shuffled with seed `20261104` and labeled `Row 1` to
  `Row 20`.
- **The reply format:** CSV only, with the first line exactly `row,category,note`, then one
  line per row and nothing else. The merge refuses a reply without that header.
- **The row-to-problem mapping** is `review/taxonomy/test/blind_rows.csv`, which no judge
  sees.
- **Both judges get this prompt,** including the judge of record for the primary 5a
  taxonomy. The frozen `LLM_PROMPT.md` is still generated, but no judge gets it.
- **The replies** are kept verbatim, as `review/taxonomy/test/judge_reply.csv` and
  `second_judge_reply.csv`. The script merges them back with the frozen
  `packets.merge_reply`, which checks every row's key:
  - the judge of record's goes into `labels.csv` (5a);
  - the second judge's goes into `second_judge.csv`.

**Blind grading** is `review/blind_grading/test/PACKET.md`, byte-identical to the frozen
code's output.
- The judge of record gets it and then, in the same message, `REPLY_FORMAT.txt`. It asks for
  CSV only, with the first line exactly `number,grade,note`, then one line per item and
  nothing else.
- Blind grading comes first, as pre-registered, and each check runs in a new conversation.

**Known limits of the blinding:**
- **Direct answers are recognizable.** A row with no model is an answer given directly, so a
  judge can tell those rows apart even though the condition isn't named.
- **Pairs are visible.** The pre-registered fact "the same answer as row N's model" (kept,
  with its row renumbered) pairs a direct answer with a model of the same problem.
- **The text can be looked up.** The problem text itself could be searched for, as in every
  earlier packet.

## Limits

- **Post hoc.** The rule, the covered set, the choice to cover only shared failures, and the
  blinding were all decided after seeing which answers failed.
- **One direction only.** The row can turn wrong answers right, never the reverse.
  - Answers that match a wrong answer key aren't examined here.
  - The only check on those is blind grading's stratum of models scored right.
- **Absolute accuracy, not differences.** Every covered problem fails in all three
  conditions. So the row moves the conditions together, except where a baseline row and a
  model row on the same problem get different labels. It says something about accuracy,
  and almost nothing about differences between conditions.
- **The same vendor.** The system, the judge of record and the author of this amendment are
  all Claude. The second judge is the independent check, and either judge alone can keep a
  failure wrong.

## Code

- **`scripts/blind_taxonomy.py`** writes the blinded prompt and its mapping, and merges
  replies. `tests/test_blind_taxonomy.py` checks five things:
  - the prompt hides the ids, conditions, keys and reviews;
  - the prompt puts the reply's header on a line of its own;
  - every failure has one row;
  - the order is reproducible;
  - a reply merges onto the right problems, and a missing header, a skipped row or an
    unknown category is refused.
- **The row itself** will come from a script outside `src/opt_agent/` (not yet written),
  which reads `labels.csv` and `second_judge.csv`. Wherever the row appears in the README,
  it comes from `results/eval.json`, labeled exploratory.
- **No frozen module changes.**
