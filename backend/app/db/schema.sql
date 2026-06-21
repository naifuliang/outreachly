-- Outreachly CRM schema. Four core tables: leads, campaigns, messages, events.
-- JSON-ish blobs are stored as TEXT (sqlite). Timestamps are ISO-8601 strings.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS campaigns (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    icp         TEXT,                          -- JSON: the ICP this campaign targets
    channels    TEXT,                          -- JSON array: ["email","linkedin","twitter"]
    status      TEXT NOT NULL DEFAULT 'draft', -- draft | running | paused | done
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS leads (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source        TEXT NOT NULL,               -- maps | linkedin | twitter
    external_id   TEXT,                        -- provider-side id (place_id, profile id, ...)
    name          TEXT,
    company       TEXT,
    website       TEXT,
    domain        TEXT,                        -- normalized website host, used for dedup
    email         TEXT,
    email_status  TEXT,                        -- valid | risky | invalid | unknown
    phone         TEXT,
    location      TEXT,
    title         TEXT,
    profile       TEXT,                        -- JSON: raw/enriched provider data
    score         INTEGER DEFAULT 0,           -- 0-100 ICP match
    status        TEXT NOT NULL DEFAULT 'new', -- new | contacted | replied | converted | rejected
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Dedup keys: same provider+external_id, or same email, or same domain.
CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_source_external
    ON leads (source, external_id) WHERE external_id IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_email
    ON leads (email) WHERE email IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_leads_domain ON leads (domain);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads (status);

CREATE TABLE IF NOT EXISTS messages (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id        INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    campaign_id    INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    channel        TEXT NOT NULL,              -- email | linkedin | twitter
    direction      TEXT NOT NULL,              -- outbound | inbound
    sequence_step  INTEGER DEFAULT 0,          -- 0 = first touch, 1.. = follow-ups
    subject        TEXT,
    body           TEXT,
    status         TEXT,                       -- draft | queued | sent | delivered | failed
    intent         TEXT,                       -- (inbound) interested | not_interested | later
    sent_at        TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_lead ON messages (lead_id);
CREATE INDEX IF NOT EXISTS idx_messages_campaign ON messages (campaign_id);

CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id      INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    campaign_id  INTEGER REFERENCES campaigns(id) ON DELETE SET NULL,
    type         TEXT NOT NULL,                -- discovered | enriched | sent | opened | replied ...
    payload      TEXT,                         -- JSON
    created_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_events_lead ON events (lead_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events (type);
