# Encoding check: judge prompt (follow-up pre-registration, section 5b)

This is the prompt each of the two judges gets, once per checked problem, in a fresh chat
(as section 5b says where each judge runs). Only the two placeholders are filled in:

- `{{PROBLEM_TEXT}}`: the problem's text, exactly as the benchmark gives it;
- `{{ENCODING}}`: the encoding written from that text alone (5b, step 1), in the form below.

Nothing else goes in: not the benchmark's answer, not any condition's model or answer, not
which condition or person wrote the encoding, not why the problem is being checked, and not
this file's first two sections. The prompt is everything from the line after "Prompt
starts" to the line before "Prompt ends", with only the placeholders filled in.

**The encoding's form.** One block of plain text: each variable with its meaning, type
(continuous, integer or binary) and bounds; the objective (minimize or maximize, and every
term); and each constraint with a short name, every term, its sense (<=, >=, =) and its
right-hand side.

**Reading the reply.** The first line is `VERDICT: match`, `VERDICT: mismatch` or
`VERDICT: unsure`. Only `match` confirms. The encoding's solve counts only if both judges
reply `match` (5b, step 2). The listed items are recorded with the dispute, verbatim. An
encoding that a judge doesn't confirm may be corrected and checked again by both judges in
new chats; every round is recorded.

---- Prompt starts ----

You are checking whether a mathematical optimization model says exactly what a word problem
says. You will get the problem's text and a model written from it. Don't solve the model,
don't compute or guess its optimal value, and don't rewrite it: only compare it with the
text.

Check every part against the text:
- every decision the text asks for has a variable, with the right meaning;
- each variable's type: integer or binary where the text counts whole things or yes/no
  choices, continuous where it measures amounts;
- each variable's bounds, including non-negativity and any limits the text states;
- the objective: minimize or maximize as the text says, with every cost, profit or other
  coefficient the text gives, and nothing the text doesn't give;
- each constraint: the right variables, every coefficient and right-hand side as the text
  states it, and the right sense (at most, at least, exactly). Read wording such as "at
  least", "no more than", "exactly", "must equal" and "twice as many" literally;
- every requirement in the text is in the model, and the model has no requirement the text
  doesn't state or clearly imply.

If the text can be read two reasonable ways and the model takes one of them, say so under
AMBIGUOUS; don't count it as a mismatch.

Reply in exactly this format and nothing else:

VERDICT: match | mismatch | unsure
MISMATCHED:
- <the model's variable, objective or constraint name>: the text says <...>; the model has <...>
MISSING:
- <a requirement the text states that the model lacks>
EXTRA:
- <a requirement in the model that the text doesn't state>
AMBIGUOUS:
- <wording with two reasonable readings, and which one the model takes>

Write "- none" under any heading with nothing to list. Reply `VERDICT: match` only if every
list but AMBIGUOUS is "- none". Reply `VERDICT: unsure` if you can't tell, and say why in
the list it concerns.

PROBLEM TEXT:
{{PROBLEM_TEXT}}

MODEL:
{{ENCODING}}

---- Prompt ends ----
