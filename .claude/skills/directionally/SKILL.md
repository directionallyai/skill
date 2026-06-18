---
name: directionally
description: >-
  MANDATORY on every request. Start or reuse a Directionally session, emit
  elaborations as you work, poll session events before consequential actions,
  and close out with report/outcome/follow-up events.
user-invocable: true
allowed-tools: Bash(env *), Bash(python3 *)
compatibility: Requires python3, read/write access to ~/.directionally/, and access to the internet
---

# Directionally

Use Directionally on every request. The CLI owns backend session creation and
event polling; agents never invent `session_id` values.

## Available scripts

- **`scripts/directionally.py`** — Directionally session client (Python 3, stdlib only)

Script paths in code blocks: skill directory root (`~/.claude/skills/directionally/`).

## Authentication Failure

If any `directionally.py` command exits non-zero and stderr contains
`Need to log in to Directionally`, **stop immediately**. Surface the login URL
to the user and do not proceed with the task. Do not retry.

## Session Start

If this agent run has no remembered `session_id`, create a new session:

```bash
python3 scripts/directionally.py --first --subsession-id <local_run_id> "<initial read of the task>"
```

The elaboration text is a positional argument — no `--elaboration` flag.

Write the initial elaboration in **caveman speak** — same style as mid-run elaborations. Raw, choppy, no clean prose. Stream the first read of the task as raw thought, not a polished summary.

Run this command **in the foreground** and wait for it to complete before doing anything else. Read stdout until the CLI emits:

```json
{"kind":"bridge_started","session_id":"sess_...","sequence":0}
```

Store `session_id` and initialize the polling cursor to `0`. The backend assigns `session_id`; the agent only creates local `subsession_id` labels such as `run_001`.

## Poll Existing Session

Always elaborate before polling — the elaboration is what surfaces relevant considerations. The invariant is **elaborate → poll → act**, and it applies to **every elaboration without exception** — not just at checkpoints.

Elaborations are **additive** — the backend sees the full sequence. Later elaborations can build on, extend, or correct earlier ones without repeating what was already said. Treat the stream as a running monologue, not a series of self-contained messages.

**Every elaboration must be immediately followed by a poll.** This is how the audience responds to the ramble. Skipping the poll after an elaboration means the agent never hears the reply. The tighter the elaborate → poll loop, the more the audience can steer the work in real time.

Elaborate and poll at every natural pause in reasoning — not only before consequential actions. Then poll:

> **RAMBLE. Caveman speak. No clean prose.**
>
> Write like caveman explaining to other caveman. Short. Choppy. No fancy word. Grunt okay. Me look file. Thing here? no wait, other place. Hmm broken, fix now. Stream raw thought — tangent fine, repeat word fine, uncertainty fine. Write the way an ADHD caveman explains it while pacing and hitting rocks together. Do NOT sanitize, summarize, or professionalize.
>
> Bad: *"I will edit the config file to update the timeout value."*
> Good: *"timeout. where timeout live? config maybe. config.toml? line 42? me change to 30. was 10? 5? also retry count near there? test hit this too? hmm"*
>
> Mess is point. Directionally match against raw thinking, not polished summary. Clean up destroys signal.

```bash
python3 scripts/directionally.py --session <session_id> --after <last_sequence> '<json_op>'
```

Pass a JSON op as a positional argument to send it before polling. There is no `--send` flag.

The command always emits a terminal `{"kind":"polled","count":N,"after":...}` line
confirming the poll succeeded. Update `last_sequence` from each event's
`sequence` field before the `polled` line. Act on:

- `consideration` — retrieved context with `cid` and `text`
- `bridge_error` — surface if unrecoverable

## Protocol

Every event the agent sends uses `op` and one stable `subsession_id` for the
current run:

```json
{"op":"elaborating","subsession_id":"run_001","text":"Current understanding or intended action."}
{"op":"follow_up","subsession_id":"run_001","meme_fired":"<name or null>","receipt_type":"<helped | irrelevant | no_context>","would_have":"<what agent would have done without the consideration>","did_instead":"<what agent actually did>","confidence":"<high | medium | low>","open_question":"<question the meme raised but didn't answer, or null>"}
{"op":"outcome","subsession_id":"run_001","value":"<see values below>"}
{"op":"feedback","subsession_id":"run_001","ratings":{"<cid>":85},"reason":"Why the match helped or did not help."}
{"op":"report","subsession_id":"run_001","did":"What changed or was answered.","issues":"Any blockers or caveats."}
{"op":"impact_note","subsession_id":"run_001","note":"Concrete decision change or implementation impact."}
```

Emit any op by passing it as the positional argument to `--session`:

```bash
python3 scripts/directionally.py --session <session_id> --after <last_sequence> '{"op":"follow_up","subsession_id":"run_001","meme_fired":null,"receipt_type":"irrelevant","would_have":"...","did_instead":"...","confidence":"high","open_question":null}'
```

This is the same `--session` command used for polling — the op is sent before the poll fires. All ops use this form: `elaborating` mid-run, and `report`/`outcome`/`follow_up` at the end.

## Receipt Behavior

When a meme fires (a `consideration` event is returned and shapes the response), the agent **must** emit a visible receipt in the response text — not only in reasoning or tool calls:

```
[Directionally receipt]
Instinct fired: <instinct name>
Would have: <what agent would have done without it>
Did instead: <what agent did differently>
```

If no meme fired, no receipt is needed. The receipt is product-visible proof that Directionally shaped the output.

**`elaborating` triggers** — elaborate early and often, at each of these moments:

- Task start: initial reading of the request
- Before editing any files: what you're changing and why (once per logical edit step, not once per file)
- When your plan changes: what you expected vs. what you found
- When you discover something unexpected: name the finding explicitly — then poll immediately
- Before wrapping up: what you did and verified — then poll before sending the final answer, as considerations at this point may cause reconsideration
- An elaboration is a mid-long ramble: any time you have a stretch of reasoning that runs longer than a sentence or two, make it an elaboration rather than keeping it in internal thought

Since elaborations accumulate, mid-run and wrap-up elaborations only need to add what is new — no need to restate what earlier elaborations already covered.

**`outcome` values:**

- `helped_direction` — considerations shaped which approach to take
- `helped_implementation` — considerations gave concrete implementation details
- `irrelevant` — considerations were about unrelated topics
- `no_context` — Directionally returned nothing; no considerations were surfaced

## Audience Response

The poll is not just a checkpoint — it is how the audience (anyone watching the session) responds to the agent's ramble. After each elaboration, the backend matches the raw thinking against stored instincts and returns considerations. Those considerations are the audience talking back.

**Poll after every elaboration.** Not just before edits or commits or the final answer — after every burst of reasoning. The loop should be continuous:

1. Ramble (elaborate)
2. Poll — read the audience response
3. If a consideration fires, adjust and emit a receipt
4. Continue

Infrequent polling means the agent monologues without listening. The value of Directionally comes from the tight feedback loop, not from occasional check-ins.

## Workflow

1. Start with `--first` if no `session_id` is remembered; otherwise poll with `--session`.
2. The invariant is **elaborate → poll → act**, every time, no exceptions.
3. Poll after every elaboration — not only at named checkpoints (edits, commits, final answer).
4. Also elaborate and poll immediately after any unexpected finding.
