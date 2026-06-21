# Outreachly — Engineering Plan & Acceptance Criteria

Build roadmap for a **single, importable Claude Skill**. Phases ship in order; each merges via
its own PR after multi-agent acceptance against the criteria below. Process: see
[`../CONTRIBUTING.md`](../CONTRIBUTING.md).

## Architecture

- **One skill = the repo.** `SKILL.md` at the root; import the whole folder.
- **Claude does the reasoning** — ICP generation, copywriting, reply classification — in the
  conversation. No LLM API key in the skill.
- **`scripts/` do external IO only** — call provider APIs and read/write the SQLite CRM.
- **Only dependency: `httpx`.** Everything else is the Python standard library.
- **Optional UI**: `scripts/serve_ui.py` serves a single-file `web/index.html` (no build step).
- **Bilingual**: Claude replies/writes in 中文 or English; the UI has a zh/en toggle.

## Channel → API map (all API, zero self-hosted scrapers)

| Step | Channel | API | Script |
|---|---|---|---|
| Discover + DM + inbox | LinkedIn | Unipile | `linkedin.py` |
| Discover + DM | Twitter/X | X API v2 | `twitter.py` |
| Email find | — | Hunter | `find_email.py` |
| Email verify | — | NeverBounce | `verify_email.py` |
| Email send + reply sync | Email | Unipile | `send_email.py` |

---

## P0 · Skill scaffold

**Goal**: an importable skill skeleton that runs.

**Acceptance**
- [ ] `python scripts/crm.py init` creates the 4 tables (leads, campaigns, messages, events).
- [ ] Each provider script has a `ping` (200 with a key; clear named error without).
- [ ] Missing key → clear error naming the env var (no stack crash).
- [ ] `SKILL.md` is at the repo root with valid frontmatter and lists the scripts; every
      referenced script exists and is CLI-invokable.
- [ ] Optional UI launches (`serve_ui.py`) and serves the bilingual `web/index.html`.

## P1 · ICP Engine

**Goal**: structured ICP from a product description, or validate a pasted one.

**Acceptance**
- [ ] A one-line product description yields an ICP with all required fields, valid against
      `reference/icp_schema.json`.
- [ ] A pasted ICP is validated; invalid input is rejected naming the offending field.
- [ ] The user can edit any field before discovery (confirmed in conversation and/or UI).

## P2 · CRM scoring & status

**Goal**: dedup (done in P0), ICP-match scoring, and a lead status state machine.

**Acceptance**
- [ ] Duplicate writes collapse to one row (dedup key hit). *(P0 baseline; keep green.)*
- [ ] Scoring distinguishes a high-ICP-match lead from a clear mismatch (high vs low).
- [ ] Status transitions reject illegal moves (e.g. new → converted without outreach).

## P3 · Email enrichment

**Goal**: turn discovered leads that have a website/domain into verified email contacts.

**Acceptance**
- [ ] For leads with a domain (e.g. from a LinkedIn company or an X bio link), email finding
      returns candidate addresses; hit-rate is measurable.
- [ ] Verification labels each address (valid/risky/invalid); `invalid` never enters the send queue.
- [ ] The chain (lead domain → find → verify → CRM) runs end to end, visible in the UI.

## P4 · Sequences + send + reply (core loop)

**Acceptance**
- [ ] A personalized sequence (first touch + follow-ups) is generated per lead, each distinct.
- [ ] A real email is sent to a test inbox and received.
- [ ] A reply is fetched and intent-classified; repliers auto-stop follow-ups; CRM updates.

## P5 · LinkedIn + Twitter channels

**Acceptance**
- [ ] LinkedIn: ICP search lands leads; a real DM is sent to a test account.
- [ ] Twitter: keyword search lands accounts; a real DM is sent.
- [ ] Replies across channels are visible together; cross-channel dedup holds.
- [ ] Draft mode never sends; auto mode sends.

## P6 · Analytics + polish

**Acceptance**
- [ ] UI funnel numbers match CRM data.
- [ ] One continuous demo runs from product description to a tracked reply.
- [ ] Any provider failure degrades gracefully (clear message, no crash).

---

## Definition of Done (global)

- Every script independently CLI-invokable (`python scripts/<name>.py [--help|ping|run]`).
- Critical paths have tests (`tests/`, pytest): dedup, CRM init, env errors, scoring, status.
- All external calls go through `_common.request` (timeout + retry + normalized errors).
- `SKILL.md` orchestrates the scripts and reasoning into a one-sentence-triggered flow.

## Dependencies

P0 → P1 → P2 foundation. P3 = first real chain. P4 depends on P3 data. P5 depends on P4's
send/reply framework. P6 last. **P3 done = demoable; P4 done = full story; P5/P6 = bonus.**
