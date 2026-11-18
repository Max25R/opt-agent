# Answer-key disputes: a spot-check for a person

*Exploratory and post hoc. Written by `python scripts/dispute_spotcheck.py`; please don't edit the table by hand, except the verdict column.*

An LLM judge (Claude) flagged 90 of the follow-up's wrong answers, on 13 problems, as answer-key disputes ([`failure_types.md`](failure_types.md)): it found no error in the model, so either the key is wrong or it rests on another reading of the text. **No person has verified any of them.** Here are 10 of the 13 problems, drawn at random (seed 20261118, from the 13 in id order; the table is in draw order), for a person to check. Nothing here changes a reported result: the raw keys are the result of record, as pre-registered (the key check 5b wasn't run: [`DEVIATIONS.md`](../followup/DEVIATIONS.md), deviation 2).

**How to check one.** Fetch the problems with `python scripts/fetch_llm4or.py`. A ComplexLP problem is the row of `data/external/llm4or-clean/Mamo_complex_lp_clean.jsonl` whose `id` is its number (the text is `Question`, the key `Answer`); an IndustryOR problem is the line of `data/external/llm4or-clean/IndustryOR.jsonl` with its number, counting from 1 (`en_question`, `en_answer`). Claude's models come from a replay with no key, `python scripts/failure_cases.py` (into the git-ignored `review/failure_types/cases.jsonl`), and the judge's full notes are the problem's rows of [`failure_types.csv`](failure_types.csv). Write one verdict per problem: **key wrong**, **model wrong**, **both readings defensible** or **can't tell**.

| # | Problem | Key, as written | Our flagged answers | Why it was flagged | Verdict |
|---:|---|---:|---|---|---|
| 1 | `industryor:28` | 1146.6 | 1146.41 (1 answer, 1 model) | Integrality: the model keeps production in whole units, as IndustryOR's own MIP tag has it; the key is the continuous optimum. | |
| 2 | `complexlp:83` | 138.0 | 145 (9 answers, 3 models) | The key is two separate two-city loops; the text asks for one tour back to the start, and the model's tour is the cheapest one. | |
| 3 | `industryor:17` | 43700 | 43200 (9 answers, 4 models) | A fixed-charge reading: setup costs only for the types made, and larger containers may serve smaller demand; the key makes every type for its own demand. | |
| 4 | `complexlp:78` | 248.0 | 260 (7 answers, 3 models) | The key is two separate round trips (cities 1-2 and 3-4); the text asks for one tour, and the model's tour is the cheapest one. | |
| 5 | `complexlp:63` | 50.0 | 127 (9 answers, 3 models) | The key is two separate round trips (cities 1-4 and 2-3); the text asks for one tour, and the model's tour is the cheapest one. | |
| 6 | `industryor:26` | 8505 | 10755 (9 answers, 3 models) | The model charges storage on the required year-end stock too, a literal reading of the fee rule; the key is exactly that fee less. | |
| 7 | `industryor:27` | 32.436 | 0.0324359 (9 answers, 3 models) | Units: the model reads the nutrient contents per gram, as the text writes them; the key is exactly 1000 times its answer (per kilogram). | |
| 8 | `industryor:30` | 9337440 | 10349920 (6 answers, 4 models) | No model error found, yet the key is about 1.01 million below the model's optimum: it needs a cost or limit the judge found nowhere in the text. | |
| 9 | `complexlp:81` | 140.0 | 182 (9 answers, 3 models) | The key is two separate round trips (cities 1-3 and 2-4); the text asks for one tour, and the model's (1-2-4-3-1) is the cheapest. | |
| 10 | `industryor:41` | 1146.57 | 1146.41 (6 answers, 2 models) | Integrality: the model keeps every quantity in whole units, as IndustryOR's own MIP tag has it; the key is the continuous optimum. | |
