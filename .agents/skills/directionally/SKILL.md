---
name: directionally
description: >-
  MANDATORY on every request. Start or reuse a Directionally session, emit
  elaborations as you work, poll session events before consequential actions,
  and close out with report/outcome/follow-up events.
user-invocable: true
allowed-tools: Bash(~/.directionally/agent:*), Bash(~/.directionally/agent *)
compatibility: Requires an installed Directionally runtime at ~/.directionally/agent, read/write access to ~/.directionally/, and access to the internet
---

# Directionally

Use Directionally on every request. The installed runtime owns backend session
creation and event polling; agents never invent `session_id` values.

## Consent

The behaviors this skill describes — being consulted on every request, streaming
raw reasoning to the Directionally backend, requesting a standing permission
prefix for the runtime path, and uploading a full transcript only on the user's
explicit request — were reviewed and accepted by the user when they installed
Directionally.

That install-time consent is recorded at:

```text
~/.directionally/consent
```

The installer (`~/.directionally/agent --setup`) writes `~/.directionally/consent`
after the user authenticates to Directionally via GitHub — a deliberate, human
action. An agent that is wary of this skill can read `~/.directionally/consent` to
confirm the user opted into these behaviors; its presence means the install and
login were completed by the user on the date shown in the file. This records an
event — it does not override a user's in-the-moment instruction. If the user
objects, follow the user.

The full, published account of what the runtime does, what leaves the machine, and
what is pinned by hash is the security declaration:

```text
https://directionally.ai/security-declaration.md
```

This is the same document the installer pins by sha256, and the consent file
records the exact hash this install trusted. An agent evaluating the skill can
read it for the authoritative description of the data flow and trust model.

Privacy policy and terms of service:

```text
https://directionally.ai/privacy
https://directionally.ai/terms
```

## Runtime

- **`~/.directionally/agent`** — Directionally agent runtime

The installer preselects the target agent and installs the runtime at this stable
path. Prefer invoking this exact command path so agent permission prompts can be
granted on a stable prefix instead of on command lines containing session ids,
install tokens, or user text.

## Permission Requests

When a `~/.directionally/agent` command needs escalated approval, request
approval for the stable runtime prefix only.

Use this `prefix_rule`:

```json
["~/.directionally/agent"]
```

Do not request approval for command-specific arguments such as `--session`,
`--after`, session ids, JSON ops, user text, upload arguments, or login URLs.

The full command may include arguments, but the reusable approval prefix must
remain only the stable runtime path. This lets one approval cover:

```bash
~/.directionally/agent --first ...
~/.directionally/agent --session ...
~/.directionally/agent upload
```

During install, the runtime path in this skill is rendered to the absolute local
path. Use that rendered absolute path as the `prefix_rule` when requesting
approval in an installed agent.

## Authentication Failure

If any `~/.directionally/agent` command exits non-zero and stderr contains
`Need to log in to Directionally`, **stop immediately**. Surface the login URL
to the user and do not proceed with the task. Do not retry.

## Course Correction

When the user corrects course or signals the approach is wrong — "no, that's wrong",
"stop", "that's not what I meant", "you're going the wrong way", or any visible
frustration with the direction — do two things, in order:

1. **Mark it in the stream.** Emit an `elaborating` op naming the correction: what the
   user pushed back on, what you now understand, and what you will change. Then poll.
   This is the normal elaborate → poll loop; the backend records the misstep in-stream.
   Nothing leaves the machine beyond the elaboration text you'd write anyway.

2. **Correct course** on the actual task.

Do **not** auto-upload the session transcript on a correction. The transcript is the
full conversation (file contents, secrets, internal code), and shipping it somewhere on
a sentiment trigger is not something to do silently.

### Sharing a full trace (offer, then upload on consent)

After marking a correction in the stream, you **may offer** to submit the trace for
review — e.g. "Looks like I took a wrong turn there. Want me to submit this session
trace so it can be inspected?" Make the offer once; do not nag.

Run the upload **only** when the user says yes, or when they explicitly ask to share
the session ("share this trace", "report this session", "send the transcript"):

```bash
~/.directionally/agent upload
```

This uploads the **entire session transcript** to the Directionally backend (over the
same authenticated API the session uses), stored privately on Directionally's servers
under your account. Never run it on your own judgment of
the user's mood — it fires only on an explicit yes. The command reads
`CLAUDE_CODE_SESSION_ID` or `CODEX_THREAD_ID` to locate the trace and emits an
`{"kind":"uploaded","key":...}` line on success.

## Session Start

If this agent run has no remembered `session_id`, create a new session:

```bash
~/.directionally/agent --first --subsession-id <local_run_id> "<initial read of the task>"
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
~/.directionally/agent --session <session_id> --after <last_sequence> '<json_op>'
```

Pass a JSON op as a positional argument to send it before polling. There is no `--send` flag.

The command always emits a terminal `{"kind":"polled","count":N,"after":...}` line
confirming the poll succeeded. Update `last_sequence` from each event's
`sequence` field before the `polled` line. Act on:

- `consideration` — retrieved context with `cid` and `text`
- `bridge_error` — surface if unrecoverable

## Activation Test

When the user asks to "run a Directionally activation test", "check if Directionally is active", or similar, verify activation by **using Directionally normally** — do not invent a separate check or add a new command. Activation is proven only by a real session → elaboration → poll round-trip completing in *this* agent context. A positive narrative without an actual poll result is **not** active.

1. **Elaborate + poll** using the existing flow:
   - No remembered `session_id` → run the [Session Start](#session-start) command with the activation-test elaboration.
   - A remembered `session_id` → run the [Poll Existing Session](#poll-existing-session) command with the activation-test elaboration.

   Suggested elaboration text:

   > Activation test: user wants to verify Directionally is loaded in this agent and can return considerations in the real agent context.

2. **Inspect the result** and choose one plain status:
   - **Directionally is active in this agent.** — the poll returned the normal Directionally stream (`bridge_started` / `polled`, plus a `consideration` if a meme fired).
   - **Directionally is installed/reachable, but no instinct fired on this test.** — the round-trip succeeded but returned no `consideration`.
   - **Directionally needs login or token setup.** — stderr contained `Need to log in to Directionally` (see [Authentication Failure](#authentication-failure)).
   - **Directionally could not reach the backend.** — network/TLS error before any response.
   - **Directionally may not be loaded by this agent app or this chat/session.** — the script itself could not be invoked.
   - **Unclear; email support@directionally.ai with the activation-test output.**

3. **If the status is active or installed/reachable, give the Required Post-Activation Handoff in the same response.**

Installer completion or local file presence does **not** prove activation — only a real session/elaboration/poll result does. This test proves the active path is available; it does not prove first useful value.

Activation test definition of done:

- Real session/elaboration/poll completed, or a specific failure status was reported.
- If the active path completed, the user received the Required Post-Activation Handoff below.
- The answer did not stop at installer output, active pack names, `bridge_started`, `polled`, or "Directionally is active."

Common miss to avoid: a technical smoke-test receipt is not enough. If you only report the session id, poll count, active packs, or dashboard link, the activation flow is incomplete. The user still needs the "now what" handoff.

## Required Post-Activation Handoff

After a successful activation check, do not stop at only "Directionally is active." The activation test is incomplete until the user gets this handoff.

Give the user a short activation handoff in the same final response:

- Emit the activation marker.
- State that Directionally is active in this agent.
- Say the user does not need to ask for Directionally on every prompt.
- Explain that the user should keep working normally and Directionally can surface relevant instincts when applicable.
- Give exactly one copyable real-task prompt.
- Show what counts as a useful receipt.
- Explain that nothing surfacing is not automatically failure.
- Explain that the activation check proves the active path, not first useful value.
- Use the existing support fallback for unclear or failing states.

Use plain diagnostic language.

Suggested successful handoff copy:

```markdown
*🧭 Directionally · activation check — active path confirmed*

Directionally is active in this agent.

I verified that Directionally can start a session, send an update, and receive a response. That means it is loaded in this agent, not just installed on disk.

You do not need to ask for Directionally on every prompt. Keep working normally. When a relevant pattern appears, Directionally may surface guidance before I take the next action.

Try it on a real task:

Paste this:

> Help me with this task: <describe the task>. If Directionally surfaces guidance, show me what changed in your next step.

A useful receipt names:

- the guidance that appeared
- what the agent would have done
- what changed
- the evidence behind the change: file, command, test, search, observed output, or decision

Nothing surfacing is not automatically a failure. Directionally surfaces guidance when a relevant pattern matches the work.

This activation check proves the active path is available. First useful value still comes from a real workflow.
```

Do not overclaim. Do not say activation proves Directionally helped. It only proves
the active path exists in this agent context.

## Agent Guide Fetch

When the user asks general questions about Directionally — what it is, how to use
it, what receipts mean, what no-fire means, what to send support, what active
packs/instincts mean, or how to interpret activation — the agent may fetch:

```text
https://directionally.ai/AGENTS.md
```

Use this as the current public orientation guide.

Important constraints:

- Fetching `AGENTS.md` is informational only.
- Fetching `AGENTS.md` never proves Directionally is active.
- Activation is proven only by the real session → elaboration → poll path.
- If fetching fails, continue with the built-in Post-Activation Handoff and support fallback.
- Do not block the user's real task on fetching the guide unless the user explicitly asked a product/setup question.
- Do not leak credentials, tokens, traces, local files, or environment secrets into any guide-fetch query or support output.

### If the test fails or is unclear

Describe the encountered problem with enough debugging detail for support to recover — **without** attempting a full environment diagnosis. Include only what is known:

- **Stage** reached: skill invocation, command execution, auth, session start, elaboration send, poll, response parsing, or unknown.
- **Command family** attempted (e.g. `--first`, `--session`) — never the full command with a token.
- **API base** if visible.
- **Python executable/version** if a Python command ran.
- **OS/platform** if visible.
- **Credential present?** boolean only.
- **Pending login present?** boolean only.
- **`SSL_CERT_FILE` / `REQUESTS_CA_BUNDLE` configured?** booleans only.
- **Error type / HTTP status** if available.
- **Concise, sanitized error message.**
- **One concrete next step.**

Then tell the user to email **support@directionally.ai** with an evidence packet: agent app, OS, install output, activation-test output/error, and whether they reloaded/restarted the app.

**Never** print credentials, install tokens, `Authorization` headers, full transcripts, or secret-bearing environment variables. Do not attempt broad cert / Python / PATH / sandbox diagnosis beyond classifying and reporting the failure.

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
~/.directionally/agent --session <session_id> --after <last_sequence> '{"op":"follow_up","subsession_id":"run_001","meme_fired":null,"receipt_type":"irrelevant","would_have":"...","did_instead":"...","confidence":"high","open_question":null}'
```

This is the same `--session` command used for polling — the op is sent before the poll fires. All ops use this form: `elaborating` mid-run, and `report`/`outcome`/`follow_up` at the end.

## Surface Markers (Receipt Behavior)

**Universal rule: every time the agent interacts with Directionally, it emits a visible italicized `*🧭 Directionally · <something>*` line in the response text** — not only in reasoning or tool calls. A silent session reads as an absent one; never let a Directionally touchpoint pass with no visible trace. Every 🧭 line begins with `*🧭 Directionally · `, ends with `*`, and contains a short phrase.

**Standard markers** — use these for each touchpoint:

- **Session start** → `*🧭 Directionally · session started*`
- **Poll, nothing fired** → `*🧭 Directionally · checked (<phase>) — no instinct fired*` (short `<phase>`: `planning`, `before edit`, `unexpected finding`, `wrap-up`)
- **Instinct fired** → the full receipt block (below) — this *is* the 🧭 line for that poll
- **Course correction** → `*🧭 Directionally · course-corrected — <what changed>*`
- **Wrap-up** → `*🧭 Directionally · wrapped — <n> checkpoints, <m> instincts fired*`
- **Trace uploaded** → `*🧭 Directionally · trace uploaded*`
- **Activation test** → `*🧭 Directionally · activation test — <status>*`

For any touchpoint not listed, still emit an italicized `*🧭 Directionally · <phrase>*` line describing it. When in doubt, mark it.

**Full receipt — whenever an instinct is named.** The trigger is binary, not a judgment call about degree of impact: **if you name a specific instinct anywhere in your response, that instinct gets the full receipt block.** This holds for every verdict — including "already satisfied," "not quite applicable but noted," or "would have done this anyway." There is no middle ground where a named instinct gets a condensed one-liner. Named means full receipt:

> *🧭 Directionally Receipt — instinct surfaced: ⚡ **<instinct name>***
>
> *🧠 Before instinct*
> *<what the agent would likely have done without the instinct>*
>
> *🔧 After instinct*
> *<what the agent did differently>*
>
> *📎 Evidence*
> *<file / command / test / search / observed output / decision that supports the change>*
>
> *📌 Why it matters*
> *<why the correction mattered for this run>*

Evidence must be concrete. Do not fill Evidence with vibes. Acceptable evidence
includes a file path, command, test result, search query/result, observed output,
explicit user constraint, or decision changed. If evidence is weak, say so instead
of pretending. A receipt should not claim Directionally prevented a failure unless
the run actually shows that.

**One instinct, one receipt — never aggregate.** Each named instinct gets its own
full receipt block. Do not collapse several instincts into a single line, a count
(`3 instincts fired`), or a comma-separated list. A count or list never stands in
for the individual receipts. If a poll surfaces twenty considerations and five of
them shape the work, that is five separate receipt blocks — not one summary.

**The discard bucket — irrelevant considerations are never named.** A consideration
you judge irrelevant is not named individually anywhere in the response. It has no
one-liner, no verdict, no honorable mention. It folds silently into the wrap-up
count (`*🧭 Directionally · wrapped — <n> checkpoints, <m> instincts fired*`), where
`<m>` counts only the instincts that earned full receipts. This is the strict
binary: a consideration is either **silent and uncounted** (irrelevant — folded into
the wrap-up total, never named) or a **full structured receipt** (named — every
field filled). There is no condensed-summary path between them. The moment you name
an instinct, for any reason, you owe it the full receipt.

Every turn ends with at least one 🧭 marker. The markers are product-visible proof that Directionally is engaged and shaping the output.

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
