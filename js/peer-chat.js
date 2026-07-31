let currentConversationId = null;
let currentUserId = null;
let highestMessageId = null;
let pollInterval = null;
let isConversationActive = true;
let otherParticipantName = "Peer"; // Default fallback

// DOM Elements
const chatView = document.getElementById('chatView');
const errorView = document.getElementById('errorView');
const chatPeerName = document.getElementById('chatPeerName');
const chatStatusBadge = document.getElementById('chatStatusBadge');
const crisisGuidanceContainer = document.getElementById('crisisGuidanceContainer');
const peerNoticeContainer = document.getElementById('peerNoticeContainer');
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const chatDisabledBanner = document.getElementById('chatDisabledBanner');

// ── Initialization ──────────────────────────────────────────────────────────
async function initChat() {
  const token = getAuthToken();
  if (!token) return;

  const urlParams = new URLSearchParams(window.location.search);
  currentConversationId = urlParams.get('conv');

  if (!currentConversationId) {
    showError("Invalid Link", "No conversation ID provided.");
    return;
  }

  const userStr = localStorage.getItem('mindease_user');
  if (userStr) {
    try {
      const user = JSON.parse(userStr);
      currentUserId = user.id;
      const name = user.name || 'User';
      const initials = name.substring(0, 2).toUpperCase();
      document.getElementById('userInitials').textContent = initials;
      document.getElementById('dropdownName').textContent = name;
      document.getElementById('dropdownEmail').textContent = user.email || '';
    } catch (e) {
      console.error("Error parsing user:", e);
    }
  }

  // Load the conversation list to find the other participant's name
  try {
    const convRes = await peerFetch('/conversations');
    if (convRes.ok) {
      const convData = await convRes.json();
      const match = (convData.conversations || []).find(c => c.id === currentConversationId);
      if (match) {
        otherParticipantName = _safeName(match.other_participant_name);
        chatPeerName.textContent = otherParticipantName;
      }
    }
  } catch (e) {
    console.warn("Could not fetch conversation list for name", e);
  }

  // Initial load
  await fetchMessages();

  // Polling
  pollInterval = setInterval(() => {
    if (isConversationActive) {
      fetchMessages(true);
    }
  }, 5000);

  // Event Listeners
  sendButton.addEventListener('click', sendMessage);
  messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
}

// ── UI Helpers ──────────────────────────────────────────────────────────────
function showError(title, msg) {
  chatView.style.display = 'none';
  errorView.style.display = 'block';
  document.getElementById('errorTitle').textContent = title;
  document.getElementById('errorMsg').textContent = msg;
}

function updateStatusUI(status) {
  chatStatusBadge.textContent = status.charAt(0).toUpperCase() + status.slice(1);
  chatStatusBadge.className = 'status-badge';
  
  if (status === 'active' || status === 'suspended') {
    if (status === 'active') chatStatusBadge.classList.add('status-active');
    if (status === 'suspended') chatStatusBadge.classList.add('status-suspended');
    
    isConversationActive = true;
    messageInput.disabled = false;
    sendButton.disabled = false;
    chatDisabledBanner.style.display = 'none';
  } else {
    chatStatusBadge.classList.add('status-closed');
    
    isConversationActive = false;
    messageInput.disabled = true;
    sendButton.disabled = true;
    chatDisabledBanner.style.display = 'block';
    
    // Stop polling since it's no longer active
    if (pollInterval) {
      clearInterval(pollInterval);
      pollInterval = null;
    }
  }
}

function renderCrisisGuidance(cg) {
  if (!cg) {
    crisisGuidanceContainer.innerHTML = '';
    return;
  }
  crisisGuidanceContainer.innerHTML = `
    <div class="crisis-banner">
      <h3>Priority Support</h3>
      <p style="font-weight:500;">${cg.summary}</p>
      <p>${cg.guidance}</p>
      <ul class="crisis-resources">
        ${(cg.resources || []).map(r => `<li>${r}</li>`).join('')}
      </ul>
    </div>
  `;
}

function renderPeerNotice(noticeMsg) {
  if (!noticeMsg) {
    if (peerNoticeContainer) peerNoticeContainer.innerHTML = '';
    return;
  }
  if (peerNoticeContainer) {
    peerNoticeContainer.innerHTML = `
      <div class="peer-notice-banner" style="background: #e0f2fe; border-left: 4px solid #0284c7; padding: 0.75rem 1.5rem; margin: 1rem 1.5rem; border-radius: 0 var(--radius-md) var(--radius-md) 0; color: #0369a1; font-size: 0.9rem;">
        <i class="fa-solid fa-circle-info" style="margin-right: 0.5rem;"></i>
        ${noticeMsg}
      </div>
    `;
  }
}

function appendMessage(msgData, isOptimistic = false) {
  // Dedupe
  if (!isOptimistic && document.getElementById(`msg-${msgData.id}`)) return;

  const isSentByMe = msgData.sender_id === currentUserId;
  const wrapper = document.createElement('div');
  wrapper.className = `message-wrapper ${isSentByMe ? 'sent' : 'received'}`;
  
  if (msgData.id) {
    wrapper.id = `msg-${msgData.id}`;
  } else if (msgData.tempId) {
    wrapper.id = `msg-${msgData.tempId}`;
  }

  const timeStr = msgData.created_at ? new Date(msgData.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'Just now';
  
  const bubbleClass = `message-bubble ${isOptimistic ? 'sending' : ''}`;
  
  // Basic escaping
  const escapedContent = msgData.content.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  
  wrapper.innerHTML = `
    <div class="${bubbleClass}">
      ${escapedContent.replace(/\n/g, '<br/>')}
    </div>
    <div class="message-meta">
      <span>${timeStr}</span>
      ${isOptimistic ? '<span class="status-indicator"><i class="fa-solid fa-clock"></i></span>' : ''}
    </div>
  `;
  
  chatMessages.appendChild(wrapper);
  scrollToBottom();
}

function scrollToBottom() {
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ── API Interactions ────────────────────────────────────────────────────────
async function fetchMessages(isPoll = false) {
  let url = `/conversations/${currentConversationId}/messages`;
  if (isPoll && highestMessageId) {
    url += `?since_id=${highestMessageId}`;
  }

  try {
    const res = await peerFetch(url);
    if (!res.ok) {
      if (!isPoll) {
        if (res.status === 404) showError("Not Found", "Conversation does not exist.");
        else if (res.status === 403) showError("Forbidden", "You don't have access to this conversation.");
        else showError("Error", "Could not load messages.");
      }
      return;
    }

    const data = await res.json();
    
    // Show UI on first successful load
    if (!isPoll) {
      chatView.style.display = 'block';
    }

    if (data.crisis_guidance) {
      renderCrisisGuidance(data.crisis_guidance);
    } else {
      renderCrisisGuidance(null); // Clear if no longer high risk
    }
    
    if (data.peer_notice) {
      renderPeerNotice(data.peer_notice);
    } else {
      renderPeerNotice(null);
    }

    if (data.conversation_status) {
      updateStatusUI(data.conversation_status);
    }

    const msgs = data.messages || [];
    msgs.forEach(msg => {
      appendMessage(msg);
      // Track highest ID for polling (MongoDB ObjectIds sort alphabetically)
      if (!highestMessageId || msg.id > highestMessageId) {
        highestMessageId = msg.id;
      }
    });
  } catch (e) {
    console.error("Fetch messages error:", e);
  }
}

async function sendMessage() {
  const content = messageInput.value.trim();
  if (!content || !isConversationActive) return;

  // Optimistic UI update
  messageInput.value = '';
  messageInput.style.height = '';
  const tempId = 'temp-' + Date.now();
  
  appendMessage({
    tempId: tempId,
    sender_id: currentUserId,
    content: content,
    created_at: null
  }, true);

  const wrapper = document.getElementById(`msg-${tempId}`);
  const bubble = wrapper.querySelector('.message-bubble');
  const indicator = wrapper.querySelector('.status-indicator');

  try {
    const res = await peerFetch(`/conversations/${currentConversationId}/messages`, {
      method: 'POST',
      body: JSON.stringify({ content: content })
    });
    
    const data = await res.json();
    
    if (res.ok) {
      // Success! Update optimistic message to actual message
      wrapper.id = `msg-${data.msg._id}`;
      bubble.classList.remove('sending');
      if (indicator) indicator.innerHTML = '<i class="fa-solid fa-check"></i>';
      
      if (!highestMessageId || data.msg._id > highestMessageId) {
        highestMessageId = data.msg._id;
      }
      
      // Persistent banner for sender if escalated
      if (data.crisis_guidance) {
        renderCrisisGuidance(data.crisis_guidance);
        
        // Also keep the inline nudge
        const nudge = document.createElement('div');
        nudge.className = 'inline-crisis-nudge';
        nudge.textContent = data.crisis_guidance.summary || 'Please consider reaching out for support.';
        wrapper.appendChild(nudge);
        scrollToBottom();
      } else {
        renderCrisisGuidance(null);
      }
      
      if (data.peer_notice) {
        renderPeerNotice(data.peer_notice);
      } else {
        renderPeerNotice(null);
      }
      
      // Update status if it changed
      if (data.conversation_status) updateStatusUI(data.conversation_status);

    } else {
      // Generic failure
      bubble.classList.remove('sending');
      bubble.classList.add('failed');
      if (indicator) indicator.innerHTML = '<i class="fa-solid fa-circle-exclamation" style="color:#ef4444"></i>';
      
      const errTxt = document.createElement('div');
      errTxt.style.color = '#ef4444';
      errTxt.style.fontSize = '0.75rem';
      errTxt.style.marginTop = '0.25rem';
      errTxt.textContent = data.error || data.message || 'Failed to send';
      wrapper.appendChild(errTxt);
      scrollToBottom();
    }
  } catch (e) {
    console.error("Send message error:", e);
    bubble.classList.remove('sending');
    bubble.classList.add('failed');
    if (indicator) indicator.innerHTML = '<i class="fa-solid fa-circle-exclamation" style="color:#ef4444"></i>';
  }
}

// ── Boot ────────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', initChat);
