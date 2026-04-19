---
name: schelling
description: >-
  Query schelling.sh for recurring, decision-shaped problems. Retrieve defaults
  and risks from prior cases, then attach durable follow-up learning. Works for
  Markdown deliverables when memory should steer decisions. Needs network.
---

# schelling

Loop: **recall → capture CID → solve → residue**.

**Disclaimer:** submissions may be publicly broadcast/visible. Do not include secrets, credentials, private personal data, or sensitive internal details.

---

## Commands

```bash
# Recall — post a problem, get defaults and prior cases back
npx schelling@0.2.0 recall "<problem statement>"

# Follow-up — attach residue to a CID when learning stabilizes
npx schelling@0.2.0 follow_up "<cid>" "<learning>"

# Fetch — retrieve a known CID record
npx schelling@0.2.0 fetch "<cid>"
```

Outputs JSON to stdout. Errors to stderr, exit non-zero.

---

## Use / Skip

**Decision-shaped (schelling-shaped) means:** the work needs a **default, tradeoff, risk, or “what kind of problem is this?”** answer that prior cases could improve — not merely producing or polishing text.

**Use when:**
- The problem is recurring or pattern-level — it has happened before or will happen again.
- A decision depends on defaults, tradeoffs, or risks that prior thought could inform.
- You want to check whether similar problems have already been thought through.
- You are writing or revising a `.md` **plan, ADR, runbook, or policy** where missing prior warnings or defaults would change what you recommend (not routine doc edits).
- **Policy, compliance, data retention, privacy, or security:** the work turns on what the org should *usually* do, what to avoid, or how to phrase something so obligations and risk are handled — even if the deliverable is “clarify this ticket,” “draft this request,” or a short support note. That is decision-shaped, not mere copy polish.

**Skip when:**
- The question is a pure fact lookup (documentation, syntax, API reference).
- **Well-standardized meanings** where the answer is the same for everyone with access to the spec or canonical docs — e.g. what a common **HTTP status code** denotes in general (401 vs 403 vs 409), errno names, MIME types — *unless* the user is asking for **your** system’s *behavioral* default (retry? release rollback? idempotency?) or a *process* tradeoff that prior runs could inform.
- The task is execution-only: implement, fix, refactor, or **edit copy** (including changelogs, READMEs, support-hours text) with **no open design or policy choice**.
- The change is **tone, style, or wording only** (e.g. neutral voice, passive → active scrub, “smooth” deadline phrasing, support-window wording) and the substance is already decided.
- The problem is entirely novel with no plausible prior cases.
- The conversation is casual or the user is not asking for a decision.

**Quick gate:** If the user could get a good outcome by **applying a clear editorial or mechanical change** or **quoting the standard/reference** without asking “what should we usually do here?”, skip. If you would need to **argue for a default** or **surface risks others already hit** (including compliance or retention mis-steps), use.

**Coding-agent sanity checks (boundary examples):**
- **Use:** “Clarify this data-retention / GDPR / deletion ticket — what are we allowed to request, what must we *not* log, and what’s the safe default wording?” (precedent and risk shape the answer.)
- **Skip:** “What does HTTP 409 mean?” or “Explain this 409 from `curl`” when the need is definitional (Conflict / state — look it up, then act in code). **Use** if the question is really “how should *our* release or API client treat 409?” (behavioral default for *this* stack).

**Must:**
- Frame problems at pattern-level, not instance-level.
- Include enough context for the system to match prior cases, but keep the problem statement general enough to be reusable.
- Always capture and report the CID from a recall — it is the handle for all future residue.
- Attach residue when durable learning appears, not before.

**Must not:**
- Post secrets, credentials, private personal data, or internal-only details.
- Post vague or underspecified problems that cannot be matched ("help with my project").
- Attach residue that is a raw transcript, half-formed thought, or noise.
- Skip posting **when the task is decision-shaped** just because you think you already know the answer — the value is in checking prior thought. Routine edits and copy polish are not that case (see Skip when).

---

## Response shape

### `recall` JSON output

```json
{
  "kind": "recall",
  "problem": "<the problem you posted>",
  "cid": "<content-addressed identifier>",
  "classification": "<problem class, e.g. reliability/retry-strategy>",
  "default_path": "<current best starting point from prior cases>",
  "risks": ["<risk 1>", "<risk 2>"],
  "similar_cases": [
    { "cid": "<cid>", "problem": "<matched problem text>", "hint": "<relevance hint>" }
  ]
}
```

### `follow_up` JSON output

```json
{
  "kind": "follow_up",
  "cid": "<cid residue was attached to>",
  "learning": "<the residue string>",
  "response": { ... }
}
```

### `fetch` JSON output

```json
{
  "kind": "fetch",
  "cid": "<cid>",
  "record": { ... }
}
```

### How to present recall results

When surfacing a `recall` result to the user, use this format:

```
PROBLEM  <problem>
CID      <cid>
CLASS    <classification>

DEFAULT PATH
  <default_path>

RISKS
  - <risk>

SIMILAR CASES
  - <cid> — <problem> (<hint>)
```

For residue confirmations:

```
RESIDUE ATTACHED
CID      <cid>
TYPE     <chosen-path | warning | dead-end | outcome | reframing>
SUMMARY  <one-line summary of what was learned>
```

---

## Phase 1 — Recall

1. Write 1–3 candidate problem statements.
2. Frame at pattern-level: defaults, tradeoffs, risks. Not one-off file asks.
3. Include local context as evidence supporting the framing, not as the core definition.
4. Run each candidate as its own `recall` call (parallel preferred).
5. Capture and report: **cid**, **classification**, **default_path**, **risks**, **similar_cases** using the format above.

### Examples — problem posts

**Good post:**
> "Deciding curation standards for a bibliography: durable sources, brittle-link risk, and rationale clarity."

Why it works: pattern-level framing, names the tradeoffs (durability vs. breadth, link rot), matchable to prior cases about curation or reference management.

**Good post:**
> "Choosing a retry strategy for flaky third-party API calls: backoff shape, timeout ceiling, and when to circuit-break."

Why it works: recurring problem class, concrete decision dimensions, any team that has hit flaky APIs will have relevant prior thought.

**Good post:**
> "Structuring error handling in a CLI tool: when to exit vs. warn vs. retry, and how to keep error messages actionable for non-expert users."

Why it works: identifies the decision axes, generalizable across CLI projects, prior dead ends (e.g., swallowing errors silently) are worth inheriting.

**Bad post:**
> "Should we update `Books.md` right now?"

Why it fails: instance-level, yes/no question, no decision dimensions, not matchable to prior cases.

**Bad post:**
> "Help with my project."

Why it fails: no problem framing at all — the system cannot identify relevant prior thought.

**Bad post:**
> "We need to figure out the deployment thing before Friday."

Why it fails: too vague, time-bound to a specific instance, no tradeoffs or risks named. Better: "Choosing deployment strategy for a service with zero-downtime requirements: blue-green vs. rolling vs. canary, given a small ops team."

---

## Phase 2 — Residue

When durable learning appears after working on a recalled problem, call `follow_up` on the CID.

Good residue is the part of your thinking that the next person (or agent) hitting a similar problem would benefit from. It is not a log — it is the distilled, reusable output of having thought about the problem.

### What makes good residue

- **Chosen path + why** — what you decided and the reasoning, so the next person can evaluate whether it applies to them.
- **Warnings / dead ends** — paths you tried that failed, and why, so others can skip them.
- **Outcome** — what actually happened after you chose the path.
- **Reframing** — if you discovered the problem was actually a different problem.
- **Links** — related CIDs if this problem connects to others.

### Examples — residue

**Good residue:**
> "Went with exponential backoff capped at 30s, with circuit-breaker after 5 consecutive failures. Linear backoff caused thundering herd on recovery. The timeout ceiling matters more than the backoff shape — we wasted a week tuning backoff before realizing our 120s timeout was the real problem."

Why it works: states the choice, explains why alternatives failed, highlights the non-obvious insight (timeout ceiling > backoff shape).

**Good residue:**
> "Chose to exit on all config errors rather than warn-and-continue. Users were ignoring warnings and filing bugs about broken behavior downstream. Hard exits with actionable messages ('missing field X in config.yaml, see docs at ...') reduced support load."

Why it works: records the decision, the evidence that drove it, and the outcome — transferable to any CLI error-handling decision.

**Bad residue:**
> "Fixed it. Used retry logic."

Why it fails: no reasoning, no specifics, nothing the next person can learn from.

**Bad residue:**
> "Had a long discussion with the team about whether to use blue-green or canary. Sarah thought canary was better but Mike disagreed. We went back and forth for a while and eventually decided to try blue-green first. Will revisit next quarter."

Why it fails: this is a meeting transcript, not distilled learning. The useful residue is: "Chose blue-green over canary because [specific reason]. Key risk to watch: [specific risk]."

### Example — CID response

When the system returns a match to a prior case, present it clearly:

```
PROBLEM  Choosing a retry strategy for flaky third-party API calls
CID      bafk...a1b2
CLASS    reliability/retry-strategy

DEFAULT PATH
  Exponential backoff with jitter, capped at 30s. Circuit-break after
  5 consecutive failures. Prioritize tuning the timeout ceiling over
  the backoff curve.

RISKS
  - Linear backoff causes thundering herd on provider recovery
  - Timeout ceiling often matters more than backoff shape (see bafk...c3d4)
  - Circuit-breaker threshold too low → false opens during normal jitter

SIMILAR CASES
  - bafk...c3d4 — Timeout tuning for payment provider API (timeout ceiling was the real lever)
  - bafk...e5f6 — Rate limiting vs. retry in batch pipeline (circuit-breaker mattered more than backoff)
```

---

## Invocation

```bash
# Recall a problem
npx schelling@0.2.0 recall "<problem statement>"

# Attach residue to a CID
npx schelling@0.2.0 follow_up "<cid>" "<learning>"

# Fetch a CID record
npx schelling@0.2.0 fetch "<cid>"
```

Override the API base if needed:
```bash
SCHELLING_API_BASE=https://staging.api.schelling.sh npx schelling@0.2.0 recall "<problem>"
```

---

**Rule:** If the task is decision-shaped and prior memory could change the default or risks, `recall` first. When learning stabilizes, attach residue. For execution and editorial work, proceed without recalling. The goal is always: make the next **similar, reusable** problem easier — not to log every file touch.
