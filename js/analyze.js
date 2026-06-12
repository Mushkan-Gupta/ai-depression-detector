// API_BASE_URL is declared in dashboard.js (loaded before this file)
// const API_BASE_URL = 'http://127.0.0.1:5000';  ← defined in dashboard.js

// ── Landing Page CTA ──────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  // Wire the Enter button on landing page
  const enterBtn = document.getElementById("enterBtn");
  if (enterBtn) {
    enterBtn.addEventListener("click", () => {
      // Always go to auth; auth.html redirects back if already logged in
      const token = localStorage.getItem('mindease_token');
      if (token) {
        showDashboard();
      } else {
        window.location.href = 'auth.html';
      }
    });
  }

  // If landed here with a token in URL hash (post-auth redirect), go straight to dashboard
  const token = localStorage.getItem('mindease_token');
  if (token && window.location.hash === '#dashboard') {
    showDashboard();
  }

  // Word counter update
  const journalInput = document.getElementById("journalInput");
  const charCount    = document.getElementById("charCount");
  if (journalInput && charCount) {
    journalInput.addEventListener("input", () => {
      const words = journalInput.value.trim().split(/\s+/).filter(w => w.length > 0);
      charCount.textContent = words.length === 0 ? "0 words" : `${words.length} word${words.length !== 1 ? "s" : ""}`;
    });
  }
});

// ── Show Dashboard ─────────────────────────────────────────
function showDashboard() {
  const landing   = document.getElementById("landingPage");
  const dashboard = document.getElementById("appDashboard");
  if (landing)   landing.classList.add("hidden");
  if (dashboard) dashboard.classList.remove("hidden");
  // Init dashboard (user profile, etc.)
  if (typeof window.initDashboard === 'function') {
    window.initDashboard();
  }
}

// ── Clear Journal ──────────────────────────────────────
window.clearJournal = function () {
  const journalInput = document.getElementById("journalInput");
  const charCount    = document.getElementById("charCount");
  if (journalInput) journalInput.value = "";
  if (charCount)    charCount.textContent = "0 words";
  showEmptyState();
};

// ── UI State Helpers ───────────────────────────────────
function showEmptyState()   { setActiveState("emptyState"); }
function showLoadingState() { setActiveState("loadingState"); }
function showResultsState() { setActiveState("resultsState"); }
function showErrorState()   { setActiveState("errorState"); }

function setActiveState(active) {
  ["emptyState","loadingState","resultsState","errorState"].forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      if (id === active) {
        el.classList.remove("hidden");
      } else {
        el.classList.add("hidden");
      }
    }
  });
}

// ── Keyword Analysis (Local) ───────────────────────────
const SIGNAL_MAP = [
  // High-risk signals
  { keyword: "suicide",         label: "Suicidal ideation",     tier: "high-risk" },
  { keyword: "kill myself",     label: "Self-harm thoughts",    tier: "high-risk" },
  { keyword: "want to die",     label: "Death ideation",        tier: "high-risk" },
  { keyword: "end it all",      label: "Crisis intent",         tier: "high-risk" },
  { keyword: "hopeless",        label: "Hopelessness",          tier: "high-risk" },
  { keyword: "worthless",       label: "Low self-worth",        tier: "high-risk" },
  { keyword: "no reason to live",label:"Anhedonia",             tier: "high-risk" },
  { keyword: "no point",        label: "Purpose loss",          tier: "high-risk" },
  { keyword: "better off dead", label: "Passive suicidality",   tier: "high-risk" },
  { keyword: "self harm",       label: "Self-harm",             tier: "high-risk" },
  { keyword: "hurt myself",     label: "Self-harm urge",        tier: "high-risk" },
  { keyword: "give up",         label: "Resignation",           tier: "high-risk" },
  // Moderate signals
  { keyword: "depressed",       label: "Depression indicators", tier: "moderate-risk" },
  { keyword: "sad",             label: "Sadness",               tier: "moderate-risk" },
  { keyword: "lonely",          label: "Loneliness",            tier: "moderate-risk" },
  { keyword: "anxious",         label: "Anxiety",               tier: "moderate-risk" },
  { keyword: "stressed",        label: "Stress",                tier: "moderate-risk" },
  { keyword: "overwhelmed",     label: "Overwhelm",             tier: "moderate-risk" },
  { keyword: "can't sleep",     label: "Sleep disruption",      tier: "moderate-risk" },
  { keyword: "insomnia",        label: "Insomnia",              tier: "moderate-risk" },
  { keyword: "no energy",       label: "Low energy",            tier: "moderate-risk" },
  { keyword: "exhausted",       label: "Exhaustion",            tier: "moderate-risk" },
  { keyword: "tired",           label: "Fatigue",               tier: "moderate-risk" },
  { keyword: "struggling",      label: "Difficulty coping",     tier: "moderate-risk" },
  { keyword: "unmotivated",     label: "Motivation loss",       tier: "moderate-risk" },
  { keyword: "numb",            label: "Emotional numbness",    tier: "moderate-risk" },
  { keyword: "crying",          label: "Emotional distress",    tier: "moderate-risk" },
  { keyword: "hate myself",     label: "Self-hatred",           tier: "moderate-risk" },
  { keyword: "panic",           label: "Panic",                 tier: "moderate-risk" },
  { keyword: "fear",            label: "Fear",                  tier: "moderate-risk" },
  // Positive signals
  { keyword: "happy",           label: "Happiness",             tier: "low-risk" },
  { keyword: "grateful",        label: "Gratitude",             tier: "low-risk" },
  { keyword: "excited",         label: "Excitement",            tier: "low-risk" },
  { keyword: "content",         label: "Contentment",           tier: "low-risk" },
  { keyword: "peaceful",        label: "Peace",                 tier: "low-risk" },
  { keyword: "hopeful",         label: "Hopefulness",           tier: "low-risk" },
  { keyword: "good",            label: "Positive mood",         tier: "low-risk" },
  { keyword: "love",            label: "Connection",            tier: "low-risk" },
  { keyword: "motivated",       label: "Motivation",            tier: "low-risk" },
  { keyword: "great",           label: "Positive state",        tier: "low-risk" },
];

const THEME_MAP = [
  { keywords: ["work", "job", "boss", "colleague", "office", "career"],   theme: "Work & Career Stress" },
  { keywords: ["family", "parent", "mother", "father", "sibling", "home"], theme: "Family Relationships" },
  { keywords: ["friend", "social", "alone", "lonely", "isolated"],         theme: "Social & Loneliness" },
  { keywords: ["school", "study", "exam", "university", "college"],        theme: "Academic Pressure" },
  { keywords: ["health", "sick", "pain", "doctor", "illness"],             theme: "Health Concerns" },
  { keywords: ["money", "financial", "debt", "bills", "broke"],            theme: "Financial Stress" },
  { keywords: ["relationship", "partner", "boyfriend", "girlfriend", "breakup", "divorce"], theme: "Relationship Issues" },
  { keywords: ["sleep", "tired", "insomnia", "rest", "exhausted"],         theme: "Sleep & Energy" },
  { keywords: ["future", "hope", "goal", "dream", "plan"],                 theme: "Future Outlook" },
  { keywords: ["anxiety", "panic", "worry", "fear", "nervous"],            theme: "Anxiety & Fear" },
  { keywords: ["happy", "grateful", "joy", "love", "excited"],             theme: "Positive Emotions" },
];

function analyzeLocally(text) {
  const lower = text.toLowerCase();
  const detectedSignals = SIGNAL_MAP.filter(s => lower.includes(s.keyword));
  const detectedThemes  = THEME_MAP.filter(t => t.keywords.some(k => lower.includes(k))).map(t => t.theme);
  return { detectedSignals, detectedThemes };
}

// ── Guidance Content ───────────────────────────────────
const GUIDANCE = {
  Low: {
    summary: "Your journal entry reflects a generally stable emotional state. Maintaining healthy habits, reflection practices, and social connections are your best allies right now.",
    guidance: "Continue journaling regularly — it's a powerful tool for emotional clarity. Consider adding a short mindfulness or gratitude practice to your routine to reinforce your current positive state. Checking in with yourself periodically helps catch early signs of stress.",
    resources: [
      "Practice 5-minute daily mindfulness: Headspace or Calm app",
      "The Mental Health Foundation: mentalhealth.org.uk",
      "Mood journaling: apps like Daylio help track emotional patterns over time",
    ]
  },
  Moderate: {
    summary: "Your entry shows signs of moderate emotional distress — including stress, low mood, or fatigue. This is common, and reaching out for support early makes a meaningful difference.",
    guidance: "Try the '3-3-3' grounding exercise: name 3 things you see, 3 sounds you hear, and 3 body parts you can feel. It helps reduce anxiety in the moment. Also consider scheduling time for self-care — even 15 minutes of gentle walking, journaling, or talking to someone you trust can provide relief. If these feelings persist beyond two weeks, speaking with a counselor is a healthy next step.",
    resources: [
      "iCall (India): icallhelpline.org | 9152987821",
      "BetterHelp — online licensed therapist sessions: betterhelp.com",
      "Crisis Text Line: text HOME to 741741 (US, UK, Canada, Ireland)",
      "Mind UK: mind.org.uk/information-support",
    ]
  },
  High: {
    summary: "Your entry contains signals that suggest you may be experiencing a significant mental health crisis. Please know that you are not alone, and immediate support is available. Your life has immense value.",
    guidance: "If you are having thoughts of ending your life or harming yourself, please reach out to a crisis line immediately — trained counselors are there 24/7 and want to help. You do not have to carry this alone. Talking to someone — a friend, family member, or professional — is a courageous and important step. Your feelings are real and valid, and with the right support, things can get better.",
    resources: [
      "🆘 iCall (India): 9152987821 (Mon–Sat, 8am–10pm)",
      "🆘 Vandrevala Foundation (India, 24/7): 1860-2662-345",
      "🆘 National Suicide Prevention Lifeline (US, 24/7): 988",
      "🆘 Samaritans (UK, 24/7): 116 123",
      "🆘 Crisis Text Line (Global): text HOME to 741741",
      "International Association for Suicide Prevention: iasp.info/resources/Crisis_Centres",
    ]
  }
};

// ── Render Results ─────────────────────────────────────
function renderResults(risk, confidence, detectedSignals, detectedThemes) {
  const riskClass = risk.toLowerCase();
  const guidanceData = GUIDANCE[risk] || GUIDANCE["Low"];

  // Risk header
  const riskHeader = document.getElementById("riskHeader");
  riskHeader.className = `risk-header ${riskClass}`;

  const riskBadge = document.getElementById("riskBadge");
  riskBadge.className = `risk-badge ${riskClass}`;
  riskBadge.textContent = risk;

  document.getElementById("riskSummary").textContent = guidanceData.summary;

  // Confidence bar
  if (confidence !== null && confidence !== undefined) {
    const pct = Math.round(confidence * 100);
    document.getElementById("confidenceValue").textContent = `${pct}%`;
    const bar = document.getElementById("confidenceBar");
    bar.className = `confidence-bar-inner ${riskClass}`;
    // Defer to allow browser to paint first (for animation)
    setTimeout(() => { bar.style.width = `${pct}%`; }, 80);
  } else {
    document.getElementById("confidenceCard").classList.add("hidden");
  }

  // Emotional signals
  const signalsList = document.getElementById("signalsList");
  signalsList.innerHTML = "";
  if (detectedSignals.length > 0) {
    detectedSignals.slice(0, 10).forEach((s, i) => {
      const chip = document.createElement("span");
      chip.className = `signal-chip ${s.tier}`;
      chip.style.animationDelay = `${i * 0.06}s`;
      chip.textContent = s.label;
      signalsList.appendChild(chip);
    });
  } else {
    const chip = document.createElement("span");
    chip.className = "signal-chip neutral";
    chip.textContent = "No specific emotional signals flagged";
    signalsList.appendChild(chip);
  }

  // Themes
  const themesList = document.getElementById("themesList");
  themesList.innerHTML = "";
  const uniqueThemes = [...new Set(detectedThemes)].slice(0, 6);
  if (uniqueThemes.length > 0) {
    uniqueThemes.forEach(t => {
      const item = document.createElement("div");
      item.className = "theme-item";
      item.innerHTML = `<span class="theme-dot"></span><span>${t}</span>`;
      themesList.appendChild(item);
    });
  } else {
    themesList.innerHTML = `<div class="theme-item"><span class="theme-dot" style="background:var(--text-3)"></span><span style="color:var(--text-3)">No specific themes identified</span></div>`;
  }

  // Guidance
  document.getElementById("guidanceText").textContent = guidanceData.guidance;

  // Resources
  const resourcesList = document.getElementById("resourcesList");
  resourcesList.innerHTML = guidanceData.resources.map(r => `<li>${r}</li>`).join("");

  showResultsState();
}

// ── Main Analyze Function ──────────────────────────────
window.analyzeJournal = async function () {
  const journalInput = document.getElementById("journalInput");
  const analyzeBtn   = document.getElementById("analyzeBtn");
  if (!journalInput || !analyzeBtn) return;

  const text = journalInput.value.trim();

  if (!text || text.split(/\s+/).filter(w => w.length > 0).length < 5) {
    // Show soft inline error without disrupting state
    const prev = analyzeBtn.innerHTML;
    analyzeBtn.innerHTML = `<span class="btn-icon">⚠️</span><span>Write at least a few sentences</span>`;
    analyzeBtn.disabled = true;
    setTimeout(() => {
      analyzeBtn.innerHTML = prev;
      analyzeBtn.disabled = false;
    }, 2500);
    return;
  }

  // Run local analysis immediately (for signals & themes)
  const { detectedSignals, detectedThemes } = analyzeLocally(text);

  // Show loading
  analyzeBtn.disabled = true;
  analyzeBtn.innerHTML = `<span class="btn-icon">⏳</span><span>Analyzing…</span>`;
  showLoadingState();

  let risk = "Low";
  let confidence = null;

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);

    // Attach JWT token if user is logged in
    const authToken = localStorage.getItem('mindease_token');
    const authHeaders = { "Content-Type": "application/json" };
    if (authToken) authHeaders["Authorization"] = `Bearer ${authToken}`;

    const response = await fetch(`${API_BASE_URL}/predict`, {
      method: "POST",
      headers: authHeaders,
      body: JSON.stringify({ journal: text }),
      signal: controller.signal
    });
    clearTimeout(timeout);

    if (response.status === 401) {
      // Token expired — clear and redirect
      localStorage.removeItem('mindease_token');
      localStorage.removeItem('mindease_user');
      window.location.href = 'auth.html';
      return;
    }

    if (!response.ok) throw new Error(`Server responded with ${response.status}`);

    const data = await response.json();
    risk       = data.risk || "Low";
    confidence = data.confidence ?? null;

  } catch (err) {
    console.warn("API unreachable, falling back to keyword model:", err.message);

    // ── Local Fallback Classification ──
    const lower = text.toLowerCase();
    const HIGH_WORDS = ["suicide","kill myself","end it all","want to die","hopeless","worthless","no reason to live","better off dead","self harm","hurt myself","give up","no point"];
    const MOD_WORDS  = ["depressed","sad","lonely","anxious","stressed","overwhelmed","can't sleep","insomnia","no energy","exhausted","tired","struggling","unmotivated","numb","crying","hate myself","panic"];

    const highCount = HIGH_WORDS.filter(w => lower.includes(w)).length;
    const modCount  = MOD_WORDS.filter(w => lower.includes(w)).length;

    if (highCount >= 1) {
      risk = "High"; confidence = highCount >= 2 ? 0.85 : 0.75;
    } else if (modCount >= 3) {
      risk = "Moderate"; confidence = 0.70;
    } else if (modCount >= 1) {
      risk = "Moderate"; confidence = 0.60;
    } else {
      risk = "Low"; confidence = 0.65;
    }
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.innerHTML = `<span class="btn-icon">🔍</span><span>Analyze My Journal</span>`;
  }

  renderResults(risk, confidence, detectedSignals, detectedThemes);

  // Refresh history panel if it's open
  if (typeof window.loadHistory === 'function' && window.historyPanelOpen) {
    setTimeout(() => window.loadHistory(), 500);
  }
};

// ── Music Toggle ───────────────────────────────────────
window.toggleMusic = function () {
  const music  = document.getElementById("calmMusic");
  const btn    = document.getElementById("musicToggle");
  const label  = btn ? btn.querySelector(".music-label") : null;
  if (!music) return;

  if (music.paused) {
    music.play().then(() => {
      if (btn)   btn.classList.add("playing");
      if (label) label.textContent = "Pause Music";
    }).catch(() => {
      alert("Please click anywhere on the page first, then press Play Music.");
    });
  } else {
    music.pause();
    if (btn)   btn.classList.remove("playing");
    if (label) label.textContent = "Calm Music";
  }
};