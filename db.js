// public/db.js — PhotoKiryy API client
// All paths are relative so they work on any Vercel deployment URL automatically.

const db = {

  /**
   * POST /api/lookup
   * Checks if @username has a photoshoot and triggers OTP delivery via bot.
   * Returns { found: bool, sessionToken: string }
   */
  async lookupUser(username) {
    const res = await fetch('/api/lookup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.replace(/^@/, '') }),
    });
    if (!res.ok) throw new Error(`Lookup error: ${res.status}`);
    return res.json();
  },

  /**
   * POST /api/verify
   * Validates the one-time code.
   * Returns { valid: bool, photoshootUrl: string|null }
   */
  async verifyCode(sessionToken, code) {
    const res = await fetch('/api/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sessionToken, code }),
    });
    if (!res.ok) throw new Error(`Verify error: ${res.status}`);
    return res.json();
  },

};

Object.freeze(db);
