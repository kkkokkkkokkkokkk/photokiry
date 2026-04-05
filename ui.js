// ui.js — PhotoKiryy Telegram Mini App UI controller
// Handles all screen transitions, input logic, and calls db.js for data.

(function () {
  'use strict';

  // ── Telegram WebApp SDK ────────────────────────
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    // Let Telegram know we are a mini app
    tg.MainButton.hide();
  }

  // ── State ──────────────────────────────────────
  const state = {
    username: '',
    sessionToken: null,
    photoshootUrl: null,
  };

  // ── DOM refs ───────────────────────────────────
  const screens = {
    landing: document.getElementById('screen-landing'),
    auth:    document.getElementById('screen-auth'),
    success: document.getElementById('screen-success'),
  };

  const els = {
    usernameInput:   document.getElementById('tg-username'),
    searchHint:      document.getElementById('search-hint'),
    searchBtn:       document.getElementById('search-btn'),

    displayUsername: document.getElementById('display-username'),
    codeRow:         document.getElementById('code-row'),
    codeBoxes:       Array.from(document.querySelectorAll('.code-box')),
    authHint:        document.getElementById('auth-hint'),
    verifyBtn:       document.getElementById('verify-btn'),
    backBtn:         document.getElementById('back-btn'),

    successUsername: document.getElementById('success-username'),
    galleryLink:     document.getElementById('gallery-link'),
  };

  // ── Screen management ──────────────────────────
  function showScreen(name) {
    Object.entries(screens).forEach(([key, el]) => {
      el.classList.toggle('hidden', key !== name);
    });
  }

  // ── Hint helpers ───────────────────────────────
  function setHint(el, msg, type = '') {
    el.textContent = msg;
    el.className = 'hint' + (type ? ` ${type}` : '');
  }

  // ── Loading state ──────────────────────────────
  function setLoading(btn, loading, label) {
    btn.disabled = loading;
    btn.textContent = loading ? 'Please wait…' : label;
    btn.style.opacity = loading ? '0.65' : '1';
  }

  // ── Username validation ────────────────────────
  function validateUsername(raw) {
    const clean = raw.trim().replace(/^@/, '');
    if (!clean) return { ok: false, msg: 'Please enter your Telegram username.' };
    if (!/^[a-zA-Z0-9_]{3,32}$/.test(clean))
      return { ok: false, msg: 'Username must be 3–32 chars: letters, numbers, underscores.' };
    return { ok: true, value: clean };
  }

  // ── SCREEN 1: Search ───────────────────────────
  async function handleSearch() {
    const validation = validateUsername(els.usernameInput.value);
    if (!validation.ok) {
      setHint(els.searchHint, validation.msg, 'error');
      els.usernameInput.focus();
      return;
    }

    setLoading(els.searchBtn, true, 'Search my Photoshoot');
    setHint(els.searchHint, 'Looking up your username…');

    try {
      const result = await db.lookupUser(validation.value);

      if (!result.found) {
        setHint(els.searchHint, 'No photoshoot found for this username.', 'error');
        setLoading(els.searchBtn, false, 'Search my Photoshoot');
        return;
      }

      state.username = validation.value;
      state.sessionToken = result.sessionToken;

      // Transition to auth screen
      els.displayUsername.textContent = state.username;
      resetCodeBoxes();
      showScreen('auth');
      setTimeout(() => els.codeBoxes[0]?.focus(), 80);

    } catch (err) {
      console.error(err);
      setHint(els.searchHint, 'Connection error. Please try again.', 'error');
    } finally {
      setLoading(els.searchBtn, false, 'Search my Photoshoot');
    }
  }

  // ── SCREEN 2: Code input ───────────────────────
  function getCodeValue() {
    return els.codeBoxes.map(b => b.value).join('').toUpperCase();
  }

  function resetCodeBoxes() {
    els.codeBoxes.forEach(b => {
      b.value = '';
      b.classList.remove('filled', 'error-shake');
    });
    setHint(els.authHint, 'Check your Telegram — the bot sent you a 6-character code.');
  }

  function shakeCodeBoxes() {
    els.codeBoxes.forEach(b => {
      b.classList.remove('error-shake');
      void b.offsetWidth; // reflow to restart animation
      b.classList.add('error-shake');
    });
    setTimeout(() => els.codeBoxes.forEach(b => b.classList.remove('error-shake')), 450);
  }

  function initCodeBoxes() {
    els.codeBoxes.forEach((box, i) => {
      box.addEventListener('input', () => {
        // Keep only alphanumeric, uppercase
        const v = box.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
        box.value = v ? v[v.length - 1] : '';
        box.classList.toggle('filled', !!box.value);

        if (box.value && i < els.codeBoxes.length - 1) {
          els.codeBoxes[i + 1].focus();
        }

        if (getCodeValue().length === 6) handleVerify();
      });

      box.addEventListener('keydown', e => {
        if (e.key === 'Backspace' && !box.value && i > 0) {
          els.codeBoxes[i - 1].value = '';
          els.codeBoxes[i - 1].classList.remove('filled');
          els.codeBoxes[i - 1].focus();
        }
      });

      box.addEventListener('paste', e => {
        e.preventDefault();
        const text = (e.clipboardData.getData('text') || '')
          .toUpperCase().replace(/[^A-Z0-9]/g, '');
        els.codeBoxes.forEach((b, idx) => {
          b.value = text[idx] || '';
          b.classList.toggle('filled', !!b.value);
        });
        const next = Math.min(text.length, els.codeBoxes.length - 1);
        els.codeBoxes[next].focus();
        if (getCodeValue().length === 6) handleVerify();
      });
    });
  }

  async function handleVerify() {
    const code = getCodeValue();
    if (code.length < 6) {
      setHint(els.authHint, 'Please enter all 6 characters of the code.', 'error');
      return;
    }

    setLoading(els.verifyBtn, true, 'Access my Gallery');
    setHint(els.authHint, 'Verifying your code…');

    try {
      const result = await db.verifyCode(state.sessionToken, code);

      if (!result.valid) {
        setHint(els.authHint, 'Incorrect code. Please try again.', 'error');
        shakeCodeBoxes();
        els.codeBoxes.forEach(b => { b.value = ''; b.classList.remove('filled'); });
        els.codeBoxes[0].focus();
        return;
      }

      state.photoshootUrl = result.photoshootUrl;
      els.successUsername.textContent = state.username;
      els.galleryLink.href = state.photoshootUrl;
      showScreen('success');

    } catch (err) {
      console.error(err);
      setHint(els.authHint, 'Connection error. Please try again.', 'error');
    } finally {
      setLoading(els.verifyBtn, false, 'Access my Gallery');
    }
  }

  // ── SCREEN 3: Open gallery ─────────────────────
  function handleOpenGallery(e) {
    e.preventDefault();
    if (!state.photoshootUrl) return;

    // Inside Telegram Mini App, open URL in Telegram's built-in browser
    if (tg) {
      tg.openLink(state.photoshootUrl);
    } else {
      window.open(state.photoshootUrl, '_blank', 'noopener');
    }
  }

  // ── Event wiring ───────────────────────────────
  els.searchBtn.addEventListener('click', handleSearch);
  els.usernameInput.addEventListener('keydown', e => {
    if (e.key === 'Enter') handleSearch();
  });

  els.verifyBtn.addEventListener('click', handleVerify);
  els.backBtn.addEventListener('click', () => {
    showScreen('landing');
    setHint(els.searchHint, 'Enter the username you use on Telegram.');
  });

  els.galleryLink.addEventListener('click', handleOpenGallery);

  // ── Bootstrap ──────────────────────────────────
  initCodeBoxes();
  showScreen('landing');

})();
