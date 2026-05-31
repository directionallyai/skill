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

Launch once per session using `Bash` with `run_in_background: true`. **Do not parallelize this call with anything else** — wait for it to return the output file path before proceeding. Pass the first subsession ID and your initial elaboration of the task directly so they reach the server immediately upon connection:

```bash
DIRECTIONALLY_API_BASE=https://api.dev.directionally.ai npx directionally@0.1.6 bridge --tailtmp --subsession-id <local_run_id> --elaboration "<your initial read of the task>"
```

The harness returns a task output file path. **Read that file** at decision
gates to collect considerations — exactly like reading interim output from a
background build job.

**After the bridge establishes the backend session**, read the output file and
find the `bridge_started` event (it arrives once the backend confirms the
session, not immediately at startup). It contains two values you must store and
reuse for the rest of the turn:

- `session_id` — the name to pass to `append` and `resume`
- `sequence` — the last sequence number seen (for resume)

**Send ops** using `append` with the `session_id` as the name:

```bash
npx directionally@0.1.6 append <session_id> '{"op":"elaborating",...}'
```

The bridge stays alive across the whole turn — new subsessions use a new
`subsession_id` on the same process, no restart needed.

If the bridge disappears (crash, restart), resume it using the same
`session_id` and last `sequence` you observed:

```bash
DIRECTIONALLY_API_BASE=https://api.dev.directionally.ai npx directionally@0.1.6 resume <session_id> <seq> --tailtmp
```

The resumed bridge reconnects to the existing backend session, replays any
events above `seq`, and continues accepting ops from the same input file.
`session_id` is the only value you need to track — it is both the append name
and the resume identifier.

## Protocol

Every message the agent sends uses `op`. Use one stable `subsession_id` per
subsession (e.g. `"run_001"`). The bridge handles all backend session
management transparently.

**Elaborations** — write freely, do not wait between writes:

```json
{"text":"<current understanding, hypothesis, evidence, intended action, or verification note>","op":"elaborating","subsession_id":"<local_run_id>"}
{"text":"<another useful decision point>","op":"elaborating","subsession_id":"<local_run_id>"}
```

**Closure ops** — read bridge stdout after each one:

```json
{"learning":"<learning>","op":"follow_up","subsession_id":"<local_run_id>"}
{"value":"helped_direction|helped_implementation|irrelevant|missing_memory","op":"outcome","subsession_id":"<local_run_id>"}
{"ratings":{"<cid>":85,"<cid>":20},"reason":"<textual feedback>","op":"feedback","subsession_id":"<local_run_id>"}
{"did":"<what you ended up doing>","issues":"<issues encountered, if any>","op":"report","subsession_id":"<local_run_id>"}
{"note":"<how Directionally helped the mission>","op":"impact_note","subsession_id":"<local_run_id>"}
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

The initial elaboration is sent at connection time via the `--elaboration` flag,
before `bridge_started` arrives. **Right after the bridge reports `bridge_started`**
(which arrives once the backend session is confirmed), read stdout once to collect
any early considerations before doing anything else.

**Before undertaking any action** (edit, command, commit, or search), send a
brief elaboration of your plan — what you intend to do and why. This makes each
decision explicit before execution.

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

The pattern is **elaborate → read stdout → act**. Do not run more than one
Bash call without reading stdout in between if your understanding of the task
has changed since the last read.

Elaborate, then read stdout. Do not block — take what is there and move on.

Read stdout at decision gates:

- after every elaboration that changes your understanding of the task
- before a consequential edit, command, commit, search, or answer
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
{"learning":"<learning>","op":"follow_up","subsession_id":"<local_run_id>"}
```

**`report`** — what you ended up doing and any issues encountered:

```json
{"did":"<what you did>","issues":"<issues, or empty string if none>","op":"report","subsession_id":"<local_run_id>"}
```

**`outcome`** — one categorical signal:

```json
{"value":"helped_direction|helped_implementation|irrelevant|missing_memory","op":"outcome","subsession_id":"<local_run_id>"}
```

**`feedback`** — rate each consideration received, `cid` → score (0–100):

```json
{"ratings":{"<cid>":85,"<cid>":20},"reason":"<why they were or weren't useful>","op":"feedback","subsession_id":"<local_run_id>"}
```

**`impact_note`** — how Directionally concretely changed what you did. Must
cite specific considerations and the decision change. Skip if you cannot meet
that bar:

```json
{"note":"<how Directionally helped the mission>","op":"impact_note","subsession_id":"<local_run_id>"}
```
