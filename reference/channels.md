# Channel & Provider Reference

Auth and the core endpoints we use, per provider. Loaded on demand (not from `SKILL.md`'s
front matter) to keep the Skill entry point lean. All keys live in `.env` (see `.env.example`).

> Principle: **everything via API, zero self-hosted scrapers.**

---

## Google Places API — discovery (`places`)

- **Env**: `GOOGLE_PLACES_API_KEY`
- **Base**: `https://maps.googleapis.com`
- **Docs**: https://developers.google.com/maps/documentation/places/web-service
- **Use**:
  - Text Search — `GET /maps/api/place/textsearch/json?query=<icp keywords + geo>&key=`
  - Find Place — `GET /maps/api/place/findplacefromtext/json?input=&inputtype=textquery&key=`
  - Place Details — `GET /maps/api/place/details/json?place_id=&fields=name,website,formatted_phone_number,formatted_address&key=`
- **Yields**: name, website (→ domain → email finding), phone, address. `place_id` is the dedup key.
- **Ping**: Find Place returns JSON `status` in {OK, ZERO_RESULTS}; `REQUEST_DENIED` = bad key.

## Unipile — LinkedIn discovery/DM, Email send, unified inbox (`unipile`)

- **Env**: `UNIPILE_DSN` (workspace base URL, e.g. `https://apiXXX.unipile.com:YYYYY`), `UNIPILE_API_KEY`
- **Auth header**: `X-API-KEY: <key>`
- **Docs**: https://developer.unipile.com/
- **Use**:
  - List accounts — `GET /api/v1/accounts`
  - LinkedIn search — `GET /api/v1/linkedin/search` (people/company; ICP → query)
  - Send message — `POST /api/v1/chats` / `POST /api/v1/messages`
  - Send email — `POST /api/v1/emails`
  - Unified inbox / sync — `GET /api/v1/messages`, `GET /api/v1/emails`
- **Ping**: list accounts returns 200 with connected mailbox/LinkedIn accounts.

## X (Twitter) API v2 — discovery/DM (`x`)

- **Env**: `X_BEARER_TOKEN` (app bearer for read/search). DM send needs user-context OAuth (P5).
- **Base**: `https://api.twitter.com`
- **Pricing (2026)**: pay-per-use default — ~$0.015 / DM send, ~$0.010 / user-tied read.
- **Docs**: https://docs.x.com/x-api
- **Use**:
  - Resolve user — `GET /2/users/by/username/{name}`
  - Recent search — `GET /2/tweets/search/recent?query=<icp keywords>`
  - Send DM — `POST /2/dm_conversations/with/{participant_id}/messages` (user context)
- **Ping**: resolve a known username with the app bearer token.

## Hunter.io — email finding (`hunter`)

- **Env**: `HUNTER_API_KEY`
- **Base**: `https://api.hunter.io`
- **Docs**: https://hunter.io/api-documentation/v2
- **Use**:
  - Domain search — `GET /v2/domain-search?domain=&api_key=`
  - Email finder — `GET /v2/email-finder?domain=&first_name=&last_name=&api_key=`
  - Account — `GET /v2/account?api_key=`
- **Ping**: account endpoint returns plan info.

## NeverBounce — email verification (`neverbounce`)

- **Env**: `NEVERBOUNCE_API_KEY`
- **Base**: `https://api.neverbounce.com`
- **Docs**: https://developers.neverbounce.com/
- **Use**:
  - Single check — `GET /v4/single/check?email=&key=` → result: valid | invalid | disposable | catchall | unknown
  - Account info — `GET /v4/account/info?key=`
- **Ping**: account info returns `status: success`.
- **Rule**: `invalid` (and optionally `disposable`) never enters the send queue.

## Anthropic — ICP generation & copywriting (`llm`)

- **Env**: `ANTHROPIC_API_KEY`
- **Model**: `claude-opus-4-8` (latest, most capable) for ICP/sequence generation.
- **Docs**: https://docs.anthropic.com/
