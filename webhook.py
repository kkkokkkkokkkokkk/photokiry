# api/webhook.py — POST /api/webhook
# Telegram bot webhook. Register this URL with:
#   https://api.telegram.org/bot<TOKEN>/setWebhook?url=https://yourapp.vercel.app/api/webhook
#
# Handles: /start, /publish, /help

import os
import sys
import json
import logging

sys.path.insert(0, os.path.dirname(__file__))

import requests as req
from flask import Flask, request, jsonify
from _shared import db_publish, get_supabase

log = logging.getLogger(__name__)
app = Flask(__name__)

BOT_TOKEN         = os.environ.get("BOT_TOKEN", "")
ADMIN_TELEGRAM_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "0"))
MINI_APP_URL      = os.environ.get("MINI_APP_URL", "https://yourapp.vercel.app")
API_URL           = f"https://api.telegram.org/bot{BOT_TOKEN}"


# ── Telegram helpers ───────────────────────────────────────────────────────

def send_message(chat_id: int, text: str, parse_mode: str = "Markdown", reply_markup: dict = None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    req.post(f"{API_URL}/sendMessage", json=payload, timeout=8)


# ── Command handlers ───────────────────────────────────────────────────────

def handle_start(chat_id: int, user: dict):
    """Greet user, save their chat_id, and show the Mini App button."""
    username = (user.get("username") or "").lower()

    # Store chat_id so we can DM OTP codes later
    if username:
        sb = get_supabase()
        sb.table("telegram_users").upsert({
            "username": username,
            "chat_id": chat_id,
        }).execute()

    send_message(
        chat_id,
        "Welcome to *PhotoKiryy* 📷\n\nTap below to find and access your photoshoot gallery.",
        reply_markup={
            "inline_keyboard": [[
                {
                    "text": "🖼 Find my Photoshoot",
                    "web_app": {"url": MINI_APP_URL},
                }
            ]]
        }
    )


def handle_publish(chat_id: int, sender_id: int, args: list[str]):
    """/publish @username https://link"""
    if sender_id != ADMIN_TELEGRAM_ID:
        send_message(chat_id, "⛔ You are not authorised to use this command.")
        return

    if len(args) < 2:
        send_message(
            chat_id,
            "Usage: `/publish @username https://link`\n\n"
            "Example:\n`/publish @john\\_doe https://drive.google.com/...`"
        )
        return

    raw_username = args[0].lstrip("@").strip()
    url = args[1].strip()

    if not raw_username or not raw_username.replace("_", "").isalnum():
        send_message(chat_id, "❌ Invalid username format.")
        return

    if not url.startswith(("http://", "https://")):
        send_message(chat_id, "❌ URL must start with `http://` or `https://`")
        return

    try:
        db_publish(raw_username, url)
        send_message(
            chat_id,
            f"✅ *Photoshoot published!*\n\n"
            f"👤 Username: @{raw_username}\n"
            f"🔗 URL: {url}\n\n"
            f"The client can now access their photos via the Mini App."
        )
    except Exception as e:
        log.error("publish error: %s", e)
        send_message(chat_id, f"❌ Error saving to database: `{e}`")


def handle_help(chat_id: int, sender_id: int):
    msg = (
        "*PhotoKiryy Bot*\n\n"
        "/start — Open the photoshoot finder\n"
        "/help  — Show this message\n"
    )
    if sender_id == ADMIN_TELEGRAM_ID:
        msg += "\n*Admin:*\n`/publish @username https://link`"
    send_message(chat_id, msg)


# ── Webhook endpoint ───────────────────────────────────────────────────────

@app.route("/api/webhook", methods=["POST"])
def webhook():
    update = request.get_json(silent=True) or {}

    message = update.get("message") or update.get("edited_message")
    if not message:
        return jsonify({"ok": True})

    chat_id   = message["chat"]["id"]
    sender_id = message["from"]["id"]
    user      = message["from"]
    text      = (message.get("text") or "").strip()

    if not text.startswith("/"):
        return jsonify({"ok": True})

    parts   = text.split()
    command = parts[0].split("@")[0].lower()  # handle /cmd@botname
    args    = parts[1:]

    if command == "/start":
        handle_start(chat_id, user)
    elif command == "/publish":
        handle_publish(chat_id, sender_id, args)
    elif command == "/help":
        handle_help(chat_id, sender_id)

    return jsonify({"ok": True})
