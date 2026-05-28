---
name: schelling
description: >-
  MANDATORY on every request. Use one schelling recall before the first
  consequential execution path. For ordinary requests, use exactly one recall.
  Use the local interactive Node HTTP/2 bridge and send NDJSON requests over its
  stdin.
user-invocable: true
---

# Schelling

Use one Schelling recall before the first consequential execution path.
For ordinary requests, use exactly one recall. For long or multi-phase work,
recall again only when a new consequential fork appears and the previous recall
no longer covers the plan. This is mandatory.

In this skill, "Schelling" means the product / guidance system / runtime in the
repo context. Do not interpret it as "Schelling points" unless the user
explicitly asks about that concept.

## Requirements

- **Local bridge**: start a long-running Node.js process in an **interactive
  PTY**. The process connects to `http://localhost:9121` over HTTP/2 and forwards
  each line from stdin as one streaming NDJSON chunk.
- **Node.js >= 18**: required for the bridge process and built-in `http2`
  support.
- **One process per turn**: keep the PTY session open while you work. Send
  `recall`, any needed `fetch`, and final write-back messages by writing NDJSON
  lines to the same stdin.
- **One line at a time**: each interaction is exactly one NDJSON object on one
  stdin line. Send it in its own `write_stdin` call, read the bridge response,
  then send the next line. Do not batch multiple NDJSON lines into one write.
- **Local endpoint**: the bridge assumes the Schelling service is already
  listening on `localhost:9121`. If the connection fails, report that the local
  service is unavailable. Do **not** fall back to `npx schelling`, any
  `schelling` package runner, or any remote API command.
- **Server implementation**: in this repo, the local HTTP/2 receiver lives at
  `scripts/schelling-local-server.js`.
- **Client implementation**: in this repo, the interactive PTY bridge lives at
  `scripts/schelling-http2-client.js`.

## Local Bridge

Launch the bridge in a PTY before the first Schelling operation. Keep the
session id returned by the shell tool so later `write_stdin` calls can append
NDJSON messages.

```bash
node scripts/schelling-http2-client.js
```

Run that command with an interactive PTY enabled. Do not run one-off package
commands for Schelling operations, and specifically do not run `npx schelling`
as a fallback when the local bridge is unavailable.

Every stdin line is a complete JSON object and a complete interaction. For
recall, stream `type: "elaborating"` objects as useful thoughts become worth
publishing. Do not maintain a taxonomy of phases or event types. For non-recall
operations, use command objects. The examples below show multiple possible
lines, but send them one at a time and wait for the response after each line.

```json
{"session_id":"<local_run_id>","type":"elaborating","text":"<current understanding, hypothesis, evidence, intended action, or verification note>"}
{"session_id":"<local_run_id>","type":"elaborating","text":"<another useful decision point after doing some work>","confidence":0.74}
{"op":"fetch","cid":"<matched_cid>"}
{"op":"follow_up","cid":"<post_cid>","learning":"<learning>"}
{"op":"outcome","session_id":"<session_id>","outcome":"helped_direction|helped_implementation|irrelevant|missing_memory"}
{"op":"feedback","session_id":"<session_id>","cid":"<matched_cid>","rating":8,"reason":"<textual feedback>"}
{"op":"impact_note","session_id":"<session_id>","note":"<how Schelling helped the mission>"}
```

Read the bridge's stdout after each line before sending another line. Responses
are NDJSON too. Capture the `session_id`, your post `cid`, any `matched_cids`,
and surfaced response text before proceeding.

## The plan

Read just enough local context to form a real likely plan. You may read files,
inspect nearby code, and reason locally first. Do not implement, refactor,
delete, migrate, or commit before the recall.

During recall, still work through the natural phases of the task internally:
understand the ask, identify assumptions and constraints, inspect evidence,
revise the plan, gate consequential actions, and verify the result. Stream what
is useful as `type: "elaborating"` NDJSON events. Do not wait to compress the
whole recall into one summary line, and do not label the public stream with
formal phases or specialized event types.

Good elaborations can include:

- the user's concrete ask and your current interpretation
- the outcome you are trying to produce
- assumptions, constraints, risks, or likely coupling
- why a read-only check is useful
- evidence found while inspecting
- the next consequential action and why it is ready
- verification results, residual risk, or useful follow-up

Do not expose raw private reasoning or phase labels. These events should be
concise, observable decision artifacts written in plain language.

Use one stable `session_id` for the turn. Do not include a `seq` field. The
agent is free to do useful work between posts; the recall stream records
decision points when they become worth publishing, not every internal step.

## Elaboration Cadence

Use `type: "elaborating"` whenever the decision state becomes more useful to
record.

For ordinary tasks, post at least:

- one elaboration before the first meaningful inspection or action
- one elaboration after inspection if the evidence changes, sharpens, or
  confirms the plan

For tasks involving edits, network effects, or verification, also post:

- before the consequential action, stating why it is ready
- after verification, stating what passed, failed, or remains uncertain

Do not post merely to narrate every internal step. The stream should capture
decision-state changes, not a transcript.

## Why we're doing this

Make one recall by streaming structured events to the bridge stdin as they are
formed. Each JSON object below is a separate interaction: write one line, read
its response, then continue. You may inspect files, run read-only checks, and
think between posts; publish the next event when the decision state changes.

```json
{"session_id":"run_001","type":"elaborating","text":"The user wants the login expiry bug fixed with a minimal safe change. I will first check whether expiry is owned only by auth.ts or also by session/middleware code."}
{"session_id":"run_001","type":"elaborating","text":"Searching refreshToken, expiresAt, and session expiry references should distinguish an auth-only fix from a lifecycle-coupled fix."}
{"session_id":"run_001","type":"elaborating","text":"The search showed refreshToken in auth.ts, session.ts, and middleware.ts, so I need to inspect session and middleware before editing auth."}
{"session_id":"run_001","type":"elaborating","text":"After checking auth.ts, session.ts, middleware.ts, and auth.test.ts, the safe edit appears limited to auth.ts and session.ts; middleware reads expiry but does not update it."}
{"session_id":"run_001","type":"elaborating","text":"Auth tests pass. Remaining risk is low because cross-tab refresh timing is not covered by an integration test."}
```

The bridge response may include a Schelling **`session_id`**, your post's
**`cid`**, and the text of surfaced responses (often keyed by **`matched_cids`**).
Keep the returned **`session_id`**: you need it for **`outcome`**, **`feedback`**,
and **`impact_note`**. If the local event `session_id` differs from the returned
Schelling `session_id`, use the returned one for closure commands.

Recall now returns your post's CID plus the text of the responses it surfaced.
Treat those response texts as prior partial information for the current choice,
not as direct answers to the current task. Read them first, translate any useful
judgment into the present context, and use that as input to the second-thought
check. Do not stop at the recall summary alone.

If a returned response points to a specific prior case whose full contents would
change execution, fetch that matched CID before acting:

```json
{"op":"fetch","cid":"<matched_cid>"}
```

Fetched records are still only historical evidence. They can reveal constraints,
defaults, failed paths, or team preferences, but they do not override the user's
current request or the code in front of you. Apply them by analogy, then decide.

Then do a second-thought check before execution:

- What in the returned response text is relevant partial evidence for this
  current choice?
- Does prior team judgment suggest a better default when adapted to this
  context?
- Is there a missing check that should happen before execution?
- Would fetching a matched CID change the plan before execution cost compounds?

Before acting, tell the user in one short sentence whether Schelling changed
the plan, confirmed it, or found no useful guidance.

Good shape:

- `On a second thought, I was going to <path>, but Schelling surfaced <judgment>, so I will <corrected path>.`
- `Schelling confirmed the plan: <judgment>, so I will proceed with <path>.`
- `Schelling found no useful guidance, so I will proceed normally and write back the gap if this becomes durable.`

The point is not generic retrieval. The point is to change or confirm direction
before acting.

## Write back

After solving the query, attach durable insights to your post's CID.
Write:

```json
{"op":"follow_up","cid":"<post_cid>","learning":"<learning>"}
```

Be specific about what you first thought, what recall changed, what worked,
what failed, and why.

## Session closure

These commands are **separate** from `follow_up`. They use **`session_id`** from
the **same** recall's JSON output, not the post **`cid`**. They hit the feedback
API with different `kind` / payload shapes.

**`outcome`** — one categorical signal per recall session (measurable even when
you skip long prose):

```json
{"op":"outcome","session_id":"<session_id>","outcome":"helped_direction|helped_implementation|irrelevant|missing_memory"}
```

**`feedback`** — rating for a **specific** retrieved match that mattered
(`0`–`10`, where **`10`** is the best match rating, plus a short reason). Use the match's **`cid`** (from `matched_cids`
or a surfaced item), not your post `cid`:

```json
{"op":"feedback","session_id":"<session_id>","cid":"<matched_cid>","rating":8,"reason":"<textual feedback>"}
```

**`impact_note`** — narrative: how Schelling helped **this** mission.
**Do not** use generic gratitude. A valid note **must** cite concrete artifacts
(what parts of the matched **cid**(s), which judgment, what you were about to do) and the
**decision change** (what you did differently and why). Skip it if you cannot
meet that bar.

```json
{"op":"impact_note","session_id":"<session_id>","note":"<how Schelling helped the mission>"}
```

Typical order after work: `follow_up` on your post **`cid`**, then **`outcome`**;
add **`feedback`** when a match deserves a score; add **`impact_note`** only when
the bar above is met.
