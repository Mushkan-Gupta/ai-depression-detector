const PEER_API_BASE = 'http://127.0.0.1:5000/peer';

// DOM Elements
const consentSection = document.getElementById('consentSection');
const mainPeerDashboard = document.getElementById('mainPeerDashboard');
const crisisGuidanceContainer = document.getElementById('crisisGuidanceContainer');
const optInWrapper = document.getElementById('optInWrapper');
const toggleMatchBtn = document.getElementById('toggleMatchBtn');
const optInStatusText = document.getElementById('optInStatusText');
const candidatesList = document.getElementById('candidatesList');
const incomingRequestsList = document.getElementById('incomingRequestsList');
const sentRequestsList = document.getElementById('sentRequestsList');
const conversationsList = document.getElementById('conversationsList');

let isOptedIn = false;

// ── Auth Guard ──────────────────────────────────────────────────────────────
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

// ── Initialization ──────────────────────────────────────────────────────────
async function initPeerConnect() {
  const token = getAuthToken();
  if (!token) return;

  // Render user info in header (reusing dashboard logic if available, else manual)
  const userStr = localStorage.getItem('mindease_user');
  if (userStr) {
    try {
      const user = JSON.parse(userStr);
      const name = user.name || 'User';
      const initials = name.substring(0, 2).toUpperCase();
      document.getElementById('userInitials').textContent = initials;
      document.getElementById('dropdownName').textContent = name;
      document.getElementById('dropdownEmail').textContent = user.email || '';
    } catch (e) {
      console.error("Error parsing user:", e);
    }
  }

  // 1. Check Consent via Conversations Endpoint (since it requires consent)
  const convRes = await peerFetch('/conversations');
  if (convRes.status === 403) {
    const data = await convRes.json();
    if (data.error === 'peer_consent_required') {
      consentSection.classList.remove('hidden');
      return; // Stop here until consented
    }
  }

  // Consented, load main dashboard
  consentSection.classList.add('hidden');
  mainPeerDashboard.classList.remove('hidden');

  await loadDashboardData();
}

// ── Dashboard Data Loaders ──────────────────────────────────────────────────
async function loadDashboardData() {
  await loadCandidates(); // Also infers opt-in status & checks high-risk
  if (mainPeerDashboard.classList.contains('hidden')) return; // Abort if risk block applied
  
  await loadRequests();
  await loadConversations();
}

async function loadCandidates() {
  const res = await peerFetch('/candidates');
  const data = await res.json();

  if (res.status === 403 && data.error === 'not_eligible_high_risk') {
    renderCrisisGuidance(data.crisis_guidance);
    mainPeerDashboard.classList.add('hidden'); // Hide the whole dashboard
    return;
  }

  if (res.status === 400 && data.error === 'not_opted_in') {
    isOptedIn = false;
    updateOptInUI();
    candidatesList.innerHTML = '<p style="color:var(--text-secondary)">Opt in to see matching candidates.</p>';
    return;
  }

  if (res.status === 200) {
    isOptedIn = true;
    updateOptInUI();
    renderCandidates(data.candidates || []);
  }
}

async function loadRequests() {
  // Incoming
  const incRes = await peerFetch('/requests?type=incoming');
  const incData = await incRes.json();
  if (incRes.status === 200) {
    if (incData.crisis_guidance) renderCrisisGuidance(incData.crisis_guidance);
    renderIncomingRequests(incData.requests || []);
  }

  // Sent
  const sentRes = await peerFetch('/requests?type=sent');
  const sentData = await sentRes.json();
  if (sentRes.status === 200) {
    if (sentData.crisis_guidance && !incData.crisis_guidance) renderCrisisGuidance(sentData.crisis_guidance);
    renderSentRequests(sentData.requests || []);
  }
}

async function loadConversations() {
  const res = await peerFetch('/conversations');
  const data = await res.json();
  if (res.status === 200) {
    renderConversations(data.conversations || []);
  }
}

// ── UI Actions ──────────────────────────────────────────────────────────────
async function agreeConsent() {
  const res = await peerFetch('/consent', { method: 'POST' });
  if (res.ok) {
    consentSection.classList.add('hidden');
    mainPeerDashboard.classList.remove('hidden');
    loadDashboardData();
  } else {
    alert("Error saving consent.");
  }
}

async function toggleMatching() {
  const endpoint = isOptedIn ? '/opt-out' : '/opt-in';
  const res = await peerFetch(endpoint, { method: 'POST' });
  const data = await res.json();
  
  if (res.status === 403 && data.error === 'not_eligible_high_risk') {
    renderCrisisGuidance(data.crisis_guidance);
    mainPeerDashboard.classList.add('hidden');
    return;
  }

  if (res.ok) {
    isOptedIn = !isOptedIn;
    updateOptInUI();
    loadDashboardData(); // Reload candidates
  }
}

async function sendRequest(candidateId) {
  const res = await peerFetch('/requests', {
    method: 'POST',
    body: JSON.stringify({ receiver_id: candidateId })
  });
  if (res.ok) {
    alert("Request sent!");
    loadDashboardData();
  } else {
    const data = await res.json();
    alert(data.error || data.message || "Error sending request");
  }
}

async function handleRequest(requestId, action) {
  const res = await peerFetch(`/requests/${requestId}/${action}`, { method: 'POST' });
  const data = await res.json();
  
  if (res.status === 409 && data.error === 'not_eligible_high_risk' && data.crisis_guidance) {
    renderCrisisGuidance(data.crisis_guidance);
    mainPeerDashboard.classList.add('hidden');
    return;
  }

  if (res.ok) {
    loadDashboardData();
    if (action === 'accept') {
      window.location.href = `peer-chat.html?conv=${data.conversation_id}`;
    }
  } else {
    alert(data.error || "Action failed");
  }
}

// ── Render Helpers ──────────────────────────────────────────────────────────
function updateOptInUI() {
  if (isOptedIn) {
    toggleMatchBtn.textContent = 'Opt Out';
    toggleMatchBtn.classList.add('opt-out-btn');
    optInStatusText.textContent = 'You are currently opted in to peer matching.';
  } else {
    toggleMatchBtn.textContent = 'Opt In to Match';
    toggleMatchBtn.classList.remove('opt-out-btn');
    optInStatusText.textContent = 'You are currently opted out.';
  }
}

function renderCandidates(candidates) {
  if (candidates.length === 0) {
    candidatesList.innerHTML = '<p style="color:var(--text-secondary)">No candidates available right now. Check back later!</p>';
    return;
  }

  candidatesList.innerHTML = candidates.map(c => `
    <div class="candidate-card">
      <div class="candidate-info">
        <h4>${c.peer_display_name}</h4>
        <div class="theme-tags">
          ${c.overlapping_themes.map(t => `<span class="theme-tag">${t}</span>`).join('')}
        </div>
      </div>
      <button class="accept-btn" onclick="sendRequest('${c.candidate_id}')">Send Request</button>
    </div>
  `).join('');
}

function renderIncomingRequests(requests) {
  const pending = requests.filter(r => r.status === 'pending');
  if (pending.length === 0) {
    incomingRequestsList.innerHTML = '<p style="color:var(--text-secondary); font-size:0.9rem;">No incoming requests.</p>';
    return;
  }
  
  incomingRequestsList.innerHTML = pending.map(r => `
    <div class="request-card">
      <div class="candidate-info">
        <h4>${r.other_participant_name}</h4>
        <span style="font-size:0.8rem; color:var(--text-secondary);">Sent ${new Date(r.created_at).toLocaleDateString()}</span>
      </div>
      <div class="btn-group">
        <button class="accept-btn" onclick="handleRequest('${r.id}', 'accept')">Accept</button>
        <button class="decline-btn" onclick="handleRequest('${r.id}', 'decline')">Decline</button>
      </div>
    </div>
  `).join('');
}

function renderSentRequests(requests) {
  const pending = requests.filter(r => r.status === 'pending');
  if (pending.length === 0) {
    sentRequestsList.innerHTML = '<p style="color:var(--text-secondary); font-size:0.9rem;">No sent requests.</p>';
    return;
  }

  sentRequestsList.innerHTML = pending.map(r => `
    <div class="request-card">
      <div class="candidate-info">
        <h4>${r.other_participant_name}</h4>
        <span style="font-size:0.8rem; color:var(--text-secondary);">Sent ${new Date(r.created_at).toLocaleDateString()}</span>
      </div>
      <span style="color:var(--text-secondary); font-size:0.9rem;">Pending</span>
    </div>
  `).join('');
}

function renderConversations(conversations) {
  if (conversations.length === 0) {
    conversationsList.innerHTML = '<p style="color:var(--text-secondary)">No active conversations.</p>';
    return;
  }

  conversationsList.innerHTML = conversations.map(c => `
    <div class="conversation-card" style="cursor:pointer;" onclick="window.location.href='peer-chat.html?conv=${c.id}'">
      <div class="candidate-info">
        <h4>${c.other_participant_name}</h4>
        <span style="font-size:0.8rem; color:var(--text-secondary);">Status: ${c.status}</span>
      </div>
      <span style="color:var(--text-secondary);">Chat &rarr;</span>
    </div>
  `).join('');
}

function renderCrisisGuidance(cg) {
  if (!cg) return;
  crisisGuidanceContainer.innerHTML = `
    <div class="crisis-banner">
      <h3>Priority Support</h3>
      <p style="font-weight:500;">${cg.summary}</p>
      <p>${cg.guidance}</p>
      <ul class="crisis-resources">
        ${cg.resources.map(r => `<li>${r}</li>`).join('')}
      </ul>
    </div>
  `;
}

// ── Boot ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', initPeerConnect);
