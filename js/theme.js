// theme.js – handles dark/light toggle + landing-to-dashboard transition

document.addEventListener("DOMContentLoaded", () => {

  // ── Theme Initialization ───────────────────────────
  const saved = localStorage.getItem("theme") || "dark";
  applyTheme(saved);

  function applyTheme(theme) {
    if (theme === "light") {
      document.body.classList.add("light");
    } else {
      document.body.classList.remove("light");
    }
    const icon = theme === "light" ? "☀️" : "🌙";
    document.querySelectorAll(".theme-btn").forEach(btn => btn.textContent = icon);
    localStorage.setItem("theme", theme);
  }

  function toggleTheme() {
    const current = document.body.classList.contains("light") ? "light" : "dark";
    applyTheme(current === "light" ? "dark" : "light");
  }

  document.querySelectorAll(".theme-btn").forEach(btn => {
    btn.addEventListener("click", toggleTheme);
  });

  // ── Landing → Dashboard Transition ────────────────
  const enterBtn    = document.getElementById("enterBtn");
  const landingPage = document.getElementById("landingPage");
  const dashboard   = document.getElementById("appDashboard");

  if (enterBtn && landingPage && dashboard) {
    enterBtn.addEventListener("click", () => {
      landingPage.classList.add("fade-out");
      setTimeout(() => {
        landingPage.classList.add("hidden");
        landingPage.classList.remove("fade-out");
        dashboard.classList.remove("hidden");
        dashboard.classList.add("fade-in");
        setTimeout(() => dashboard.classList.remove("fade-in"), 600);
      }, 550);
    });
  }

});