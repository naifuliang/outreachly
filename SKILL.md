---
name: outreachly
description: AI-driven multi-channel cold-outreach autopilot. Use when the user wants to find leads and run cold outreach starting from a product idea or a customer profile — build an ICP (ideal customer profile), discover leads via Google Maps / LinkedIn / Twitter, find and verify emails, write personalized cold-email sequences and DMs, send across Email / LinkedIn / Twitter, and track replies with the local CRM. Bilingual: replies and outreach copy in 中文 or English to match the user.
---

# Outreachly

Turn a product description (or a ready customer profile) into qualified leads and personalized
outreach across Email, LinkedIn, and Twitter/X — with reply tracking in a local CRM.

**Division of labor:** *you* (Claude) do the reasoning — generating the ICP, writing the
sequences/DMs, and classifying replies — directly in the conversation. The `scripts/` only do
what you can't: call external APIs and read/write the SQLite CRM.

## Setup (once)

```bash
pip install -r requirements.txt          # only dependency: httpx
cp .env.example .env                      # add keys for the channels you'll use
python scripts/crm.py init                # create the local CRM
python scripts/serve_ui.py --open         # OPTIONAL: launch the local UI (skip if not wanted)
```

Run any script with `--help`. Check connectivity per provider with `python scripts/<x>.py ping`.

## Workflow

1. **Build the ICP** *(you reason; `icp.py` validates/persists)* — From the user's product/target,
   write a structured ICP conforming to `reference/icp_schema.json`. If the user pasted a profile,
   refine that instead. Then make it concrete:
   - validate: `echo '<icp json>' | python scripts/icp.py validate`
   - save as active ICP: `echo '<icp json>' | python scripts/icp.py save`
   Show the ICP to the user and let them edit any field (in chat, or in the optional UI) before
   discovery. `icp.py` rejects invalid input naming the offending field.

2. **Discover leads** *(scripts)* — Using the ICP's keywords/geographies:
   - Google Maps → `python scripts/discover_maps.py run --query "..."`
   - LinkedIn → `python scripts/linkedin.py search --keywords "..."`
   - Twitter/X → `python scripts/twitter.py search --keywords "..."`
   Each upserts into the CRM (deduped).

3. **Enrich** *(scripts)* — `find_email.py run --domain ...` then `verify_email.py run --email ...`.
   Never send to `invalid` addresses.

4. **Score & manage** *(scripts)* — `crm.py` dedups, scores leads against the ICP, and tracks
   status: `new → contacted → replied → converted | rejected`.

5. **Write outreach** *(you do this)* — Write a personalized cold-email sequence (first touch +
   follow-ups) and channel-specific DMs, using each lead's enriched details. Match the user's
   language (中文/English). Keep a draft/auto distinction: show drafts before anything sends.

6. **Send** *(scripts)* — `send_email.py`, `linkedin.py dm`, `twitter.py dm`. Drafts never send.

7. **Track replies** *(scripts fetch, you classify)* — pull replies, then classify intent
   (interested / not interested / later), stop sequences for repliers, and update the CRM.

## Channels & providers

All discovery/outreach is via official or managed APIs — no self-hosted scrapers. Auth and
endpoints: `reference/channels.md`. Keys live in `.env` only.

## Optional UI

`python scripts/serve_ui.py` opens a single-file, bilingual dashboard (CRM leads, provider
connectivity, roadmap) at http://127.0.0.1:8000. It is entirely optional — the skill works
without it.

## Files

- `scripts/` — `icp.py`, `crm.py`, `discover_maps.py`, `find_email.py`, `verify_email.py`,
  `send_email.py`, `linkedin.py`, `twitter.py`, `serve_ui.py`, `_common.py`
- `reference/` — `icp_schema.json`, `channels.md`
- `web/index.html` — optional UI · `data/` — local SQLite CRM
