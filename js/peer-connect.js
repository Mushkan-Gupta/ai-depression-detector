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

// ── Initialization ──────────────────────────────────────────────────────────
async function initPeerConnect() {
  const token = getAuthToken();
  if (!token) return;

  // Render user info in header (reusing dashboard logic if available, else manual)
  const userStr = localStorage.getItem('mindease_user');
  if (userStr) {
    try {
      const user = JSON.parse(userStr);
      const name = user.peer_display_name || 'Anonymous User';
      const initials = name.replace("Anonymous ", "").substring(0, 1).toUpperCase();
      document.getElementById('userInitials').textContent = initials;
      document.getElementById('dropdownName').textContent = name;
      const emailEl = document.getElementById('dropdownEmail');
      if (emailEl) emailEl.remove();
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
  // Each section is wrapped independently so a failure in one
  // does NOT prevent the others (or the opt-in button) from working.

  try {
    await loadCandidates(); // Also infers opt-in status & checks high-risk
    if (mainPeerDashboard.classList.contains('hidden')) return; // crisis block applied
  } catch (e) {
    console.error('[peer-connect] loadCandidates failed:', e);
    if (candidatesList) {
      candidatesList.innerHTML = '<p style="color:var(--text-secondary)">Could not load candidates. Try refreshing.</p>';
    }
  }

  try {
    await loadRequests();
  } catch (e) {
    console.error('[peer-connect] loadRequests failed:', e);
  }

  try {
    await loadConversations();
  } catch (e) {
    console.error('[peer-connect] loadConversations failed:', e);
  }
}

async function loadCandidates() {
  const res = await peerFetch('/candidates');
  // Guard: non-JSON body (e.g. 500 HTML) would throw — surface it cleanly
  let data;
  try {
    data = await res.json();
  } catch (e) {
    console.error('[peer-connect] /candidates returned non-JSON (status', res.status, ')');
    throw new Error(`/peer/candidates HTTP ${res.status}`);
  }

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

// ── FIX 3: sendRequest — no alert(), patch card in-place ───────────────────
async function sendRequest(candidateId) {
  // Find this candidate's card and button by data attribute set at render time
  const card = document.querySelector(`.candidate-card[data-candidate-id="${candidateId}"]`);
  const btn = card ? card.querySelector('.accept-btn') : null;

  // Clear any previous inline error on this card
  if (card) {
    const prev = card.querySelector('.inline-error');
    if (prev) prev.remove();
  }

  const res = await peerFetch('/requests', {
    method: 'POST',
    body: JSON.stringify({ receiver_id: candidateId })
  });

  if (res.ok) {
    // Patch the button in-place — no full page reload
    if (btn) {
      btn.disabled = true;
      btn.textContent = 'Request Sent';
      btn.style.opacity = '0.6';
      btn.style.cursor = 'default';
    }
  } else {
    const data = await res.json();
    const msg = data.reason || data.error || data.message || 'Error sending request';
    // Render error inline below the button
    if (card) {
      const errEl = document.createElement('p');
      errEl.className = 'inline-error';
      errEl.style.cssText = 'color:#ef4444;font-size:0.8rem;margin:0.4rem 0 0 0;';
      errEl.textContent = msg;
      card.appendChild(errEl);
    }
  }
}

// ── FIX 1 + 4: handleRequest — corrected error codes, inline errors ─────────
async function handleRequest(requestId, action) {
  const res = await peerFetch(`/requests/${requestId}/${action}`, { method: 'POST' });
  const data = await res.json();

  // ── FIX 1a: correct error code for risk escalation (was 'not_eligible_high_risk')
  if (res.status === 409 && data.error === 'request_declined_risk_escalation') {
    if (data.crisis_guidance) {
      renderCrisisGuidance(data.crisis_guidance);
      mainPeerDashboard.classList.add('hidden');
    } else {
      // Sender escalated (not the receiver) — show inline on the card
      _showInlineRequestError(requestId, data.message || 'Request declined due to risk escalation.');
    }
    return;
  }

  // ── FIX 1b: explicit 410 expired handling
  if (res.status === 410 && data.error === 'request_expired') {
    _showInlineRequestError(requestId, 'This request has expired and can no longer be accepted.');
    // Also remove the action buttons so the user isn't confused
    const card = document.querySelector(`.request-card[data-request-id="${requestId}"]`);
    if (card) {
      const btnGroup = card.querySelector('.btn-group');
      if (btnGroup) btnGroup.remove();
    }
    return;
  }

  if (res.ok) {
    loadDashboardData();
    if (action === 'accept') {
      window.location.href = `peer-chat.html?conv=${data.conversation_id}`;
    }
  } else {
    // ── FIX 4: no fallback alert() — show inline near the request card
    const msg = data.error || data.message || 'Action failed';
    _showInlineRequestError(requestId, msg);
  }
}

// Helper: show inline error text under a specific request card
function _showInlineRequestError(requestId, msg) {
  const card = document.querySelector(`.request-card[data-request-id="${requestId}"]`);
  if (!card) return;
  // Remove any existing inline error first
  const prev = card.querySelector('.inline-error');
  if (prev) prev.remove();
  const errEl = document.createElement('p');
  errEl.className = 'inline-error';
  errEl.style.cssText = 'color:#ef4444;font-size:0.8rem;margin:0.4rem 0 0 0;width:100%;';
  errEl.textContent = msg;
  card.appendChild(errEl);
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
    <div class="candidate-card" data-candidate-id="${c.candidate_id}">
      <div class="candidate-info">
        <h4>${_safeName(c.peer_display_name)}</h4>
        <p style="font-size: 0.85rem; color: var(--text-secondary); margin: 0.2rem 0 0.5rem 0;">
          ${Math.round(c.match_fraction * 100)}% match
        </p>
        <div class="theme-tags">
          ${(c.overlapping_themes || []).map(t => `<span class="theme-tag">${t}</span>`).join('')}
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
    <div class="request-card" data-request-id="${r.id}">
      <div class="candidate-info">
        <h4>${_safeName(r.other_participant_name)}</h4>
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
    <div class="request-card" data-request-id="${r.id}">
      <div class="candidate-info">
        <h4>${_safeName(r.other_participant_name)}</h4>
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
        <h4>${_safeName(c.other_participant_name)}</h4>
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
