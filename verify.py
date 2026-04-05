# api/verify.py — POST /api/verify
# Validates the OTP code and returns the photoshoot URL.

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request
from _shared import db_verify_code, cors_response

app = Flask(__name__)


@app.route("/api/verify", methods=["OPTIONS"])
def options():
    return cors_response({}, 200)


@app.route("/api/verify", methods=["POST"])
def verify():
    data = request.get_json(silent=True) or {}
    session_token = data.get("sessionToken", "").strip()
    code = data.get("code", "").strip()

    if not session_token or not code:
        return cors_response({"error": "sessionToken and code are required"}, 400)

    url = db_verify_code(session_token, code)

    if not url:
        return cors_response({"valid": False})

    return cors_response({"valid": True, "photoshootUrl": url})
