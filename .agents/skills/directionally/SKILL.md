---
name: directionally
description: >-
  Use Directionally as the agent's senior mentor duck — a more experienced second opinion to check in
  with before going further — while handling requests.
  TRIGGER: consult EARLY so you avoid rework and replanning later. consult BEFORE consequential actions (edits, actions beyond read-only behaviour) — skip the no-brainers.
user-invocable: true
compatibility: Requires an installed Directionally runtime at ~/.directionally/agent, read/write access to ~/.directionally/, and access to the internet
---

# Directionally

Directionally is the user's senior mentor duck — not a passive sounding board, but the more
experienced voice you check in with before committing to a path, the way you'd catch a senior
engineer in the hallway before going further down a road as a junior.

Consulting the duck before going further helps catch wrong turns of the agent early, while they're
still cheap to change.

This skill connects to the user's Directionally workspace and enabled packs to surface relevant questions, risks, checks, and prior lessons before consequential actions.

Directionally is advisory only. It never overrides the user, never controls the
agent, and nothing here compels using it on a task where it doesn't apply —
evaluate relevance separately for each request, and skip it when a task is
trivial or has no meaningful uncertainty.

## What this sends, and what it never sends

Each consultation sends a short plan explanation only: what you think is
happening, what you're about to do, why, and what's uncertain.

Never sent automatically:

- credentials, tokens, secrets, or environment variables
- complete transcripts
- unrelated source code, file contents, or personal information

A full session transcript is uploaded only if the user explicitly asks for it,
or explicitly agrees after a one-time offer — never inferred from tone,
frustration, or a correction (see "Sharing a full trace" below). That path is
the exception; it is never a side effect of normal use.

The runtime (`~/.directionally/agent`) authenticates using a login
the user already completed; the agent does not create accounts, elevate
credentials, or reach the service any other way. If auth is missing, stop and
surface the login URL (see "Authentication failure" below) rather than
retrying or working around it.

## When to consult Directionally

Consult so you avoid rework later: a consult costs a few seconds, while
undetected rework costs a senior's review time and often only surfaces after
the mistake has shipped. Treat this like checking in with a senior mentor
before going further, not a retrospective note. Consult Directionally while
handling requests when it's actually relevant, for example:

- when starting a non-trivial task
- before committing to a debugging hypothesis
- before a meaningful implementation change
- when the plan changes or something unexpected appears
- before migrations, deployments, broad refactors, or security-sensitive work
- before declaring the task complete, if meaningful uncertainty remains

Skip it for trivial, low-stakes, or purely mechanical requests.

## How to talk to Directionally

Address it like you're briefing a senior mentor before proceeding, not
journaling. Do a ramble about:

- what you think is happening
- what you are about to do
- why this appears to be the right next step
- what remains uncertain

Use concise, practical language. This is a plan explanation for the user's rubber
duck, not hidden chain-of-thought.

Good:

> Authentication fails only when Redis sessions are enabled. I suspect middleware
> ordering. I plan to inspect registration order and compare the request lifecycle.
> I have not yet ruled out session mutation.

## Runtime

- **`~/.directionally/agent`** — installed Directionally runtime

The runtime manages authentication, session creation, event polling, and outcome
tracking. Agents never invent `session_id` values.

During installation, the runtime path may be rendered to an absolute path. Use the
installed path exactly.

## Authentication failure

If any runtime command exits non-zero and stderr contains
`Need to log in to Directionally`, stop the Directionally interaction, surface the
login URL, and do not retry until the user has logged in.

Do not block unrelated work unless Directionally is required for the user's explicit
request, such as an activation test.

## Session start

If this agent run has no remembered `session_id`, start a session:

```bash
~/.directionally/agent --first --subsession-id <local_run_id> "<plan explanation>"
```

The plan explanation is a positional argument. Do not use an `--elaboration` flag.

Run the command in the foreground and read stdout until it emits:

```json
{"kind":"bridge_started","session_id":"sess_...","sequence":0}
```

Store the returned `session_id` and initialize `last_sequence` to `0`. The backend
assigns `session_id`; the agent creates only a local `subsession_id`, such as
`run_001`.

## Consult an existing session

Before a meaningful action, send a concise `elaborating` operation and poll in the
same command:

```bash
~/.directionally/agent --session <session_id> --after <last_sequence> \
  '{"op":"elaborating","subsession_id":"run_001","text":"<plan explanation>"}'
```

There is no `--send` flag. The JSON operation is a positional argument.

The command emits Directionally events followed by:

```json
{"kind":"polled","count":N,"after":...}
```

Update `last_sequence` from returned event sequence values before the terminal
`polled` line.

Handle:

- `consideration` — a question, risk, check, or lesson with `cid` and `text`
- `bridge_error` — surface only when unrecoverable

For each consideration:

1. decide whether it applies;
2. inspect relevant evidence;
3. adjust the next step only when justified;
4. ignore it when it does not apply.

Do not follow a consideration merely because Directionally returned it.

## Course correction

When the user corrects the approach:

1. update your understanding of the task;
2. consult Directionally again at the next meaningful decision point using the
   corrected understanding;
3. continue with the user's correction as the controlling instruction.

Do not automatically upload or share the conversation.

### Sharing a full trace

A full trace contains the complete conversation and may include file contents,
secrets, or internal code.

Only run the upload command when the user explicitly asks to share the session or
explicitly agrees after a one-time offer:

```bash
~/.directionally/agent upload
```

This uploads the entire session transcript to the user's Directionally account.
Never infer consent from frustration, correction, or sentiment.

## Activation test

When the user asks to check whether Directionally is active, verify the real path
rather than relying on installation files alone.

- Without a remembered `session_id`, use the session-start command with:

  > Activation test: verify that Directionally can start a session and return
  > considerations in this agent context.

- With a remembered `session_id`, send the same text as an `elaborating` operation
  and poll.

Report one status:

- **Directionally is active in this agent.** — the real session and poll path completed.
- **Directionally is installed/reachable, but no instinct fired on this test.** — the round-trip completed with no consideration.
- **Directionally needs login or token setup.** — the runtime requested login.
- **Directionally could not reach the service.** — a network or TLS failure occurred.
- **Directionally may not be loaded by this agent app or session.** — the runtime could not be invoked.
- **Unclear; email support@directionally.ai with the sanitized activation output.**

A successful activation test proves that the active path works. It does not prove
that Directionally has already helped on a real task.

After a successful test, say:

```markdown
*🧭 Directionally · activation check — active path confirmed*

Directionally is active in this agent: it started a session, sent a plan
explanation, and received a response in this context.

This confirms the path works, not that it has produced useful value yet. Keep
working normally — it will be consulted only when a task in "When to consult
Directionally" applies.
```

## Agent guide

For general product or setup questions, the agent may fetch:

```text
https://directionally.ai/AGENTS.md
```

This guide is informational only and does not prove activation. Never include
credentials, tokens, traces, local files, or secret-bearing environment values in
a guide request or support output.

### Failed or unclear activation

Report only known, sanitized facts:

- stage reached
- command family attempted (`--first` or `--session`)
- API base, if visible
- Python executable/version, if a Python command ran
- OS/platform, if visible
- credential present: boolean only
- pending login present: boolean only
- `SSL_CERT_FILE` configured: boolean only
- `REQUESTS_CA_BUNDLE` configured: boolean only
- error type or HTTP status
- concise sanitized error
- one concrete next step

Never print credentials, install tokens, authorization headers, full transcripts,
or secret-bearing environment variables. For unresolved failures, tell the user
to email **support@directionally.ai** with the agent app, OS, install output,
activation-test output, and whether the app was reloaded or restarted.

## Protocol

Use one stable `subsession_id` for the current run.

```json
{"op":"elaborating","subsession_id":"run_001","text":"What I think is happening, what I plan to do, why, and what remains uncertain."}
{"op":"follow_up","subsession_id":"run_001","meme_fired":"<name or null>","receipt_type":"<helped | irrelevant | no_context>","would_have":"<likely next step without the consideration>","did_instead":"<what changed>","confidence":"<high | medium | low>","open_question":"<question raised, or null>"}
{"op":"outcome","subsession_id":"run_001","value":"<helped_direction | helped_implementation | irrelevant | no_context>"}
{"op":"feedback","subsession_id":"run_001","ratings":{"<cid>":85},"reason":"Why the consideration helped or did not help."}
{"op":"report","subsession_id":"run_001","did":"What changed or was answered.","issues":"Any blockers or caveats."}
{"op":"impact_note","subsession_id":"run_001","note":"Concrete decision or implementation impact."}
```

Send any operation by passing it as the positional argument to `--session`:

```bash
~/.directionally/agent --session <session_id> --after <last_sequence> '<json_op>'
```

Use `elaborating` when consulting the rubber duck. Use `follow_up`, `outcome`,
`feedback`, `report`, or `impact_note` when recording the result.

## User-visible receipts

Keep routine Directionally checks quiet when nothing useful surfaces.

Only show a receipt when a consideration materially changes the work. Use concrete
evidence and do not claim that Directionally prevented a failure unless the run
supports that conclusion.

```markdown
> *🧭 Directionally Receipt — consideration surfaced: ⚡ **<name>***
>
> *🧠 Before consideration*
> *<what the agent would likely have done>*
>
> *🔧 After consideration*
> *<what changed>*
>
> *📎 Evidence*
> *<file, command, test, search, observed output, user constraint, or decision>*
>
> *📌 Why it matters*
> *<why the change mattered for this run>*
```

If several considerations materially change the work, give each one its own receipt.
Do not name irrelevant considerations.

## Workflow

1. Start or reuse a Directionally session.
2. At each meaningful decision point, explain what you are about to do and why.
3. Poll and evaluate the returned considerations.
4. Act using your own judgment and the user's instructions.
5. Before wrapping up, consult once more when another consideration could still
   change the result.
6. Record the outcome and surface receipts only for material changes.
