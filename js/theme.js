// theme.js – handles dark/light toggle for all pages (index.html, auth.html)

document.addEventListener("DOMContentLoaded", () => {

  // ── Theme Initialization ───────────────────────────
  // Support both 'theme' key (old) and 'mindease_theme' key (new auth.js uses mindease_theme)
  const saved = localStorage.getItem("mindease_theme") || localStorage.getItem("theme") || "dark";
  applyTheme(saved);

  function applyTheme(theme) {
    // Support .light class (home.css) and data-theme attr (auth.css) simultaneously
    if (theme === "light") {
      document.body.classList.add("light");
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      document.body.classList.remove("light");
      document.documentElement.setAttribute("data-theme", "dark");
    }
    const icon = theme === "light" ? "☀️" : "🌙";
    document.querySelectorAll(".theme-btn").forEach(btn => btn.textContent = icon);
    // Save under both keys for compatibility
    localStorage.setItem("theme", theme);
    localStorage.setItem("mindease_theme", theme);
  }

  function toggleTheme() {
    const current = document.body.classList.contains("light") ? "light" : "dark";
    applyTheme(current === "light" ? "dark" : "light");
  }

  document.querySelectorAll(".theme-btn").forEach(btn => {
    btn.addEventListener("click", toggleTheme);
  });

});