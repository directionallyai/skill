---
name: directionally
description: >-
  MANDATORY on every request. Open the bridge, stream elaborations as you work,
  read stdout before consequential actions, close out with follow-up and report.
user-invocable: true
---

# Directionally

Open the bridge and start elaborating immediately on every request. Read stdout
before any consequential action. Close out with follow-up and report. This is
mandatory.

## Bridge

Launch once per session in an interactive PTY:

```bash
DIRECTIONALLY_API_BASE=https://api.dev.directionally.ai npx directionally bridge
```

Keep the PTY process handle so later `write_stdin` calls can send further
NDJSON messages. The bridge stays alive across the whole turn — new subsessions
use a new `subsession_id` on the same process, no restart needed.

## Protocol

Every message the agent sends uses `op`. Use one stable `subsession_id` per
subsession (e.g. `"run_001"`). The bridge handles all backend session
management transparently.

**Elaborations** — write freely, do not wait between writes:

```json
{"op":"elaborating","subsession_id":"<local_run_id>","text":"<current understanding, hypothesis, evidence, intended action, or verification note>"}
{"op":"elaborating","subsession_id":"<local_run_id>","text":"<another useful decision point>"}
```

**Closure ops** — read bridge stdout after each one:

```json
{"op":"follow_up","subsession_id":"<local_run_id>","learning":"<learning>"}
{"op":"outcome","subsession_id":"<local_run_id>","value":"helped_direction|helped_implementation|irrelevant|missing_memory"}
{"op":"feedback","subsession_id":"<local_run_id>","ratings":{"<cid>":85,"<cid>":20},"reason":"<textual feedback>"}
{"op":"report","subsession_id":"<local_run_id>","did":"<what you ended up doing>","issues":"<issues encountered, if any>"}
{"op":"impact_note","subsession_id":"<local_run_id>","note":"<how Directionally helped the mission>"}
```

Bridge stdout is NDJSON. The only kinds you need to act on:

- `consideration` — a retrieval result with `cid` and `text`; read stdout at
  decision gates to collect these. Multiple may arrive per read.
- `bridge_error` — surface to user if unrecoverable

Everything else is internal bridge state; you do not need to act on it.

## Elaborating

Start streaming elaborations immediately from the user's query. The consult
*is* the work — open the bridge, fire the first elaboration with your initial
read of the task, then keep working. Each decision point that changes your
understanding becomes another elaboration, streamed as it forms.

The safety boundary: read stdout at least once before any edit, commit, or
answer.

Good elaborations are concise, observable decision artifacts:

- your initial interpretation of the task
- assumptions, constraints, or coupling you notice
- evidence found while inspecting
- a revised plan after new evidence
- why a consequential action is ready to take
- what passed or failed after verification

Do not narrate every step. Do not expose private reasoning or label phases.
Stream when the decision state changes, not on a fixed cadence.

Do not include a `seq` field.

## Reading considerations

Elaborate, then read stdout. Do not block — take what is there and move on.

Read stdout at decision gates:

- before a consequential edit, command, commit, or answer
- before final write-back

Collect any `consideration` lines that have arrived. Each has a `cid` and
`text`. Use all of them — later ones may supersede earlier ones as the
retrieval re-ranks, but earlier shallow matches are still useful. If nothing
has arrived yet, proceed.

Read each consideration's `text` as prior team judgment — something encountered
before that bears on what you are about to do. Apply it by analogy:

- If it describes something that failed or was reverted, treat it as a constraint
- If it describes a choice that worked, lean toward it as a default
- If it does not bear on the current decision, note that and proceed

Before acting, tell the user in one short sentence whether the direction consult
changed the plan, confirmed it, or found no useful guidance.

## Write back

After completing the task, close the subsession with the following ops in order.

**`follow_up`** — the most important write-back. This is raw material for the
direction compiler: not a task summary but a reusable behavioral lesson that
should change what a future agent does when it encounters the same class of
problem.

Write it with these ingredients:

- **pattern** — name the recurring situation, not just what happened this time
- **context trigger** — what observable condition should wake this up next time
- **behavior** — what a future agent should do differently
- **misread risk** — the plausible wrong interpretation to avoid, when obvious
- **receipt** — an observable signal that the right path was taken

Good:

> "Middleware that reads expiry but never writes it should be excluded from the
> fix scope. Trigger: any expiry bug touching both auth and session layers.
> Behavior: check middleware for writes before including it. Misread risk:
> assuming middleware involvement because it imports the expiry field. Receipt:
> grep confirms no write path in middleware."

Bad:

> "Completed the task and the considerations were useful."

```json
{"op":"follow_up","subsession_id":"<local_run_id>","learning":"<learning>"}
```

**`report`** — what you ended up doing and any issues encountered:

```json
{"op":"report","subsession_id":"<local_run_id>","did":"<what you did>","issues":"<issues, or empty string if none>"}
```

**`outcome`** — one categorical signal:

```json
{"op":"outcome","subsession_id":"<local_run_id>","value":"helped_direction|helped_implementation|irrelevant|missing_memory"}
```

**`feedback`** — rate each consideration received, `cid` → score (0–100):

```json
{"op":"feedback","subsession_id":"<local_run_id>","ratings":{"<cid>":85,"<cid>":20},"reason":"<why they were or weren't useful>"}
```

**`impact_note`** — how Directionally concretely changed what you did. Must
cite specific considerations and the decision change. Skip if you cannot meet
that bar:

```json
{"op":"impact_note","subsession_id":"<local_run_id>","note":"<how Directionally helped the mission>"}
```
