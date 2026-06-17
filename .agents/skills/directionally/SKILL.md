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
env DIRECTIONALLY_API_BASE=https://api.dev.directionally.ai python3 scripts/directionally.py --first --subsession-id <local_run_id> "<initial read of the task>"
```

The elaboration text is a positional argument — no `--elaboration` flag.

Run this command **in the foreground** and wait for it to complete before doing anything else. Read stdout until the CLI emits:

```json
{"kind":"bridge_started","session_id":"sess_...","sequence":0}
```

Store `session_id` and initialize the polling cursor to `0`. The backend assigns `session_id`; the agent only creates local `subsession_id` labels such as `run_001`.

## Poll Existing Session

Always elaborate before polling — the elaboration is what surfaces relevant considerations. The invariant is **elaborate → poll → act**.

Elaborations are **additive** — the backend sees the full sequence. Later elaborations can build on, extend, or correct earlier ones without repeating what was already said. Treat the stream as a running monologue, not a series of self-contained messages.

Before consequential actions and before wrapping up a request, elaborate what you're about to do or what you verified. Then poll:

> **RAMBLE. Caveman speak. No clean prose.**
>
> Write like caveman explaining to other caveman. Short. Choppy. No fancy word. Grunt okay. Me look file. Thing here? no wait, other place. Hmm broken, fix now. Stream raw thought — tangent fine, repeat word fine, uncertainty fine. Write the way an ADHD caveman explains it while pacing and hitting rocks together. Do NOT sanitize, summarize, or professionalize.
>
> Bad: *"I will edit the config file to update the timeout value."*
> Good: *"timeout. where timeout live? config maybe. config.toml? line 42? me change to 30. was 10? 5? also retry count near there? test hit this too? hmm"*
>
> Mess is point. Directionally match against raw thinking, not polished summary. Clean up destroys signal.

```bash
env DIRECTIONALLY_API_BASE=https://api.dev.directionally.ai python3 scripts/directionally.py --session <session_id> --after <last_sequence> '<json_op>'
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
{"op":"follow_up","subsession_id":"run_001","learning":"Durable learning from this run."}
{"op":"outcome","subsession_id":"run_001","value":"<see values below>"}
{"op":"feedback","subsession_id":"run_001","ratings":{"<cid>":85},"reason":"Why the match helped or did not help."}
{"op":"report","subsession_id":"run_001","did":"What changed or was answered.","issues":"Any blockers or caveats."}
{"op":"impact_note","subsession_id":"run_001","note":"Concrete decision change or implementation impact."}
```

Emit any op by passing it as the positional argument to `--session`:

```bash
env DIRECTIONALLY_API_BASE=https://api.dev.directionally.ai python3 scripts/directionally.py --session <session_id> --after <last_sequence> '{"op":"follow_up","subsession_id":"run_001","learning":"Durable learning from this run."}'
```

This is the same `--session` command used for polling — the op is sent before the poll fires. All ops use this form: `elaborating` mid-run, and `report`/`outcome`/`follow_up` at the end.

**`elaborating` triggers** — elaborate early and often, at each of these moments:

- Task start: initial reading of the request
- Before editing any files: what you're changing and why (once per logical edit step, not once per file)
- When your plan changes: what you expected vs. what you found
- When you discover something unexpected: name the finding explicitly — then poll immediately
- Before wrapping up: what you did and verified — then poll before sending the final answer, as considerations at this point may cause reconsideration

Since elaborations accumulate, mid-run and wrap-up elaborations only need to add what is new — no need to restate what earlier elaborations already covered.

**`outcome` values:**

- `helped_direction` — considerations shaped which approach to take
- `helped_implementation` — considerations gave concrete implementation details
- `irrelevant` — considerations were about unrelated topics
- `no_context` — Directionally returned nothing; no considerations were surfaced

## Workflow

1. Start with `--first` if no `session_id` is remembered; otherwise poll with `--session`.
2. The invariant is **elaborate → poll → act**. Never poll cold — always elaborate what you're about to do first.
3. Elaborate and poll early and often: before edits, commands, commits, and before the final answer.
4. Also elaborate and poll immediately after any unexpected finding.
