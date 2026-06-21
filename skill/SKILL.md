---
name: outreachly
description: AI-driven multi-channel cold-outreach autopilot. Use when the user wants to find leads and run cold outreach from a product idea or customer profile — generate an ICP (ideal customer profile), discover leads via Google Maps / LinkedIn / Twitter, find & verify emails, write personalized cold-email sequences and DMs, send across Email / LinkedIn / Twitter, and track replies with CRM auto-update. Bilingual (中文 / English).
---

# Outreachly

Turn a product description (or a ready customer profile) into qualified leads and personalized
outreach across Email, LinkedIn, and Twitter/X — with reply tracking and CRM auto-update.

## When to use

The user wants to: build a customer profile / ICP, find leads, get contact emails, write cold
emails or DMs, run an outreach campaign, or track replies. Works in 中文 or English.

## Setup (once)

1. Copy `.env.example` → `.env` and fill the keys you have (see `reference/channels.md`).
2. Initialize the CRM: `python -m app.db.init_db` (run from `backend/`).
3. Check provider connectivity: `python -m app.integrations`.

## Workflow & scripts

Run scripts from `backend/` as `python -m app.scripts.<name>`. Each is independently invokable.

1. **ICP** — `icp_generate` — product/target → structured ICP, or validate a pasted one.
   Schema: `reference/icp_schema.json`.
2. **Discover** — `discover_maps` (Google Places), `discover_linkedin` (Unipile),
   `discover_twitter` (X API) — ICP → leads into the CRM.
3. **Enrich** — `email_finder` (Hunter) → `email_verify` (NeverBounce). `invalid` emails are
   excluded from sending.
4. **CRM** — `crm` — dedup, ICP-match scoring, lead status state machine.
5. **Write** — `write_sequence` — personalized cold-email sequence + channel-specific DMs.
6. **Send** — `send_email` (Unipile), `send_linkedin_dm` (Unipile), `send_twitter_dm` (X API).
7. **Reply** — `reply_handler` — pull replies (unified inbox), classify intent, update CRM.

## Channels & providers

See `reference/channels.md` for auth and endpoints. All discovery/outreach is via official or
managed APIs — no self-hosted scrapers.

## Notes

- Respect the per-channel draft/auto toggle: draft mode never sends.
- All user-facing text is bilingual; keep both locales in sync.
