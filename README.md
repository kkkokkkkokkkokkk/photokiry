# PhotoKiryy — Telegram Mini App

Photoshoot gallery finder for Telegram clients, hosted on **Vercel** with **Supabase** as the database.

---

## Project Structure

```
photokiryy/
├── public/                  ← Static Mini App (served by Vercel)
│   ├── index.html           ← 3-screen UI
│   ├── style.css            ← All styles
│   ├── db.js                ← API client (fetch wrapper)
│   └── ui.js                ← All screen logic
│
├── api/                     ← Vercel Serverless Functions (Python)
│   ├── _shared.py           ← Supabase client + shared DB helpers
│   ├── lookup.py            ← POST /api/lookup
│   ├── verify.py            ← POST /api/verify
│   ├── publish.py           ← POST /api/publish  (admin only)
│   └── webhook.py           ← POST /api/webhook  (Telegram bot)
│
├── supabase/
│   └── schema.sql           ← Run once in Supabase SQL Editor
│
├── vercel.json              ← Vercel routing config
├── requirements.txt         ← Python dependencies
└── .env.example             ← Copy to .env for local dev
```

---

## How It Works

```
User opens Mini App
        ↓
Enters @telegram_username  →  POST /api/lookup
        ↓
Supabase confirms username has a photoshoot
        ↓
Bot sends 6-char OTP code to user's Telegram DM
        ↓
User enters code  →  POST /api/verify
        ↓
Supabase confirms code → returns photoshoot URL
        ↓
"Open Photoshoot" button appears
```

---

## Deployment Guide

### Step 1 — Supabase

1. Go to [supabase.com](https://supabase.com) → **New project** (free plan is fine)
2. Once created: **SQL Editor → New Query**
3. Paste the entire contents of `supabase/schema.sql` and click **Run**
4. Go to **Project Settings → API** and copy:
   - **Project URL** → `SUPABASE_URL`
   - **service_role** key (under "Project API keys") → `SUPABASE_SERVICE_KEY`
   > ⚠️ Use the `service_role` key, NOT the `anon` key. The service key bypasses RLS and is only used server-side inside Vercel functions — it is never sent to the browser.

---

### Step 2 — Telegram Bot

1. Message **@BotFather** on Telegram
2. `/newbot` → follow prompts → copy the **BOT_TOKEN**
3. Get your numeric Telegram ID by messaging **@userinfobot** → copy it as `ADMIN_TELEGRAM_ID`

---

### Step 3 — Vercel

1. Push this project to a GitHub repository
2. Go to [vercel.com](https://vercel.com) → **Add New Project** → import your repo
3. In **Settings → Environment Variables**, add all variables from `.env.example`:

   | Name | Value |
   |------|-------|
   | `SUPABASE_URL` | your Supabase project URL |
   | `SUPABASE_SERVICE_KEY` | your service_role key |
   | `BOT_TOKEN` | your BotFather token |
   | `ADMIN_TELEGRAM_ID` | your numeric Telegram ID |
   | `ADMIN_API_TOKEN` | a strong random string |
   | `MINI_APP_URL` | `https://your-project.vercel.app` |

4. Click **Deploy**

---

### Step 4 — Register the Telegram Webhook

After Vercel deploys, open this URL in your browser (replace values):

```
https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://your-project.vercel.app/api/webhook
```

You should see: `{"ok":true,"result":true,"description":"Webhook was set"}`

---

### Step 5 — Register the Mini App with BotFather

1. Message @BotFather → `/newapp`
2. Select your bot
3. Follow prompts → set the URL to `https://your-project.vercel.app`
4. BotFather gives you a short link like `t.me/YourBot/app`

---

## Admin Usage

In your Telegram bot chat (only works for `ADMIN_TELEGRAM_ID`):

```
/publish @client_username https://link-to-photoshoot.com
```

This stores the link in Supabase. The client can then find it via the Mini App.

To update a link, just run `/publish` again — it overwrites the previous URL.

---

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/api/lookup` | None | Check username, send OTP |
| `POST` | `/api/verify` | None | Verify OTP, get gallery URL |
| `POST` | `/api/publish` | Bearer token | Store photoshoot link |
| `POST` | `/api/webhook` | Telegram signature | Bot command handler |

---

## Security

- **OTP codes** are 6 characters, expire in **15 minutes**, and are deleted on first use
- **Session tokens** expire in **1 hour**
- **`/api/publish`** requires `Authorization: Bearer <ADMIN_API_TOKEN>`
- **`/publish` bot command** only works for `ADMIN_TELEGRAM_ID`
- **Supabase** is accessed only from server-side functions using the service key — the browser never touches the database directly
- **RLS** is enabled on all tables with no public policies

---

## Local Development

```bash
# Install Python deps
pip install -r requirements.txt

# Copy and fill in env vars
cp .env.example .env

# Install Vercel CLI
npm i -g vercel

# Run locally (simulates serverless functions)
vercel dev
```

The app will be available at `http://localhost:3000`.
