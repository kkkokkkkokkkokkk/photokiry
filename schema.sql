-- supabase/schema.sql
-- Run this entire file in the Supabase Dashboard → SQL Editor → New Query

-- ── photoshoots ────────────────────────────────────────────────────────────
-- One row per client. Username is stored lowercase.
CREATE TABLE IF NOT EXISTS photoshoots (
  id         BIGSERIAL PRIMARY KEY,
  username   TEXT NOT NULL UNIQUE,           -- telegram @username, lowercase
  url        TEXT NOT NULL,                  -- link to the photoshoot gallery
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- ── telegram_users ────────────────────────────────────────────────────────
-- Stores chat_id so the bot can DM OTP codes.
-- Populated when a user sends /start to the bot.
CREATE TABLE IF NOT EXISTS telegram_users (
  id         BIGSERIAL PRIMARY KEY,
  username   TEXT NOT NULL UNIQUE,           -- telegram @username, lowercase
  chat_id    BIGINT NOT NULL,                -- permanent Telegram user ID
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ── sessions ──────────────────────────────────────────────────────────────
-- Short-lived token issued after a successful username lookup.
CREATE TABLE IF NOT EXISTS sessions (
  id         BIGSERIAL PRIMARY KEY,
  token      TEXT NOT NULL UNIQUE,
  username   TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ── otp_codes ─────────────────────────────────────────────────────────────
-- Single-use one-time codes. Deleted on first successful use.
CREATE TABLE IF NOT EXISTS otp_codes (
  id         BIGSERIAL PRIMARY KEY,
  username   TEXT NOT NULL UNIQUE,           -- one active code per user at a time
  code       TEXT NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ── Indexes ───────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_photoshoots_username   ON photoshoots (username);
CREATE INDEX IF NOT EXISTS idx_telegram_users_username ON telegram_users (username);
CREATE INDEX IF NOT EXISTS idx_sessions_token          ON sessions (token);
CREATE INDEX IF NOT EXISTS idx_otp_codes_username      ON otp_codes (username);

-- ── Row Level Security ────────────────────────────────────────────────────
-- All tables use the service role key (server-side only).
-- RLS is enabled but NO public policies are added — the browser never
-- talks to Supabase directly, only the Vercel serverless functions do.

ALTER TABLE photoshoots    ENABLE ROW LEVEL SECURITY;
ALTER TABLE telegram_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions       ENABLE ROW LEVEL SECURITY;
ALTER TABLE otp_codes      ENABLE ROW LEVEL SECURITY;

-- ── Auto-cleanup (optional) ───────────────────────────────────────────────
-- Run periodically via Supabase cron (pg_cron) or a Vercel cron job.
-- DELETE FROM sessions   WHERE expires_at < now();
-- DELETE FROM otp_codes  WHERE expires_at < now();
