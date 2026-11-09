# Deviations from the pre-registration

These are things that ran differently from what the pre-registration
(`docs/PREREGISTRATION.md`, Amendments 1 and 2) or Amendment 3 says. They're recorded here
because the pre-registration is frozen (`docs/FREEZE.json`) and Amendment 3 is tagged
(`amendment-3`). Neither is edited.

## 1. Where the 5a judges ran (recorded 2026-11-08)

**What Amendment 2, part 1 says.**
- The judge of record is "Claude Opus 5.5 in Claude Code ("extra")".
- It runs "in a Claude Code session started outside this repository". The one exception
  is the reviews, which run in an incognito claude.ai chat.

**What happened for the test run's two hand checks:**

| check | judge | where it ran |
|---|---|---|
| error taxonomy | judge of record: Claude Opus 5.5 | a claude.ai incognito chat, web search off |
| blind grading | judge of record: Claude Opus 5.5 | a separate claude.ai incognito chat, web search off |
| error taxonomy (Amendment 3 only) | second judge: ChatGPT, free version | a ChatGPT Temporary Chat, web search off; model not recorded |

**Why it's a small deviation.** The rule exists so that a judge "can't read the run, the
labels or the other packets". These chats meet that purpose:
- each was a new conversation holding only its prompt;
- web search was off.

As Amendment 3 asks, each check ran in a conversation of its own.

**What it loses.** "extra" is a Claude Code effort setting, and claude.ai doesn't expose
it. So the effort level of these two checks isn't recorded.

**Where it's recorded:**
- the `grader` column of `review/taxonomy/test/labels.csv`, `second_judge.csv` and
  `review/blind_grading/test/grades.csv`;
- the commit that merged the replies (`088b0df`), whose message also records how the
  replies were cleaned.

## 2. The second judge's dates aren't in its sheets (recorded 2026-11-08)

Amendment 2, part 1 says the second judge's sheet records "what it shows, and the date".
- **None of the second judge's sheets records the date.** That covers the integrality
  labels, the reviews and the taxonomy. Each records only the grader.
- **The only dated record is the commit** that added each reply.

## 3. A known integrality-rule bug reached the scores (recorded 2026-11-08)

**What the rules say.** Wherever integrality changes the answer, the label that picks the
answer is a hand label, not the rule's (CLAUDE.md, "Ground truth"; `needs_hand_label`).
Strict wording is accepted either way for integer problems (section 3e).

**What happened.** The rule (`integrality.py`) labels a problem continuous when its text
says "units of X". Four scorable test problems with countable products and strict wording
got that label: `431521997`, `1605420061`, `-1540907330` and `2078392466`. The ground truth
builds a strict reading only for labels that aren't continuous, and the hand-label check
(`integrality_matters`) compares only the annotated LP and IP optima, which are both 0
here. So no hand label was required, no strict reading was stored, and every condition's
strict-reading answer on these four was scored wrong: 4 of the 10 failures in each
condition. Details: `docs/audit/2026-11-review.md`, section 1.1; the exploratory re-score:
Amendment 4 (draft).

**Timeline** (times as in the commits and run logs, UTC-5):

| when | what |
|---|---|
| 2026-10-19 18:09 | Commit `91e3d60` adds to CLAUDE.md: "Known and unfixed: the integrality rule matches ingredient names ("units of chicken" meat), so it labels countable products continuous in at least 3 reviewed test problems (bubble teas, crepes, curry bowls; harmless for the annotated answers; fix after the owner's labels, and check the unreviewed rule labels too)". The fourth problem, `2078392466`, isn't named. |
| 2026-11-04 10:59 | Commit `dc008c8` applies the review judges' outcomes (Amendment 2, part 6). The second judge disputes 8 reviews; CLAUDE.md records that "4 of the 8 are continuous rule labels on countable products with strict wording, the known ingredient-name issue". The four stay scorable, as part 6 says a disputed review does. |
| 2026-11-04 11:05 | The pre-registration is approved (`7f03e1d`). |
| 2026-11-04 11:12 | The freeze is approved (`8f522c0`, tagged `m6-freeze` on 2026-11-08). At this commit CLAUDE.md still lists the bug as known, unfixed and "harmless for the annotated answers". `freeze.unfinished()` has no check for open data bugs. |
| 2026-11-04 11:13-12:06 | `runs/test` runs (commit `8f522c0`). All three conditions answer the four with their strict readings' integer optima (36, 20, 17 and 11); each is scored wrong against 0. |
| 2026-11-04 12:14-12:46 | `runs/test-perturbed` runs. The four aren't in the perturbed set (do-nothing problems are left out of it), so it's unaffected. |
| 2026-11-04 18:41 | Amendment 3 (`ad04f1e`, tag `amendment-3`) lists the 8 shared failures, these four among them, and observes that they are every failure in the do-nothing subset. |
| 2026-11-05 08:39 | Commit `088b0df` merges the taxonomy labels. Both judges label all four `reference`; several of the judge of record's notes say "though the label is continuous". |
| 2026-11-08 | The project audit (`d24fdfd`) traces the mechanism above and finds that "harmless" was true for the annotated answers but not for the strict reading. |

**The order, plainly.** The judges' flag came first. The second judge's disputes of these
four reviews were committed at 10:59 on 2026-11-04 (`dc008c8`, the first commit with the
judges' replies). The pre-registration was approved at 11:05, the freeze at 11:12, and the
test runs started at 11:13, all on the same day. The flag was known when the inputs were
frozen, and the runs went ahead with the four scorable and the bug unfixed.

**The assessment before the runs was wrong.** The bug was judged harmless because it
doesn't change the annotated answers. That missed its second effect: a continuous label
also switches off the strict reading. The scores as frozen are unchanged; Amendment 4
(draft) reports the re-score with corrected labels as an exploratory row, and the result of
record stays 264/274 per condition.
