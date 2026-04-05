# api/publish.py — POST /api/publish
# Admin-only endpoint. Used by the Telegram bot webhook to store photoshoot links.
# Protected by Bearer token (ADMIN_API_TOKEN env var).

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request
from _shared import db_publish, cors_response, require_admin

app = Flask(__name__)


@app.route("/api/publish", methods=["OPTIONS"])
def options():
    return cors_response({}, 200)


@app.route("/api/publish", methods=["POST"])
@require_admin
def publish():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip().lstrip("@")
    url = data.get("url", "").strip()

    if not username or not url:
        return cors_response({"error": "username and url are required"}, 400)

    if not url.startswith(("http://", "https://")):
        return cors_response({"error": "url must start with http:// or https://"}, 400)

    db_publish(username, url)
    return cors_response({"success": True, "message": f"Published photoshoot for @{username}"})
