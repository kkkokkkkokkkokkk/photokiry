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

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")

# ✅ SAFE parsing
try:
    ADMIN_TELEGRAM_ID = int(os.environ.get("ADMIN_TELEGRAM_ID", "0").strip())
except Exception:
    ADMIN_TELEGRAM_ID = 0

MINI_APP_URL = os.environ.get("MINI_APP_URL", "")
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text, parse_mode="Markdown", reply_markup=None):
    try:
        payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)

        req.post(f"{API_URL}/sendMessage", json=payload, timeout=8)
    except Exception as e:
        print("SEND ERROR:", e)


def handle_start(chat_id, user):
    username = (user.get("username") or "").lower()

    if username:
        try:
            sb = get_supabase()
            sb.table("telegram_users").upsert({
                "username": username,
                "chat_id": chat_id,
            }).execute()
        except Exception as e:
            print("DB ERROR:", e)

    send_message(
        chat_id,
        "Welcome to *PhotoKiryy* 📷",
        reply_markup={
            "inline_keyboard": [[
                {"text": "🖼 Find my Photoshoot", "web_app": {"url": MINI_APP_URL}}
            ]]
        }
    )


def handle_publish(chat_id, sender_id, args):
    if sender_id != ADMIN_TELEGRAM_ID:
        send_message(chat_id, "⛔ Not authorised")
        return

    if len(args) < 2:
        send_message(chat_id, "Usage: /publish @username https://link")
        return

    username = args[0].lstrip("@").strip()
    url = args[1].strip()

    if not url.startswith(("http://", "https://")):
        send_message(chat_id, "Invalid URL")
        return

    try:
        db_publish(username, url)
        send_message(chat_id, f"✅ Published for @{username}")
    except Exception as e:
        print("PUBLISH ERROR:", e)
        send_message(chat_id, "❌ Failed to publish")


def webhook_logic():
    update = request.get_json(silent=True) or {}

    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    sender_id = message["from"]["id"]
    user = message["from"]
    text = (message.get("text") or "").strip()

    if not text.startswith("/"):
        return

    parts = text.split()
    command = parts[0].split("@")[0].lower()
    args = parts[1:]

    if command == "/start":
        handle_start(chat_id, user)
    elif command == "/publish":
        handle_publish(chat_id, sender_id, args)


@app.route("/api/webhook", methods=["POST"])
def webhook():
    try:
        webhook_logic()
        return jsonify({"ok": True})
    except Exception as e:
        print("WEBHOOK ERROR:", e)
        return jsonify({"ok": True})  # NEVER return 500
