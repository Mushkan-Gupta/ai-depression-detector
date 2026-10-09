// ── Common Peer Functions (Auth & Helpers) ────────────────────────────────

const PEER_API_BASE = '/peer';

function getAuthToken() {
  const token = localStorage.getItem('mindease_token');
  if (!token) {
    window.location.href = 'auth.html';
  }
  return token;
}

// Global fetch wrapper for peer routes to handle 401s
async function peerFetch(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json',
    ...(options.headers || {})
  };

  const response = await fetch(`${PEER_API_BASE}${endpoint}`, { ...options, headers });
  
  if (response.status === 401) {
    if (typeof logout === 'function') logout();
    else {
      localStorage.removeItem('mindease_token');
      localStorage.removeItem('mindease_user');
      window.location.href = 'auth.html';
    }
  }
  return response;
}

// Defensive fallback for null/undefined display names
function _safeName(name) {
  return (name && name !== 'undefined' && name !== 'null') ? name : 'Anonymous';
}

// Indian Standard Time (IST, UTC+5:30) Formatters
function formatISTDate(dateInput, options = {}) {
  if (!dateInput) return '';
  const d = (dateInput instanceof Date) ? dateInput : new Date(dateInput);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleDateString('en-IN', { timeZone: 'Asia/Kolkata', ...options });
}

function formatISTTime(dateInput, options = {}) {
  if (!dateInput) return '';
  const d = (dateInput instanceof Date) ? dateInput : new Date(dateInput);
  if (isNaN(d.getTime())) return '';
  return d.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: true, ...options });
}

