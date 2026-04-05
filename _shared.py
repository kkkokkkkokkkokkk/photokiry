# api/_shared.py — helpers shared across all Vercel serverless functions
# Imported by lookup.py, verify.py, publish.py, webhook.py

import os
import secrets
import string
from datetime import datetime, timezone, timedelta
from functools import wraps

from supabase import create_client, Client

# ── Supabase client ────────────────────────────────────────────────────────
_supabase: Client | None = None

def get_supabase() -> Client:
    global _supabase
    if _supabase is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]  # service role — never exposed to browser
        _supabase = create_client(url, key)
    return _supabase


# ── Constants ──────────────────────────────────────────────────────────────
CODE_LENGTH      = 6
CODE_TTL_MINUTES = 15
SESSION_TTL_HOURS = 1


# ── Time helpers ───────────────────────────────────────────────────────────
def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def in_minutes(n: int) -> str:
    return (utcnow() + timedelta(minutes=n)).isoformat()

def in_hours(n: int) -> str:
    return (utcnow() + timedelta(hours=n)).isoformat()

def is_expired(ts: str) -> bool:
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt < utcnow()


# ── Code / token generators ────────────────────────────────────────────────
def generate_code(length: int = CODE_LENGTH) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def generate_token() -> str:
    return secrets.token_urlsafe(32)


# ── CORS headers (Telegram Mini Apps need these) ───────────────────────────
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization",
}

def cors_response(body: dict, status: int = 200) -> tuple:
    from flask import jsonify, make_response
    resp = make_response(jsonify(body), status)
    for k, v in CORS_HEADERS.items():
        resp.headers[k] = v
    return resp


# ── Admin token guard ──────────────────────────────────────────────────────
def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        from flask import request
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()
        if token != os.environ.get("ADMIN_API_TOKEN", ""):
            from flask import jsonify, make_response
            resp = make_response(jsonify({"error": "Forbidden"}), 403)
            for k, v in CORS_HEADERS.items():
                resp.headers[k] = v
            return resp
        return f(*args, **kwargs)
    return decorated


# ── DB operations ──────────────────────────────────────────────────────────

def db_lookup(username: str) -> str | None:
    """
    Check if username has a photoshoot.
    If yes, create a session and return the session token.
    """
    sb = get_supabase()
    uname = username.lower()

    result = sb.table("photoshoots").select("id").eq("username", uname).execute()
    if not result.data:
        return None

    token = generate_token()
    sb.table("sessions").upsert({
        "token": token,
        "username": uname,
        "expires_at": in_hours(SESSION_TTL_HOURS),
    }).execute()

    return token


def db_store_otp(username: str, code: str):
    sb = get_supabase()
    sb.table("otp_codes").upsert({
        "username": username.lower(),
        "code": code,
        "expires_at": in_minutes(CODE_TTL_MINUTES),
    }).execute()


def db_verify_code(session_token: str, code: str) -> str | None:
    """
    Verify the OTP. Returns the photoshoot URL on success, None on failure.
    Deletes the OTP on success (single-use).
    """
    sb = get_supabase()

    sess = sb.table("sessions").select("username, expires_at").eq("token", session_token).execute()
    if not sess.data:
        return None

    row = sess.data[0]
    if is_expired(row["expires_at"]):
        return None

    username = row["username"]

    otp = sb.table("otp_codes").select("code, expires_at").eq("username", username).execute()
    if not otp.data:
        return None

    otp_row = otp.data[0]
    if is_expired(otp_row["expires_at"]):
        return None

    if otp_row["code"].upper() != code.upper():
        return None

    # Consume the code
    sb.table("otp_codes").delete().eq("username", username).execute()

    shoot = sb.table("photoshoots").select("url").eq("username", username).execute()
    return shoot.data[0]["url"] if shoot.data else None


def db_publish(username: str, url: str) -> bool:
    sb = get_supabase()
    now = utcnow().isoformat()
    sb.table("photoshoots").upsert({
        "username": username.lower(),
        "url": url,
        "updated_at": now,
    }).execute()
    return True
