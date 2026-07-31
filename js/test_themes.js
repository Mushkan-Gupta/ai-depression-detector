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
  const detectedThemes  = THEME_MAP.filter(t => t.keywords.some(k => lower.includes(k))).map(t => t.theme);
  return detectedThemes;
}

const tests = [
  "I am feeling anxious and lonely lately, but I am managing okay.",
  "I feel anxious about my exams but my friends are supporting me.",
  "I am not lonely anymore and I feel happy today.",
  "Work has been stressful and I cannot sleep properly.",
  "Today was a normal day. I completed my assignments and watched a movie."
];

tests.forEach((t, i) => {
    console.log(String.fromCharCode(97 + i) + ".", JSON.stringify(analyzeLocally(t)));
});
