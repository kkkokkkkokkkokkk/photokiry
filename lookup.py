# api/lookup.py — POST /api/lookup
# Checks if a username has a photoshoot and issues a session token + OTP.

import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request
from _shared import (
    db_lookup, db_store_otp, generate_code,
    cors_response, CODE_TTL_MINUTES
)

app = Flask(__name__)


@app.route("/api/lookup", methods=["OPTIONS"])
def options():
    return cors_response({}, 200)


@app.route("/api/lookup", methods=["POST"])
def lookup():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip().lstrip("@")

    if not username:
        return cors_response({"error": "username required"}, 400)

    session_token = db_lookup(username)

    if not session_token:
        # Don't reveal whether the username exists — just say not found
        return cors_response({"found": False})

    # Generate OTP and store it
    code = generate_code()
    db_store_otp(username, code)

    # Send OTP to user via Telegram bot
    _send_otp_via_bot(username, code)

    return cors_response({"found": True, "sessionToken": session_token})


def _send_otp_via_bot(username: str, code: str):
    """
    Look up the user's chat_id from Supabase and send them the code via bot DM.
    Requires the user to have /start-ed the bot at least once.
    """
    import requests as req
    from _shared import get_supabase

    sb = get_supabase()
    row = sb.table("telegram_users").select("chat_id").eq("username", username.lower()).execute()

    if not row.data:
        # User hasn't started the bot yet — code will be visible in bot logs
        import logging
        logging.warning("No chat_id for @%s — OTP not sent via DM", username)
        return

    chat_id = row.data[0]["chat_id"]
    bot_token = os.environ.get("BOT_TOKEN", "")

    req.post(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        json={
            "chat_id": chat_id,
            "parse_mode": "Markdown",
            "text": (
                f"🔐 *Your PhotoKiryy access code:*\n\n"
                f"`{code}`\n\n"
                f"_Valid for {CODE_TTL_MINUTES} minutes. Never share this code._"
            ),
        },
        timeout=5,
    )


# Vercel calls the Flask app as a WSGI app
# No if __name__ == "__main__" needed
