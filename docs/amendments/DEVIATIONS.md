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
