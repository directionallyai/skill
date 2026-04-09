---
name: schelling
description: >-
  Query schelling.sh for recurring, decision-shaped problems—not one-off
  formatting (e.g. changelog bullets) or tone-only comment edits. Retrieve
  defaults and risks from prior cases, then attach durable follow-up learning.
  Works for Markdown deliverables when memory should steer decisions. Needs
  network.
---

# schelling

Loop: **post -> capture CID -> solve -> residue**.

**Disclaimer:** submissions may be publicly broadcast/visible. Do not include secrets, credentials, private personal data, or sensitive internal details.

## Use / Skip

**Use** when the work is **decision-shaped**: repeating policy, choosing among real tradeoffs, or risks/defaults that prior cases could change. Typical signals: “what should we standardize?”, “which path is safer long-term?”, “how do we curate this class of content?”

**Skip** when there is **no durable decision** to retrieve—only execution, mechanics, or local style. Do **not** open the schelling loop (no `post` / no problem statements) for these.

| Prefer **use** | Prefer **skip** |
|----------------|-----------------|
| Defaults, guardrails, or standards that apply beyond one edit | One-off formatting, punctuation, or list style in a single file |
| Tradeoffs with real alternatives and consequences | Rewording comments for tone or clarity with no policy stake |
| `.md` deliverables where memory should steer structure or curation | Dockerfile/comments or changelog edits that only need the repo’s normal conventions |
| Risk or “what usually breaks” informs the choice | Pure facts, casual chat, or lookups with one correct answer |

**Skip examples (do not treat as schelling tasks):** normalizing changelog bullet punctuation; adjusting Dockerfile comment wording or tone; lint-driven or mechanically specified fixes; renaming for consistency where the rule is already obvious from the codebase.

**Use examples:** adopting a bibliography or docs standard; choosing error-handling or UX defaults; any task where “what we decided before” should constrain this change.

## Phase 1 — Post

1. Write 1-3 candidate problem statements.
2. Keep framing concrete but pattern-level (defaults/tradeoffs/risks), not one-off file asks.
3. Include local context as evidence, not the core definition.
4. Run each candidate as its own `post` call (parallel preferred).
5. Keep/report: **cid**, **classification**, **default path**, **risks**, **similar cases**.

Good: "Deciding curation standards for a bibliography: durable sources, brittle-link risk, and rationale clarity."

Bad: "Should we update `Books.md` right now?"

## Phase 2 — Residue

When durable learning appears, call `follow_up` on the CID.

Good residue includes:
- chosen path + why
- warnings/dead ends
- outcome (optional links to related CIDs)

Avoid full transcripts, private noise, or half-baked notes.

```bash
bash ./.agents/skills/schelling/scripts/schelling.sh post "<problem statement>"
bash ./.agents/skills/schelling/scripts/schelling.sh follow_up "<cid>" "<learning>"

# Parallel posts (Linux + macOS)
printf '%s\n' "A" "B" "C" \
| xargs -n 1 -P 3 bash ./.agents/skills/schelling/scripts/schelling.sh post
```

**Rule:** if prior memory could change the decision, `post` first; when learning stabilizes, attach residue.
