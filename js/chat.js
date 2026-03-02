function sendMessage() {
  const input = document.getElementById("userInput");
  const messages = document.getElementById("messages");
  const orb = document.getElementById("aiOrb");

  if (!input.value.trim()) return;

  const text = input.value.toLowerCase();

  // USER MESSAGE
  const user = document.createElement("div");
  user.className = "msg user";
  user.innerText = input.value;
  messages.appendChild(user);
  input.value = "";

  // EMOTION DETECTION (basic but effective)
  orb.classList.remove("calm", "sad", "stressed");

  if (text.includes("sad") || text.includes("lonely")) {
    orb.classList.add("sad");
  } else if (text.includes("stress") || text.includes("anxious")) {
    orb.classList.add("stressed");
  } else {
    orb.classList.add("calm");
  }

  // RIPPLE EFFECT
  const ripple = document.createElement("div");
  ripple.className = "ripple";
  orb.appendChild(ripple);
  setTimeout(() => ripple.remove(), 1800);

  // AI RESPONSE
  setTimeout(() => {
    const bot = document.createElement("div");
    bot.className = "msg bot";
    bot.innerText =
      "I’m sensing how you feel 💙  Take a slow breath… I’m here with you.";
    messages.appendChild(bot);
    messages.scrollTop = messages.scrollHeight;
  }, 1200);
}

function toggleMusic() {
  const music = document.getElementById("calmMusic");
  music.paused ? music.play() : music.pause();
}
