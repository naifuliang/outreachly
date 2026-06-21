# Outreachly — Engineering Plan & Acceptance Criteria

This is the build roadmap. Phases ship in order; each merges via its own PR after multi-agent
acceptance against the criteria below. See [`../CONTRIBUTING.md`](../CONTRIBUTING.md) for process.

## Stack

- **Skill**: single Claude Skill (`skill/SKILL.md`) orchestrating the script layer.
- **Backend**: FastAPI (Python 3.13), scripts under `backend/app/scripts/` (CLI-invokable).
- **Frontend**: React + Vite + TypeScript, bilingual (中文 / English).
- **Storage**: local SQLite (`data/crm.sqlite`).
- **External APIs**: Google Places, Unipile (LinkedIn + Email + unified inbox), X API v2,
  Hunter/Apollo (email finding), NeverBounce (email verification).

## Channel → API map (all API, zero self-hosted scrapers)

| Step | Channel | API | Official? |
|---|---|---|---|
| Discover | Google Maps | Google Places API | ✅ |
| Discover + DM + inbox | LinkedIn | Unipile (REST) | 3rd-party managed |
| Discover + DM | Twitter/X | X API v2 (pay-per-use) | ✅ |
| Email find | — | Hunter / Apollo | 3rd-party |
| Email verify | — | NeverBounce | 3rd-party |
| Email send + reply sync | Email | Unipile (Gmail/Outlook) | 3rd-party |

---

## P0 · Scaffold & Foundations

**Goal**: stand up the single-Skill skeleton; keys and runtime in place.

Tasks: directory structure; `icp_schema.json`; `reference/channels.md`; `.env.example` + key
loading; SQLite init + schema (leads / campaigns / messages / events); unified API client
(timeout, retry, rate-limit, normalized errors); i18n scaffolding (zh + en).

**Acceptance**
- [ ] `python -m app.db.init_db` creates the 4 tables matching the schema.
- [ ] Each external API has a `ping`/minimal call returning 200 (free test tier/key).
- [ ] Missing key → clear error naming the missing env var (no stack crash).
- [ ] `SKILL.md` is recognized and lists the callable scripts.
- [ ] Both locales (zh, en) load; no hardcoded user-facing strings in scaffolded code.

## P1 · ICP Engine + Profile Editor

**Goal**: both entry modes produce a structured profile; visual field-level editing.

**Acceptance**
- [ ] A one-line product description yields an ICP with all required fields populated & schema-valid.
- [ ] Pasted ICP JSON validates and loads into the editor.
- [ ] Editing any field and saving persists (re-read matches).
- [ ] Invalid ICP (missing field / wrong type) is rejected with the specific field named.

## P2 · CRM + Lead Table

**Goal**: lead data backbone for all discovery/outreach.

**Acceptance**
- [ ] Duplicate lead writes collapse to one row (dedup key hit).
- [ ] Scoring distinguishes a high-ICP-match sample from a clear mismatch (high vs low score).
- [ ] State machine rejects illegal transitions (e.g. New → Converted without outreach).
- [ ] Frontend table filters/sorts by score & status; status change writes back to DB.

## P3 · Google Maps Discovery + Email Finding/Verification (first real chain)

**Goal**: from ICP to real contactable leads; validate end-to-end data path.

**Acceptance**
- [ ] A localized ICP returns ≥ 20 real businesses with websites.
- [ ] Email hit-rate is measurable; hit emails are format-valid.
- [ ] Each email carries a status label; `invalid` never enters the send queue.
- [ ] The full chain (ICP → Maps → email → verify → CRM) runs in one command, visible in frontend.

## P4 · Sequences + Email Send + Reply Follow-up (core loop)

**Goal**: close the generate → send → reply → CRM-update loop.

**Acceptance**
- [ ] Generated sequence: each email differs and contains lead-specific personalization.
- [ ] A real email is sent to a test inbox and received (end-to-end delivery).
- [ ] After the test inbox replies, `reply_handler` fetches it and classifies intent.
- [ ] "Replied" leads auto-stop the follow-up sequence; CRM status syncs.
- [ ] Frontend shows campaign progress and a per-lead message timeline.

## P5 · Full Channel: LinkedIn + Twitter Discovery & DM

**Goal**: all three channels; true multi-channel outreach.

**Acceptance**
- [ ] LinkedIn: ICP-based search lands leads; a real DM is sent to a test account.
- [ ] Twitter: keyword search lands accounts; a real DM is sent.
- [ ] Replies from all channels flow into one unified inbox view.
- [ ] Cross-channel dedup: same lead not double-counted.
- [ ] Draft mode never sends; auto mode sends — toggle behaves correctly.

## P6 · Analytics Dashboard + Demo Polish

**Goal**: funnel visualization; demoable.

**Acceptance**
- [ ] Dashboard numbers match DB events (spot-checked).
- [ ] One continuous demo runs from "product description" to "reply in funnel".
- [ ] Any external-API failure degrades gracefully (no white screen/crash).

---

## Definition of Done (global)

- Every script independently CLI-invokable.
- Critical paths have minimal self-tests (dedup, state machine, scoring, email-verify filter).
- All external calls go through the unified client (retry + rate-limit + normalized errors).
- `SKILL.md` orchestrates the scripts into a one-sentence-triggered full flow.

## Dependencies

P0 → P1 → P2 are the foundation. P3 is the first real chain. P4 depends on P3 data. P5 depends
on P4's send/reply framework. P6 last. **P3 done = demoable; P4 done = full story; P5/P6 = bonus.**
