# Final review, November 2026

**Reviewed:** commit `ba2f7f0` (main, clean), on 2026-11-15, as a skeptical outside reviewer.
**No API calls:** no key was set anywhere in the review, the fresh clone had no `.env`, and
nothing reached `api.anthropic.com`. **Changes:** only mechanical fixes (stale status lines,
stale section names, two count slips), in the same commit as this file; they're listed at
the end. Everything else is reported here and left for the owner. Frozen files, results,
tags, answer keys and history weren't touched.

**Method.** A fresh clone from GitHub, run step by step through the README (section 1). Four
read-only subagents checked the claims, the docs drift, the code and tests, and the data
licensing. I re-checked each finding I kept against the files and JSON before writing it
down (two of their items I couldn't confirm are left out). Links, the git history, CI and
the GitHub page I checked myself.

Tags: **must-fix** (wrong or misleading; fix before anyone relies on it), **should-fix**
(unclear, inconsistent, a missing limitation, or a gap in checks), **nice-to-have**.

---

## Summary

**Status (2026-11-18, after the review):** M1-M5 were fixed on 2026-11-15 and S1-S11 on
2026-11-16, each on the owner's go-ahead and with the owner's choices (S7 documented, not
built; S8 moved to `scripts/historical/`; S9 a pure MIT `LICENSE` and a "How this was built"
section; S2's limitations in the README and `docs/ie2310/summary.md`). Not done:
- S9's repository description and topics: GitHub settings, the owner's to change (suggested
  text in `docs/HANDOFF.md`, open item 2).
- S11's last bullet, the earlier audit's item 4 (rename the `owner` source of 4 labels): it
  would change `data/nl4opt/integrality.json`, an input of the frozen answer key, so it's left
  as is; `docs/DESIGN.md` now says what those labels are.

The nice-to-have items were done on 2026-11-18 (commit "The final review's nice-to-have
items"), except two the review gives as notes only: the stale status lines in frozen or tagged
files (section 5), and the lightweight `followup-freeze` tag (no tag is rewritten). The
findings below are kept as written.

**Must-fix**

| # | finding | where |
|---|---|---|
| M1 | "Frozen before any test problem was opened" is false for both studies | README.md:7-8, docs/ie2310/summary.md:30 |
| M2 | Every NL4Opt failure is called a misread model with agreeing solvers, but the baseline has no solver and 6 of 8 shared failures are labeled key errors | README.md:34-36 |
| M3 | The write-up omits pre-registered rows (lenient 266/274 for both solver conditions vs 264; without disputed reviews 260/266) | docs/EVALUATION.md:16-21, 76-81; README.md:27-31 |
| M4 | DATA_NOTICE says ORLM's CC BY-NC answers are "never committed"; about 38 are cited in committed files | DATA_NOTICE.md:42-43 |
| M5 | The agent CLI calls the API with no budget guard, against the project's hard budget rule | src/opt_agent/agent.py:476 |

**Should-fix**

| # | finding | where |
|---|---|---|
| S1 | Overstated pitch and wording: "verified optimal plans", "every number rebuilds ... with no API key", "proves" a MIP's optimum | README.md:3, 9-10, 65; summary.md:78 |
| S2 | Missing limitations: the cross-check never fired; the explanation was never evaluated; contamination; 88.1% against an outside key; self-correction's "0 loud" | README.md:63-85 |
| S3 | LLM judges presented as hand checks; "stricter" secondary test; "all five steps"; "correct" omits accepted readings | EVALUATION.md:11-13, 68; summary.md:25-26, 49, 88 |
| S4 | DATA_NOTICE misses NL4Opt text in review/ and tests/, ORLMBenchmark, LLM4OR's NL4Opt keys; EXTERNAL_DATA.md says LLM4OR data isn't committed | DATA_NOTICE.md:36-43; docs/EXTERNAL_DATA.md:3, 20 |
| S5 | 25 tests skip in CI; several checks never run anywhere in CI | .github/workflows/ci.yml:43-44, 75-104 |
| S6 | Any other `-m` brings the live tests back | pyproject.toml:44 |
| S7 | The demo's live dollar cap resets with every `docker run --rm` | src/opt_agent/demo/app.py:47 |
| S8 | Two scripts can't run at HEAD, undocumented, though the docs say the 5b check "could still be run" | scripts/rescore_dev.py, scripts/dispute_packets.py |
| S9 | GitHub page: license shown as "Other", no description or topics, results 1.4 screens down, authorship unexplained | LICENSE:23-24; README.md:1-17 |
| S10 | Setup steps split across sections; Reproduce assumes an install; no Python version | README.md:100-108, 167-174 |
| S11 | Docs drift left for the owner (content, not mechanical) | docs/DESIGN.md:19, 113-120; CLAUDE.md:68, 496-497 |

---

## 1. Fresh clone

`git clone https://github.com/Max25R/opt-agent.git` into a temp folder (commit `ba2f7f0`,
with its tags), then the README's steps on macOS arm64, Python 3.13.7, with no `.env` and no
key.

| step (README) | result | time |
|---|---|---|
| `python3 -m venv .venv && source .venv/bin/activate` (Development) | ok | 1 s |
| `pip install -r requirements.lock && pip install --no-deps -e .` | ok (see the note) | 30 s |
| `pytest` | 1012 passed, 25 skipped, 3 deselected (live) | 160 s |
| `ruff check . && ruff format --check .` | clean (180 files) | 1 s |
| `python scripts/fetch_llm4or.py` | fetched, hashes checked | 3 s |
| `python scripts/reproduce.py` | every answer replays; 6 of 6 files rebuild byte for byte (M6 93 s, follow-up 118 s) | 212 s |
| `python -m opt_agent.demo` (examples mode) | serves on :8000; examples solve from the cache | — |
| `docker build` / `docker run` | not run: no Docker here. CI's `demo-image` job builds and smoke-tests it (green at `ba2f7f0`) | — |

Note: inside this review's sandbox, pip's first attempt failed on TLS (`OSStatus -26276`, the
sandbox's known problem in CLAUDE.md's Gotchas); with `PIP_USE_DEPRECATED=legacy-certs` it
installed. That's the sandbox, not the repository.

The demo, started from the fresh clone exactly as the README says and driven in a browser:
`/`, `/health` and `/examples` answer; the café-staffing example comes back verified with 16
baristas, which I re-checked by hand (all seven coverage constraints hold, with the surplus of
2 on Monday and 1 on Tuesday that the explanation states); any other text gets a clear
"examples mode solves only the example problems" message (404), and the server log shows no
outbound call.

- **should-fix (S10): the setup is split, and Reproduce assumes it.** README.md:100-101 gives
  the pip line without a venv or a Python version; README.md:103-108 ("Reproduce every
  number") never says to install first, so a reader who starts there gets
  `ModuleNotFoundError: No module named 'opt_agent'` (as the first, failed install here
  showed); the venv appears only at README.md:167-174, at the end. pyproject.toml says Python
  3.12+, and the studies ran on 3.13. *Fix:* one short "Setup" block (Python 3.12+, venv,
  the two pip lines) before "Try the demo", referenced from Reproduce and Development.
- **nice-to-have:** the README's `pytest` comment could say that 25 tests skip without the
  data and Pillow (`python -m opt_agent.data`, `scripts/fetch_llm4or.py`,
  `requirements-docs.lock`), so a fresh reader isn't surprised.

## 2. Claims

- **must-fix (M1): "pre-registered and frozen before any test problem was opened"**
  (README.md:7-8; docs/ie2310/summary.md:30, "before anyone looked at the test problems").
  False for both studies: Claude read and reviewed NL4Opt test problems to build the answer
  key, the LLM judges labeled 44 of them, and two test problems were used while building the
  agent (`data/nl4opt/exclusions.json`) — all before the freeze; and 7 follow-up problems were
  seen before the split (docs/FOLLOWUP_PREREGISTRATION.md, section 5c, which the README's own
  "121 problems" reflects). The pre-registration says what's true: "approved ... before any
  test-split run" (docs/PREREGISTRATION.md:4). *Fix:* "frozen before any test run; problems
  seen during development are excluded from the primary results" in both files.
- **must-fix (M2): "all 10 failures per condition were silent: CBC and HiGHS agreed and every
  check passed, on a model that misread the text"** (README.md:34-36). The baseline has no
  solver, so that can't describe its 10; and README.md:72-73 (Amendment 3) says two judges
  labeled 6 of the 8 shared failures answer-key errors, i.e. not a misread model. *Fix:* "All
  10 failures per condition were silent (a wrong answer with no warning); the judges label 6
  of the 8 shared ones key errors."
- **must-fix (M3): pre-registered rows are missing from the write-up.** Amendment 2 asks for
  lenient accuracy next to every strict one, and Amendment 4 exists to add "two pre-registered
  rows the README omitted", but docs/EVALUATION.md:16-21 and README.md:27-31 still show only
  the strict rows (and the post hoc row in the headline table). The omitted rows are the ones
  that favor the solver: lenient, single-shot and self-correction 266/274 vs the baseline's
  264/274; without disputed reviews, 260/266 each (`results/eval.json`, `amendment_4`).
  docs/EVALUATION.md:76-81 ("The rules") lists Amendments 1-3 and doesn't link 4 or 5. *Fix:*
  add Amendment 4's rows under the result of record in EVALUATION.md (labeled as such), one
  line in the README, links to both amendments, and update EVALUATION.md:3-5's "text ...
  unchanged" note.
- **should-fix (S1): overstated wording.**
  - README.md:3, "verified optimal plans out": "verified" means optimal for Claude's own
    model; 62 of single-shot's 384 follow-up answers were wrong with every check passed
    (`also_reported.failures`). *Fix:* "plans verified optimal for Claude's model".
  - README.md:9-10, "Every reported number rebuilds from committed cached replies, with no API
    key": the follow-up and Amendment 5 also need LLM4OR's data, fetched (README.md:106); the
    M6 write-up scripts run from HEAD, not the tag (docs/HANDOFF.md, step 2); the judges'
    labels come from chat sheets that can't be replayed; and a new run would differ
    (temperature 1). *Fix:* say "with no API key, after fetching the follow-up's public
    benchmark data", and add one line on what replay can't show.
  - README.md:65, "It proves the solution", and summary.md:78, "really is optimal": for a
    MIP, the arithmetic checks prove feasibility only and optimality rests on the two solvers
    agreeing (README.md:135-136 gives a certificate "for an LP"). *Fix:* "proves it for an LP;
    for a MIP, two solvers agree".
- **should-fix (S2): limitations the docs leave out.**
  - *The cross-check never fired.* No loud failure in either study came from a solver
    disagreement or a failed check: M6 had none at all, and every follow-up loud failure was
    an unusable or cut-off reply (`descriptive.loud_failures_by_kind`). Yet summary.md:17-19
    defines a loud failure as "the two solvers disagree, or a check fails". The checks did
    catch real solver bugs in the property tests (docs/DESIGN.md), not in the studies.
  - *The explanation was never evaluated:* every run used `with_explanation=False`
    (src/opt_agent/evaluate.py:381), while README.md:6, 129 and summary.md:22-23 present it
    as a feature ("every number traced to the solver"). The earlier audit's finding 10 said to
    document this; it isn't in the README.
  - *Contamination.* NL4Opt, ComplexLP and IndustryOR are public; "no one had seen"
    (README.md:42-43) covers this project, not the model's training. The README never
    mentions the perturbed-numbers set (it's in EVALUATION.md), and the follow-up has none.
  - *Key errors cut both ways.* Against LLM4OR's cleaned key, every NL4Opt condition scores
    185/210 (88.1%) on the shared problems, vs 206/210 on the frozen key (`amendment_5`),
    mostly where the two keys differ. README.md:72-75 mentions only key errors that lower
    scores.
  - *Self-correction's "65 / 0"* (README.md:58-59): its 0 loud failures come from revising
    single-shot's 4 unusable replies, 3 of which became silently wrong answers
    (`also_reported.self_correction`: 1 wrong to right, 3 wrong to wrong). The counts also
    cover all 128 problems, next to scores on 121.
  - *Fix:* one line each under Limitations, and in summary.md's.
- **should-fix (S3): judges and definitions.**
  - docs/EVALUATION.md:68, "Blind grading agreed with the automatic score on 29 of 30": the
    grader was Claude Opus 5.5 (`hand_checks.label`: "LLM judges, not a human check").
    summary.md:88 says "some of the grading was done by AI judges": all of it was. *Fix:* name
    the grader; "all".
  - summary.md:49 calls the McNemar test on majority votes "a second, stricter test"; it's
    the coarser, less sensitive secondary test. *Fix:* "a second, less sensitive test".
  - summary.md:25-26, "The demo page shows all five steps": no example ever reaches step 4
    (each is solved on its first attempt). *Fix:* "the steps (every example solves first
    time, so the fix step doesn't show)".
  - docs/EVALUATION.md:11-13 defines "correct" as status and objective matching the key,
    leaving out the accepted readings (strict, "=", and both optima of an `either` label),
    which several correct answers needed (`primary`, "correct by reading"). *Fix:* one clause.
- **nice-to-have:**
  - README.md:25, "The NL4Opt test split, 274 problems": 274 of its 289 are scorable
    (data/nl4opt/ground_truth/REPORT.md). Mind the README-number test if 289 is added.
  - README.md:56-57, "(95% CI -1.7 to 3.0 pp): no difference larger than 4 pp, and nothing
    stronger": a reader sees 3.0 and 4. RESULTS.md explains the rule (the smallest whole X
    with the interval inside ±X, on unrounded bounds); say so in a few words.
  - README.md:117 mentions "the IE 2310 figures" without saying what IE 2310 is or linking
    `docs/ie2310/`; docs/ie2310/README.md:14 lists "the summary" among the teammate's parts,
    next to this kit's own summary.md.
  - The demo page says Claude writes "a linear program" (src/opt_agent/demo/page.html:79);
    the staffing example is an integer program.

Checked and sound: every README and EVALUATION.md number against the JSON (264/274, the
Wilson intervals, which I recomputed independently for 264/274, every p = 1 and at most 3
discordant pairs, costs, latencies); H2's +6.3 pp, Holm p 0.0445, the McNemar Holm p 0.24 and
the 1.38 pp from 8 cut-off replies; H1's interval (`score_ci_pp` [-1.65, 3.03]) and its
4 pp rule; "6 of the 8 shared failures"; the integrality-bug bullet (DEVIATIONS.md section 3,
268/274 in `amendment_4`); the related-work paragraph (venues, ORLM and IndustryOR); every
value in docs/ie2310/numbers.md and numbers.csv against its cited field.

## 3. Links

44 tracked Markdown files, 38 relative links (files, folders, images, one anchor:
docs/EVALUATION.md:78 → `PREREGISTRATION.md#amendments`): **none broken.** A script resolved
each link against `git ls-files`, so a link to a git-ignored file would count as broken, as it
is on GitHub, and each anchor against GitHub's heading slugs; it was first checked on planted
failures (a missing file and a missing anchor, both caught). Backticked repository paths in
the docs resolve too (the rest name git-ignored data or files in LLM4OR's repository).

## 4. Secrets and data

**Secrets: clean.**
- Every blob reachable from any ref or the reflog (79 commits, 3,110 blobs) was scanned for
  Anthropic (`sk-ant-`), OpenAI, GitHub, AWS, Slack and Google key patterns, private-key
  headers and `ANTHROPIC_API_KEY=<value>`. No key. One hit is a false positive: `AIza…` inside
  a base64 thinking signature in `runs/followup-test/cache/8aa87731….json`.
- No `.env` was ever committed: the only `.env`-like path in history is `.env.example`, whose
  key line is empty in both versions. HEAD's only `sk-ant-` text is the hygiene test's regex
  (tests/test_repo_hygiene.py:14) and prose in the earlier audit.

**The Docker image: no benchmark data.** It takes requirements.lock, pyproject.toml,
README.md, LICENSE and `src/` (the package, `demo/page.html` and the 16 `demo/replies/*.json`,
which are this project's own examples); `runs/`, `data/`, `review/`, `docs/`, `tests/` and
`.env` stay out (.dockerignore, and the COPY lines name only those files). The only
third-party text in it: the opening 13 words of one NL4Opt dev problem
(src/opt_agent/agent.py:15) and one ORLM status in a comment-like constant
(src/opt_agent/external_check.py:359). DATA_NOTICE.md isn't in the image and needn't be.

**DATA_NOTICE.md doesn't cover everything committed.** Method: 8-word shingles from all 1,245
problem texts in the six local sources (NL4Opt raw, ComplexLP, IndustryOR, ORLM's NL4Opt,
ORLMBenchmark's NL4OPT, LLM4OR's NL4Opt), scanned against all 2,706 tracked text files
(raw, decoded JSON strings, Python string constants). `runs/` matches the notice exactly.

- **must-fix (M4): DATA_NOTICE.md:42-43 says ORLM's NL4Opt answers (CC BY-NC 4.0) "are a
  cross-check only and are never committed"** (also data/nl4opt/README.md:19-21, "isn't
  redistributed here", and CLAUDE.md:589). Individual ORLM answers are cited in committed
  files: data/nl4opt/reviews.json (e.g. "ORLM's 2500 breaks the 70%-adult constraint", and
  "matching ORLM" with values), copied into ground_truth/*.json, REPORT.md (ORLM's implied
  labels, which with our optima give its answers) and review/test_reviews/; and
  src/opt_agent/external_check.py:359 ("ORLM found no solution"), which ships in the image.
  About 38 of ORLM's 245 answers in all. The file itself is never committed. *Fix:* say that,
  list where answers are cited, with CC BY-NC 4.0 attribution (or remove the citations).
- **should-fix (S4): coverage gaps.**
  - NL4Opt problem text is also in review/ (12 packets and prompts, e.g.
    review/test_reviews/PACKET.md, 62 problems) and tests/problems.py, tests/fakes.py, but
    DATA_NOTICE.md:36-37 names only runs/test, runs/test-perturbed and data/nl4opt. NL4Opt is
    MIT with its license committed, so no exposure; but these files read as this project's
    MIT work. *Fix:* add review/, tests/ and "short quotes in docs/".
  - ORLMBenchmark (Apache-2.0) isn't mentioned, though review/external_check.md holds 13 of
    its answers; and its NL4OPT.jsonl is ORLM's file with corrections (same 245 rows, 223
    identical answers), so the inherited answers are arguably ORLM's (CC BY-NC). *Fix:* an
    entry that says both.
  - LLM4OR's NL4Opt keys (no license) are cited in docs/amendments/amendment-5.md and
    `results/eval.json` (`amendment_5`). *Fix:* name them in the LLM4OR paragraph.
  - docs/EXTERNAL_DATA.md:3 and :20 say the LLM4OR data is "not committed" / "isn't committed
    here", and DATA_NOTICE.md:25 links there for details; the follow-up's LLM4OR problem text
    is committed under runs/. *Fix:* "the files aren't committed; their problem text is, in
    runs/ (DATA_NOTICE.md)".
- **nice-to-have:**
  - DATA_NOTICE.md:11-12 says results.jsonl quotes "short phrases"; checklist flags quote runs
    of up to about 44 words. DATA_NOTICE.md:13-14 names only
    runs/dev-checklist-rev1/attempts.jsonl; its results.jsonl quotes 4 ComplexLP problems.
  - tests/test_demo.py:87-99 checks the examples against NL4Opt only, matching word runs as
    substrings of punctuated text. (The claim holds: no example shares 8 words in a row with
    any of the six sources.)
  - .dockerignore: `*.egg-info/` and `build/` match only at the root, and COPY takes the
    working tree, so stray untracked files under src/ would enter a local build. Use `**/`.

## 5. Docs drift

Every tag target the docs cite is right; the numbers restated by hand in CLAUDE.md and
HANDOFF still match the results files; only three Markdown files are fingerprinted
(PREREGISTRATION.md, FOLLOWUP_PREREGISTRATION.md, judge_prompt.md), and all three match their
tags.

**Fixed in this commit (mechanical):**
- docs/amendments/amendment-5.md:3: "DRAFT ... Not approved, not tagged" → tagged
  `amendment-5` (1cb05ed), as was done for Amendment 4; CLAUDE.md and HANDOFF's open item 4
  updated to match.
- docs/amendments/DEVIATIONS.md:60, 84-85: "Amendment 4 (draft)" → tagged.
- README section names that changed in M8 ("Follow-up evaluation", "Evaluation", "Sources"):
  CLAUDE.md (the hard rule at :21-23, and :290, :379, :388), docs/HANDOFF.md (:30, :43,
  :113-114), docs/followup/RUN_NOTES.md:52.
- What CI does with `amendment_5` since M8 (the test job copies it forward; the reproduce job
  rebuilds it): CLAUDE.md:327, docs/HANDOFF.md:127-128.
- docs/HANDOFF.md:14: "still rebuild byte-identical at HEAD (checked 2026-11-13)" → from the
  tag, checked again from a fresh clone today.
- CLAUDE.md provenance lines that predate Amendment 2 (:553, :558-560, :586-588: the
  `judge` source, the retired blind sample, and the test reviews' checks).
- Count and status slips: CLAUDE.md:85 ("at least 3" problems, four named → 4), :90 (the CLI
  key item is still open after M8), :490 (`pytest` takes about 2.5 minutes, not 100 s);
  docs/FOLLOWUP_DEV_LOG.md:21 ("One so far" → two bug fixes are logged); data/nl4opt/README.md:9
  (labels can also be `either`).
- Pointers to this review: CLAUDE.md (milestone 8) and docs/HANDOFF.md (open item 7).

**should-fix (S11): drift that needs the owner's wording.**
- docs/DESIGN.md:113-120, "Claude ... wrote every hand review and most hand labels. The owner
  decided the rest", and "Test split: every hand label and every review is Claude's": 44 test
  labels are the judges' combined labels (source `judge`) and 4 are the owner's `either`
  labels (`data/nl4opt/integrality.json`).
- docs/DESIGN.md:19 says a claimed optimum is "overruled only by such a ray", but
  src/opt_agent/solver.py:40-47 also overrules an optimum claimed at an infeasible point; the
  bug list (:35-52) leaves out `CBC_INFEASIBLE_OPTIMUM_BUG`.
- CLAUDE.md:68, "Before milestone 6 (all done)", includes labeling
  `review/taxonomy/dev-1/`, whose labels.csv has 0 of 7 rows labeled. Say it was skipped (if
  it was).
- CLAUDE.md:496-497 lists `scripts/dev_walkthrough.py` and `packets integrality|reviews|
  agreement` as everyday commands, but both overwrite records that are kept as sent. Add
  "don't regenerate".
- **Duplication.** Results are restated by hand, with no test, in CLAUDE.md (M6 and M7
  entries) and docs/HANDOFF.md (Current state); the known-unfixed lists in CLAUDE.md:83-90
  and HANDOFF:86-88 had already diverged; provenance lives in CLAUDE.md, DESIGN.md and
  REPORT.md. CLAUDE.md's status log is now about 7,300 words (the earlier audit's item 12
  suggested moving history out). *Fix:* numbers only in the results files, current state in
  HANDOFF, history in a docs/HISTORY.md.
- **The earlier audit's section 5** (docs/audit/2026-11-review.md): items 1, 2 (mostly), 6, 8
  and 10 are done; 3 ("say 4" exclusions, DESIGN.md:111), 4 (rename the `owner` source), 5
  (the explanation never evaluated, in the README), 7 (the lenient column, see M3), 9
  (REPORT.md's writer), 11 (fixed here) and 12 (history out of CLAUDE.md) aren't.

**nice-to-have:**
- Frozen or tagged text with stale statuses, report only: the `amendment_4` and `amendment_5`
  labels in `results/eval.json` say "draft"; AMENDMENT_3.md:158 says the script is "not yet
  written"; amendment-5.md:94 says CI copies its row forward; FOLLOWUP_SPLIT.md:43-44 (a
  generated file) leaves the seen problems "for the pre-registration to decide".
- docs/EXTERNAL_DATA.md:4, "Nothing here is used by milestone 6": Amendment 5 uses it. Its
  manual fetch steps (:40-50) predate `scripts/fetch_llm4or.py`; point to the script.
- docs/HANDOFF.md: open item 2a is finished work; :212 names the CI job by its old name
  (`screenshot`, now `pictures`).
- The `followup-freeze` tag is lightweight; the other four are annotated (note only).

## 6. Code

Clean on the basics: no TODO/FIXME/XXX/HACK and no commented-out code (an AST scan); no bare
or broad `except`; every `print` in src/ is in a `main()`; all 70 argparse flags are read;
pyproject.toml and requirements.lock agree (tests/test_lock.py enforces it); every script's
`--help` works. The full suite here, with all data and Pillow present and this commit's
fixes: 1037 passed, 3 deselected (live), in 140 s (`HYPOTHESIS_PROFILE=ci`).

- **must-fix (M5): the agent CLI has no budget guard.** src/opt_agent/agent.py:476 builds a
  plain `anthropic.Anthropic(api_key=get_api_key())`: no `BudgetedClient`, no cap, no ledger;
  `--attempts` has no upper bound (:461), `--no-cache` forces paid calls, and `--model` takes
  any ID unpriced. An exported key is enough. CLAUDE.md's budget section says "Every live
  call goes through `budget.BudgetedClient`", and the earlier audit (section 7.2) said the
  guard still caps spend. *Fix:* wrap it in `BudgetedClient(..., Budget(args.cap,
  "logs/spend/agent.jsonl"))` with a `--cap` flag (and a bound on `--attempts`).
- **should-fix (S5): checks that CI never runs.** CI's test job has no data and no Pillow, so
  25 tests skip (19 need LLM4OR, ORLM or the raw annotations; 4 need Pillow); the reproduce
  job fetches LLM4OR's data but runs only `reproduce.py`; the pictures job installs Pillow but
  runs no tests. Covered elsewhere: the Amendment 5 numbers, the follow-up rebuild and the data
  hashes (reproduce). Never run in CI: REPORT.md is current (tests/test_ground_truth.py:160),
  the rebuild from the raw annotations (tests/test_perturb.py:303), review/external_check.md
  is current (tests/test_external_check.py:100), the split from its seed
  (tests/test_followup_split.py:36), the sealed loaders' id and hash checks
  (tests/test_followup_freeze.py:179, 196; tests/test_followup_test_split.py:220), and the
  committed docs/demo.png's margins and byte stability (tests/test_screenshot.py:78-106).
  *Fix:* in the reproduce job, also run `python -m opt_agent.data`, install the docs lock and
  run `pytest`; or at least `pytest tests/test_screenshot.py` in the pictures job.
- **should-fix (S6): any other `-m` re-enables the live tests.** pyproject.toml:44 sets
  `addopts = "-ra -m 'not live'"`, and a later `-m` replaces it: `pytest -m "not slow"`
  collects all 3 live tests (checked). With a key exported they'd spend, capped at $0.25 by
  their own `BudgetedClient`. *Fix:* in conftest.py, skip `live` tests unless
  `OPT_AGENT_LIVE=1`.
- **should-fix (S7): the demo's live cap resets per container.** The ledger is
  `Path("logs/spend/demo.jsonl")` (src/opt_agent/demo/app.py:47, "kept across restarts"),
  inside the container's /app; the README's `docker run --rm ... -e OPT_AGENT_LIVE=1` starts
  every container with an empty ledger, so "$0.50" is per container, not in all. *Fix:*
  document `-v "$PWD/logs:/app/logs"`, or say "per container".
- **should-fix (S8): two scripts can't run at HEAD, and the docs don't say so.**
  scripts/rescore_dev.py stops on a cache miss (HEAD's requests no longer match the dev
  cache; checked: it stops with "a request missed the cache"; it's referenced only by
  FOLLOWUP_DEV_LOG.md). scripts/dispute_packets.py calls `followup.load_test()` (:161), which
  raises `FreezeError` at HEAD by design; its docstring says it needs the frozen inputs, but
  it isn't in the `followup-freeze` tree, and nothing says how to run it, while
  docs/HANDOFF.md (open item 6) and review/followup_disputes/README.md:6 say the 5b check
  "could still be run". *Fix:* say how (via `opt_agent.frozen.Tree`) or mark both as
  historical.
- **nice-to-have:**
  - Dead code: `baseline.SYSTEM_PROMPT_SHA256` (src/opt_agent/baseline.py:52) is never used
    (its comment says it's in the logs; `self_correct`'s is). Used only by tests:
    `packets.read_says_lp` and `_ROW` (packets.py:321, 347; review/says_lp.md is retired)
    and `perturb.load_perturbed` (perturb.py:305).
  - Finished one-off scripts (key_formats, mutation_recall, dev_walkthrough, followup_split)
    still run, but nothing marks them as one-offs. A `scripts/one_off/` folder or a line in
    each docstring.
  - CI's "live mode without a key refuses to start" step passes on any startup failure and
    has no timeout (a live start would hang the job). Use `timeout 60` and check for the
    missing-key message.
  - `data.DATA_DIR = Path("data")` (src/opt_agent/data.py:18) depends on the working
    directory, unlike `runs.REPO_ROOT`; anchor it.
  - scripts/fetch_llm4or.py:79 deletes any existing `--target` that isn't the recorded copy;
    refuse a non-empty folder it didn't create.

Live tests are gated correctly otherwise: marked `live` (tests/test_live.py:30) and excluded
by default and in CI; dev problems only; every call through `BudgetedClient` ($0.25,
`logs/spend/live-tests.jsonl`). Every other real client is budgeted and behind
`OPT_AGENT_LIVE=1` or `--plan` and the freeze check (evaluate.py, demo/app.py,
cache_examples.py); the replay clients refuse every call; `.env` is read only with
`OPT_AGENT_LIVE=1`, and CI has no key.

## 7. Recruiter view (the GitHub page, first 60 seconds)

What a visitor sees at github.com/Max25R/opt-agent (public), checked in a browser at 1280×900:

- **should-fix (S9):**
  - *License shows as "Other".* The sidebar says "License" and the tab "License", not "MIT
    license"; the API reports `spdx_id: NOASSERTION`. The cause is the paragraph appended to
    LICENSE on 2026-11-15 (LICENSE:23-24), which breaks GitHub's MIT detection. *Fix:* keep
    LICENSE as the verbatim MIT text and leave the "code only" note in README.md and
    DATA_NOTICE.md, which already say it.
  - *"No description, website, or topics provided."* (a known open item). *Fix:* the
    description from pyproject.toml, and topics such as `llm`, `operations-research`,
    `linear-programming`, `evaluation`, `claude`.
  - *The results are far down.* The README starts under a 20-row file list; then a 5-line
    pitch with no numbers, then a screenshot 950 px tall. The first result is about 1.4
    screens into the README. *Fix:* one sentence of headline results in the pitch (the
    README-number test will check it), or the screenshot after Results.
  - *Authorship is unexplained.* GitHub lists "claude" as a contributor and on the latest
    commit (74 of 79 commits are co-authored), and the root's CLAUDE.md is a 671-line status
    log, the longest file in the repo. The README never says how the project was built.
    *Fix:* a short "How this was built" note in the owner's words (what they designed,
    decided and checked; Claude Code as the pair programmer), and the history moved out of
    CLAUDE.md (S11).
- **What reads well:** the pitch says what it does in one breath; the demo screenshot shows a
  real verified answer; the results tables are short; the Limitations section is candid; the
  Mermaid diagram renders; CI is green on all 5 jobs (run 43792386491 at `ba2f7f0`).
- **What would confuse a non-specialist:** "silent / loud" is defined after the first table
  that uses it; "Holm", "sign-flip", "McNemar", "pp", "H1/H2" and "mean score" come without a
  gloss; the follow-up's "121 problems no one had seen" begs a question (see M1). A
  one-sentence glossary line under Results would cover most of it.
