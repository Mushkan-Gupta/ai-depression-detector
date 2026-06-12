/* ============================================================
   auth.js — MindEase Authentication Logic
   Handles login, registration, form validation, JWT storage
   ============================================================ */

const API_BASE_URL = 'http://127.0.0.1:5000';

// ── Storage Helpers ─────────────────────────────────────────
function saveSession(token, user) {
  localStorage.setItem('mindease_token', token);
  localStorage.setItem('mindease_user', JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem('mindease_token');
  localStorage.removeItem('mindease_user');
}

// If already logged in, skip to dashboard
(function checkAlreadyLoggedIn() {
  const token = localStorage.getItem('mindease_token');
  if (token) {
    window.location.replace('index.html');
  }
})();

// ── Panel Switching ─────────────────────────────────────────
window.switchToRegister = function () {
  const loginPanel    = document.getElementById('loginPanel');
  const registerPanel = document.getElementById('registerPanel');
  if (!loginPanel || !registerPanel) return;

  loginPanel.classList.add('hidden');
  registerPanel.classList.remove('hidden');

  // Re-trigger animation
  registerPanel.style.animation = 'none';
  void registerPanel.offsetWidth;
  registerPanel.style.animation = '';

  clearErrors('register');
};

window.switchToLogin = function () {
  const loginPanel    = document.getElementById('loginPanel');
  const registerPanel = document.getElementById('registerPanel');
  if (!loginPanel || !registerPanel) return;

  registerPanel.classList.add('hidden');
  loginPanel.classList.remove('hidden');

  loginPanel.style.animation = 'none';
  void loginPanel.offsetWidth;
  loginPanel.style.animation = '';

  clearErrors('login');
};

// ── Error Helpers ───────────────────────────────────────────
function showFieldError(id, msg) {
  const el = document.getElementById(id);
  if (el) el.textContent = msg;
  const inputId = id.replace('Error', '');
  const inp = document.getElementById(inputId);
  if (inp) inp.classList.add('error');
}

function clearFieldError(id) {
  const el = document.getElementById(id);
  if (el) el.textContent = '';
  const inputId = id.replace('Error', '');
  const inp = document.getElementById(inputId);
  if (inp) inp.classList.remove('error');
}

function showBanner(id, msg, isError = true) {
  const el = document.getElementById(id);
  if (!el) return;
  el.textContent = msg;
  el.classList.remove('hidden');
  if (isError) {
    el.classList.add('form-error-banner');
    el.classList.remove('form-success-banner');
  } else {
    el.classList.add('form-success-banner');
    el.classList.remove('form-error-banner');
  }
}

function hideBanner(id) {
  const el = document.getElementById(id);
  if (el) el.classList.add('hidden');
}

function clearErrors(prefix) {
  ['Name','Email','Password'].forEach(f => clearFieldError(`${prefix}${f}Error`));
  hideBanner(`${prefix}ErrorBanner`);
  if (prefix === 'register') hideBanner('registerSuccessBanner');
}

// ── Loading State ───────────────────────────────────────────
function setLoading(btnId, spinnerId, loading) {
  const btn     = document.getElementById(btnId);
  const spinner = document.getElementById(spinnerId);
  const text    = btn ? btn.querySelector('.auth-btn-text') : null;

  if (!btn) return;
  btn.disabled = loading;
  if (loading) {
    if (text)    text.style.display = 'none';
    if (spinner) spinner.classList.remove('hidden');
  } else {
    if (text)    text.style.display = '';
    if (spinner) spinner.classList.add('hidden');
  }
}

// ── Password Visibility Toggle ──────────────────────────────
window.togglePassword = function (inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    btn.textContent = '🙈';
  } else {
    input.type = 'password';
    btn.textContent = '👁';
  }
};

// ── Password Strength ───────────────────────────────────────
window.updatePasswordStrength = function (value) {
  const fill  = document.getElementById('strengthBarFill');
  const label = document.getElementById('strengthLabel');
  if (!fill || !label) return;

  let score = 0;
  if (value.length >= 8)             score++;
  if (/[A-Z]/.test(value))           score++;
  if (/[a-z]/.test(value))           score++;
  if (/[0-9]/.test(value))           score++;
  if (/[^A-Za-z0-9]/.test(value))   score++;

  fill.className = 'strength-bar-fill';

  if (value.length === 0) {
    fill.style.width = '0%';
    label.textContent = 'Enter a password';
    label.style.color = '';
    return;
  }

  const levels = [
    { cls: 'weak',   text: '⚠️ Too weak',   color: '#ef4444' },
    { cls: 'weak',   text: '⚠️ Too weak',   color: '#ef4444' },
    { cls: 'fair',   text: '👌 Fair',       color: '#f59e0b' },
    { cls: 'good',   text: '✅ Good',        color: '#3b82f6' },
    { cls: 'strong', text: '💪 Strong',     color: '#10b981' },
    { cls: 'strong', text: '💪 Very strong',color: '#10b981' },
  ];

  const lvl = levels[Math.min(score, 5)];
  fill.classList.add(lvl.cls);
  label.textContent  = lvl.text;
  label.style.color  = lvl.color;
};

// ── Client-side Validation ──────────────────────────────────
function validateEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function validatePassword(password) {
  const errors = [];
  if (password.length < 8)              errors.push('at least 8 characters');
  if (!/[A-Z]/.test(password))          errors.push('one uppercase letter');
  if (!/[a-z]/.test(password))          errors.push('one lowercase letter');
  if (!/[0-9]/.test(password))          errors.push('one digit');
  return errors;
}

// ── Login Handler ───────────────────────────────────────────
window.handleLogin = async function (e) {
  e.preventDefault();
  clearErrors('login');

  const email    = document.getElementById('loginEmail')?.value.trim() || '';
  const password = document.getElementById('loginPassword')?.value || '';

  let valid = true;

  if (!email) {
    showFieldError('loginEmailError', 'Email is required.'); valid = false;
  } else if (!validateEmail(email)) {
    showFieldError('loginEmailError', 'Please enter a valid email.'); valid = false;
  }

  if (!password) {
    showFieldError('loginPasswordError', 'Password is required.'); valid = false;
  }

  if (!valid) return;

  setLoading('loginBtn', 'loginSpinner', true);

  try {
    const res = await fetch(`${API_BASE_URL}/auth/login`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ email, password }),
    });

    const data = await res.json();

    if (!res.ok) {
      showBanner('loginErrorBanner', data.error || 'Login failed. Please try again.');
      return;
    }

    saveSession(data.access_token, data.user);

    // Smooth redirect
    document.getElementById('authCard').style.animation = 'none';
    document.getElementById('authCard').style.opacity   = '0';
    document.getElementById('authCard').style.transform = 'scale(0.95)';
    document.getElementById('authCard').style.transition = 'all 0.3s ease';

    setTimeout(() => { window.location.replace('index.html'); }, 300);

  } catch (err) {
    showBanner('loginErrorBanner', 'Cannot connect to server. Please make sure the backend is running.');
  } finally {
    setLoading('loginBtn', 'loginSpinner', false);
  }
};

// ── Register Handler ────────────────────────────────────────
window.handleRegister = async function (e) {
  e.preventDefault();
  clearErrors('register');

  const name     = document.getElementById('registerName')?.value.trim() || '';
  const email    = document.getElementById('registerEmail')?.value.trim() || '';
  const password = document.getElementById('registerPassword')?.value || '';

  let valid = true;

  if (!name) {
    showFieldError('registerNameError', 'Name is required.'); valid = false;
  } else if (name.length > 100) {
    showFieldError('registerNameError', 'Name must be 100 characters or fewer.'); valid = false;
  }

  if (!email) {
    showFieldError('registerEmailError', 'Email is required.'); valid = false;
  } else if (!validateEmail(email)) {
    showFieldError('registerEmailError', 'Please enter a valid email.'); valid = false;
  }

  const pwdErrors = validatePassword(password);
  if (!password) {
    showFieldError('registerPasswordError', 'Password is required.'); valid = false;
  } else if (pwdErrors.length > 0) {
    showFieldError('registerPasswordError', `Password needs: ${pwdErrors.join(', ')}.`); valid = false;
  }

  if (!valid) return;

  setLoading('registerBtn', 'registerSpinner', true);

  try {
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ name, email, password }),
    });

    const data = await res.json();

    if (res.status === 409) {
      showFieldError('registerEmailError', 'An account with this email already exists.');
      return;
    }

    if (!res.ok) {
      showBanner('registerErrorBanner', data.error || 'Registration failed. Please try again.');
      return;
    }

    // Success!
    showBanner('registerSuccessBanner', `🎉 Welcome, ${data.user?.name || 'friend'}! Signing you in…`, false);
    saveSession(data.access_token, data.user);

    setTimeout(() => { window.location.replace('index.html'); }, 1200);

  } catch (err) {
    showBanner('registerErrorBanner', 'Cannot connect to server. Please make sure the backend is running.');
  } finally {
    setLoading('registerBtn', 'registerSpinner', false);
  }
};

// ── Theme toggle wiring for auth page ──────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const toggleBtn = document.getElementById('authThemeToggle');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'dark';
      const next    = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('mindease_theme', next);
      toggleBtn.textContent = next === 'dark' ? '🌙' : '☀️';
    });

    // Apply saved theme
    const saved = localStorage.getItem('mindease_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    toggleBtn.textContent = saved === 'dark' ? '🌙' : '☀️';
  }
});
