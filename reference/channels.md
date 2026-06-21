# Channel & Provider Reference

Auth and the core endpoints per provider. Loaded on demand (not from `SKILL.md`'s front matter)
to keep the skill entry point lean. All keys live in `.env` (see `.env.example`).

> Principle: **everything via API, zero self-hosted scrapers.**

---

## Unipile — LinkedIn discovery/DM, Email send, unified inbox (`unipile`)

- **Env**: `UNIPILE_DSN` (workspace base URL incl. port), `UNIPILE_API_KEY`
- **Auth header**: `X-API-KEY: <key>` · **Docs**: https://developer.unipile.com/
- **Connection**: the DSN uses a **non-standard port** — call it **directly** (our scripts pass
  `use_proxy=False`); a CONNECT proxy that only allows :443 will time out. You must also connect
  at least one real account (LinkedIn/WhatsApp/…) via the dashboard's hosted-auth wizard;
  `GET /api/v1/accounts` returns them.
- **Use**:
  - List accounts — `GET /api/v1/accounts`
  - LinkedIn search — `GET /api/v1/linkedin/search`
  - Send message — `POST /api/v1/chats` / `POST /api/v1/messages`
  - Send email — `POST /api/v1/emails` · Inbox sync — `GET /api/v1/messages`, `GET /api/v1/emails`
- **Ping**: list accounts returns 200.

## X (Twitter) API v2 — discovery/DM (`x`)

- **Env**: `X_BEARER_TOKEN` (app bearer for read/search; DM send adds user-context OAuth at P5)
- **Base**: `https://api.twitter.com` · **Docs**: https://docs.x.com/x-api
- **Pricing (2026)**: pay-per-use — ~$0.015 / DM send, ~$0.010 / user-tied read.
- **Use**:
  - Resolve user — `GET /2/users/by/username/{name}`
  - Recent search — `GET /2/tweets/search/recent?query=<keywords>`
  - Send DM — `POST /2/dm_conversations/with/{participant_id}/messages` (user context)
- **Ping**: resolve a known username with the app bearer token.

## Hunter.io — email finding (`hunter`)

- **Env**: `HUNTER_API_KEY` · **Base**: `https://api.hunter.io`
- **Docs**: https://hunter.io/api-documentation/v2
- **Use**: Domain search — `GET /v2/domain-search?domain=&api_key=` · Email finder —
  `GET /v2/email-finder?domain=&first_name=&last_name=&api_key=`
- **Ping**: `GET /v2/account?api_key=` returns plan info.

## NeverBounce — email verification (`neverbounce`)

- **Env**: `NEVERBOUNCE_API_KEY` · **Base**: `https://api.neverbounce.com`
- **Docs**: https://developers.neverbounce.com/
- **Use**: Single check — `GET /v4/single/check?email=&key=` → valid | invalid | disposable |
  catchall | unknown
- **Ping**: `GET /v4/account/info?key=` returns `status: success`.
- **Rule**: `invalid` (and optionally `disposable`) never enters the send queue.

---

> Note: ICP generation, copywriting and reply classification are done by Claude when the skill
> runs — there is no LLM API key in this skill.
