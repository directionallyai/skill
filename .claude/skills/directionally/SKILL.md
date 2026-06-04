---
name: directionally
description: >-
  MANDATORY on every request. Start or reuse a Directionally session, emit
  elaborations as you work, poll session events before consequential actions,
  and close out with report/outcome/follow-up events.
user-invocable: true
---

# Directionally

Use Directionally on every request. The CLI owns backend session creation and
event polling; agents never invent `session_id` values.

## First-command Preflight

Directionally commands need internet access to:

- `registry.npmjs.org` for `npx`
- `api.dev.directionally.ai` for the Directionally backend

Before the first command in a project, configure/approve the exact command
prefix:

```bash
env DIRECTIONALLY_API_BASE=https://api.dev.directionally.ai npx -y directionally@0.2.4 ...
```


For Codex reusable approval, use exactly:

```json
["env","DIRECTIONALLY_API_BASE=https://api.dev.directionally.ai","npx","-y","directionally@0.2.4"]
```

For Cursor project-local permissions, ensure `.cursor/cli.json` includes:

```json
{
  "permissions": {
    "allow": [
      "Shell(env DIRECTIONALLY_API_BASE=https://api.dev.directionally.ai npx -y directionally@0.2.4 *)"
    ]
  }
}
```

Do not approve broader patterns like `Shell(env *)`, `Shell(npx *)`, or
`Shell(env DIRECTIONALLY_API_BASE=https://api.dev.directionally.ai npx *)`.

## Setup

If `.schelling/project-id` or the skill files are missing, run setup:

```bash
env DIRECTIONALLY_API_BASE=https://api.dev.directionally.ai npx -y directionally@0.2.4 --setup
```

Use `--force owner/repo` only when the project id cannot be inferred from a
GitHub remote.

## Session Start

If this agent run has no remembered `session_id`, create a new session:

```bash
env DIRECTIONALLY_API_BASE=https://api.dev.directionally.ai npx -y directionally@0.2.4 --first --subsession-id <local_run_id> "<initial read of the task>"
```

The elaboration text is a positional argument — no `--elaboration` flag.

Run this command **in the foreground** and wait for it to complete before doing anything else. Do not run it in the background or in parallel with other commands — you need its stdout to get the `session_id`.

Read stdout until the CLI emits:

```json
{"kind":"bridge_started","session_id":"sess_...","sequence":0}
```

`--first` exits after creating the session and sending the elaboration.
Store `session_id` and initialize the polling cursor to `0` in the agent's own
session context. The backend assigns `session_id`; the agent only creates local
`subsession_id` labels such as `run_001`.

## Poll Existing Session

Before consequential actions and before final answer, poll the existing session:

```bash
env DIRECTIONALLY_API_BASE=https://api.dev.directionally.ai npx -y directionally@0.2.4 --session <session_id> --after <last_sequence>
```

The command always emits a terminal `{"kind":"polled","count":N,"after":...}` line
confirming the poll succeeded. Update `last_sequence` from each event's
`sequence` field before the `polled` line. Act on:

- `consideration` — retrieved context with `cid` and `text`
- `polled` — acknowledgment that the poll succeeded; `count` is how many events arrived
- `bridge_error` — surface if unrecoverable

Other events are session bookkeeping unless they are directly relevant.

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

**`elaborating` triggers** — emit at each of these moments, not just at start/end:

- Task start: initial reading of the request
- Before each file edit: what you're changing and why
- When your plan changes: what you expected vs. what you found
- When you discover something unexpected: name the finding explicitly
- Before final answer: what you verified

**`outcome` values:**

- `helped_direction` — considerations shaped which approach to take
- `helped_implementation` — considerations gave concrete implementation details
- `irrelevant` — considerations were about unrelated topics
- `no_context` — Directionally returned nothing; no considerations were surfaced

## Workflow

1. Start with `--first` if no `session_id` is remembered; otherwise poll with
   `--session`.
2. Poll before edits, commands, commits, and final answers.
3. Keep elaborations concrete: current understanding, evidence, intended action,
   verification result, or changed decision.
4. Poll later with `--session`; do not expect the `--first` process to remain
   running.

Use only the `--setup`, `--first`, and `--session` CLI forms documented here.
Do not inspect terminal transcripts to discover session state.
