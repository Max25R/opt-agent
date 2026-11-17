# Key disputes: the plan (follow-up pre-registration, section 5b)

**Status: NOT RUN.** The owner decided on 2026-11-15, for time and before any encoding or
judging, not to perform the check (`docs/followup/DEVIATIONS.md`, deviation 2). No encoding
was written and no judge saw anything. The plan below is kept as it was prepared; the packets
stay git-ignored and `scripts/historical/dispute_packets.py` stays, so it could still be run
(at commit `29b7c99`, where the test split opens: `scripts/historical/README.md`), but
anything it found would be exploratory and post hoc, never the result of record. Deviation
1, the JSON format for the encodings, is superseded.

## The problems

The frozen report (`runs/followup-test/followup_report.json`) lists 15 problems that meet 5b's
trigger: at least 3 of the 4 conditions' majority answers agree with each other and differ
from the key.

complexlp:14, complexlp:25, complexlp:63, complexlp:78, complexlp:81, complexlp:83,
complexlp:94, industryor:17, industryor:22, industryor:26, industryor:27, industryor:30,
industryor:31, industryor:32, industryor:41

The raw keys stay the result of record. An overturned key only feeds the corrected-key row,
applied to all four conditions alike.

## What's here

| file | committed? | what it is |
|---|---|---|
| `packets/<label>.md` | no (problem text; LLM4OR states no license) | the problem text and how to write the encoding; no key, no answers, no models |
| `encodings/<label>.json` | no | the encoder's reply, saved as it came: the model as JSON in the project's own format |
| `prompts/<label>.md` | no | `docs/followup/judge_prompt.md` filled in with the text and the encoding, ready to paste |
| `replies/<judge>/<label>.txt` | no (replies can quote the text) | each judge's reply, verbatim |
| `MANIFEST.json` | yes | SHA-256 of every packet, of the judge prompt and of the report they came from |
| `sheet.csv` | yes | one row per problem and round: the encoder and the model it showed, the verdicts, reply hashes, the solve and the certificate |

`python scripts/dispute_packets.py` writes the packets and the manifest;
`python scripts/dispute_packets.py --prompts` (both at `29b7c99`) writes a prompt for each problem that has an
encoding.

## Step 1: the encodings (5b, step 1)

An encoding is written from the problem text alone, without seeing any condition's model or
answer, and without looking up the key.

**Not Claude in this repository.** The session that built and analyzed the run has read the
disputed problems' keys and the conditions' answers (they're in `followup_report.json`), so
it can't write or correct an encoding.

**The encoder: Gemini on the web (owner's decision, 2026-11-15)**, a fresh chat per problem,
given only the packet: paste `packets/<label>.md` as it is, nothing before or after it. If the
chat offers web search or other tools, turn them off. Record the model Gemini shows in
`sheet.csv`'s `encoder_model`. A vendor other than Anthropic, so the encoding isn't Claude's
reading of the text (the agent's and the judge of record's).

**The format solves as written.** The packet asks for one JSON object: the model in the
project's own format (`schema.LPModel`: variables with bounds and integrality, the objective,
the constraints), the objective's constant if any, each variable's meaning, and any reading it
chose where the text is ambiguous; or `{"not_linear": ...}`. Save the reply exactly as it
came as `encodings/<label>.json` (for example `encodings/complexlp-14.json`). Nothing is
retyped: the file the judges confirm is the file that's solved.

Then run `python scripts/dispute_packets.py --prompts`. It validates each encoding first (the
model checks the solver applies, and a meaning for every variable) and lists any that fail,
with the reason, instead of writing a prompt. A failed encoding goes back to Gemini in the
same chat with the reason, and its row says so.

**Pastes for step 1:** 15, one per problem, plus one per failed validation.

## Step 2: the judges (5b, step 2)

Each prompt goes to both judges, as M6 ran them (`docs/amendments/DEVIATIONS.md`), each in a
fresh chat with web search off:
- the judge of record: Claude Opus 5.5 in a claude.ai incognito chat;
- the second judge: free ChatGPT in a Temporary Chat (record the model if it shows).

Paste `prompts/<label>.md` as it is, nothing before or after it. The judge sees the problem
text and the encoding's JSON (laid out with indentation), and nothing else. Save each reply verbatim
under `replies/judge/<label>.txt` and `replies/second/<label>.txt`, and put its verdict and
SHA-256 in the sheet. Only `VERDICT: match` from both confirms.

**Pastes:** 15 problems x 2 judges = **30 judge pastes** in the first round. A problem that
isn't confirmed may be corrected by its encoder (Gemini, in the problem's own encoding chat,
given the judges' listed items and still nothing about keys or answers) and judged again by
both, in new chats: 2 more pastes per problem per extra round, plus 1 to the encoder. Every round gets its own row in the
sheet.

## Step 3: certificate and arithmetic (5b, steps 3 and 4)

Only for a confirmed encoding:
1. Load the confirmed encoding as it is (`dispute_packets.encoding_model`): no transcription.
2. Solve it with CBC and HiGHS (the frozen solvers). The certificate is either a feasible
   solution that beats the key, or the optimum with its proof that nothing reaches the key
   (an LP's duality certificate, `verify.optimality_problems`; for a MIP, the CBC-vs-HiGHS
   cross-check).
3. Check it by arithmetic (`verify.check_solution`: every constraint evaluated, the objective
   recomputed), add the encoding's `objective_constant` before comparing with the key, and
   record the result.

A key is overturned only with all four steps. Every checked problem is listed in the
results, overturned or not, with its encoding, the verdicts and the certificate.
