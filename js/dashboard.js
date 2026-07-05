/* ============================================================
   dashboard.js — MindEase Dashboard Logic
   User profile, journal history, logout, panel controls
   ============================================================ */

const API_BASE_URL = 'http://127.0.0.1:5000';

// ── Auth Guard ──────────────────────────────────────────────
// Called when the user clicks "Open Your Journal" (CTA)
// or when we need to enforce a login gate
function getToken() {
  return localStorage.getItem('mindease_token');
}

function getUser() {
  try {
    return JSON.parse(localStorage.getItem('mindease_user') || 'null');
  } catch { return null; }
}

// ── Logout ──────────────────────────────────────────────────
window.logout = async function () {
  const token = localStorage.getItem('mindease_token');

  // Notify the server (best-effort — don't block redirect on failure)
  if (token) {
    try {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method:  'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
    } catch { /* backend offline — proceed with local logout */ }
  }

  localStorage.removeItem('mindease_token');
  localStorage.removeItem('mindease_user');
  window.location.href = 'auth.html';
};

// ── User Menu ───────────────────────────────────────────────
window.toggleUserMenu = function () {
  const dropdown = document.getElementById('userDropdown');
  if (!dropdown) return;
  dropdown.classList.toggle('hidden');
};

// Close dropdown when clicking outside
document.addEventListener('click', (e) => {
  const wrapper  = document.getElementById('userMenuWrapper');
  const dropdown = document.getElementById('userDropdown');
  if (wrapper && dropdown && !wrapper.contains(e.target)) {
    dropdown.classList.add('hidden');
  }
});

// ── Populate User Profile in Header ─────────────────────────
function populateUserHeader(user) {
  if (!user) return;

  const initials = (user.name || '?')
    .split(' ')
    .map(w => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase();

  const initialsEl = document.getElementById('userInitials');
  const nameEl     = document.getElementById('dropdownName');
  const emailEl    = document.getElementById('dropdownEmail');

  if (nameEl)  nameEl.textContent  = user.name  || '—';
  if (emailEl) emailEl.textContent = user.email || '—';

  // Show Google profile photo if available; fall back to initials
  if (initialsEl) {
    if (user.picture) {
      // Replace text initials with a circular <img>
      initialsEl.innerHTML = '';
      const img = document.createElement('img');
      img.src    = user.picture;
      img.alt    = user.name || 'Profile';
      img.style.cssText = 'width:100%;height:100%;border-radius:50%;object-fit:cover;';
      img.onerror = () => { initialsEl.innerHTML = initials; };  // fallback if URL breaks
      initialsEl.appendChild(img);
    } else {
      initialsEl.textContent = initials;
    }
  }
}

// ── History Panel ───────────────────────────────────────────
window.historyPanelOpen = false;

window.toggleHistoryPanel = function () {
  const panel   = document.getElementById('historyPanel');
  const overlay = document.getElementById('historyOverlay');
  if (!panel) return;

  window.historyPanelOpen = !window.historyPanelOpen;

  if (window.historyPanelOpen) {
    panel.classList.add('open');
    overlay.classList.remove('hidden');
    loadHistory();
  } else {
    panel.classList.remove('open');
    overlay.classList.add('hidden');
  }
};

// ── Load History from API ───────────────────────────────────
window.loadHistory = async function () {
  const token = getToken();
  if (!token) return;

  const listEl    = document.getElementById('historyList');
  const emptyEl   = document.getElementById('historyEmpty');
  const loadingEl = document.getElementById('historyLoading');

  if (!listEl) return;

  // Show loading
  if (emptyEl)   emptyEl.classList.add('hidden');
  if (listEl)    listEl.classList.add('hidden');
  if (loadingEl) loadingEl.classList.remove('hidden');

  try {
    const res = await fetch(`${API_BASE_URL}/history?page_size=20`, {
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type':  'application/json',
      },
    });

    if (res.status === 401) {
      // Token expired — redirect to login
      logout();
      return;
    }

    if (!res.ok) throw new Error('Failed to load history');

    const data = await res.json();
    renderHistory(data.entries || []);

  } catch (err) {
    console.warn('[History] Error:', err.message);
    if (emptyEl) {
      emptyEl.classList.remove('hidden');
      const p = emptyEl.querySelector('p');
      if (p) p.textContent = 'Could not load history. Is the backend running?';
    }
  } finally {
    if (loadingEl) loadingEl.classList.add('hidden');
  }
};

// ── Render History Entries ──────────────────────────────────
function renderHistory(entries) {
  const listEl  = document.getElementById('historyList');
  const emptyEl = document.getElementById('historyEmpty');

  if (!listEl) return;

  if (!entries || entries.length === 0) {
    listEl.classList.add('hidden');
    if (emptyEl) {
      emptyEl.classList.remove('hidden');
      const p = emptyEl.querySelector('p');
      if (p) p.textContent = 'Your saved journals will appear here after analysis.';
    }
    return;
  }

  if (emptyEl) emptyEl.classList.add('hidden');
  listEl.classList.remove('hidden');

  listEl.innerHTML = entries.map((entry, idx) => {
    const risk       = (entry.risk || 'Low').toLowerCase();
    const riskLabel  = entry.risk || 'Low';
    const conf       = entry.confidence != null
      ? `${Math.round(entry.confidence * 100)}% confidence`
      : '';
    const preview    = (entry.journal || '').slice(0, 120).trim();
    const date       = formatDate(entry.created_at);
    const entryId    = entry.id;

    return `
      <div class="history-entry-card" style="animation-delay:${idx * 0.05}s" data-id="${entryId}">
        <div class="history-entry-top">
          <span class="history-risk-badge ${risk}">${riskLabel}</span>
          <span class="history-entry-date">${date}</span>
        </div>
        <div class="history-entry-preview">${escapeHtml(preview)}${preview.length >= 120 ? '…' : ''}</div>
        <div class="history-entry-footer">
          <span class="history-confidence">${conf}</span>
          <button class="history-delete-btn" onclick="deleteEntry('${entryId}')" title="Delete entry">🗑 Delete</button>
        </div>
      </div>
    `;
  }).join('');
}

// ── Delete Entry ────────────────────────────────────────────
window.deleteEntry = async function (entryId) {
  const token = getToken();
  if (!token || !entryId) return;

  // Optimistic UI: fade out card
  const card = document.querySelector(`[data-id="${entryId}"]`);
  if (card) {
    card.style.transition = 'opacity 0.3s, transform 0.3s';
    card.style.opacity    = '0.4';
    card.style.transform  = 'translateX(-10px)';
  }

  try {
    const res = await fetch(`${API_BASE_URL}/history/${entryId}`, {
      method:  'DELETE',
      headers: { 'Authorization': `Bearer ${token}` },
    });

    if (res.status === 401) { logout(); return; }

    if (res.ok) {
      if (card) card.remove();
      // Check if list is now empty
      const listEl = document.getElementById('historyList');
      if (listEl && listEl.children.length === 0) {
        listEl.classList.add('hidden');
        const emptyEl = document.getElementById('historyEmpty');
        if (emptyEl) emptyEl.classList.remove('hidden');
      }
    } else {
      // Undo optimistic UI
      if (card) { card.style.opacity = '1'; card.style.transform = ''; }
    }
  } catch {
    if (card) { card.style.opacity = '1'; card.style.transform = ''; }
  }
};

// ── Helpers ─────────────────────────────────────────────────
function formatDate(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    const now = new Date();
    const diffMs = now - d;
    const diffH  = diffMs / 3600000;
    const diffD  = diffMs / 86400000;

    if (diffH < 1)  return 'Just now';
    if (diffH < 24) return `${Math.floor(diffH)}h ago`;
    if (diffD < 7)  return `${Math.floor(diffD)}d ago`;

    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch { return '—'; }
}

function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Dashboard Init ──────────────────────────────────────────
// Called from analyze.js when landing CTA is clicked
window.initDashboard = function () {
  const token = getToken();
  const user  = getUser();

  if (token && user) {
    populateUserHeader(user);
  }

  // Verify token is still valid in the background
  if (token) {
    fetch(`${API_BASE_URL}/auth/me`, {
      headers: { 'Authorization': `Bearer ${token}` },
    }).then(res => {
      if (res.status === 401) {
        logout();
      } else if (res.ok) {
        res.json().then(data => {
          if (data.user) {
            localStorage.setItem('mindease_user', JSON.stringify(data.user));
            populateUserHeader(data.user);
          }
        });
      }
    }).catch(() => { /* backend offline — allow offline use */ });
  }
};

// ── Auto-init: if the user already has a session when index.html loads ──────
// This handles the case where someone navigates directly to index.html
// with a stored token (e.g. after a page refresh or a back-navigation).
document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('mindease_token');
  const user  = getUser();
  if (token && user) {
    // Populate the header immediately from cached data
    populateUserHeader(user);
  }
});
