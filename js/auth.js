function showSignup() {
  loginBox.classList.add("hidden");
  signupBox.classList.remove("hidden");
}

function showLogin() {
  signupBox.classList.add("hidden");
  loginBox.classList.remove("hidden");
}

/* Email Validation */
function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

/* Password Validation */
function isValidPassword(password) {
  return /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$/.test(password);
}

function signup() {
  const email = signupEmail.value;
  const password = signupPassword.value;

  if (!isValidEmail(email)) {
    signupError.innerText = "Invalid email format";
    return;
  }

  if (!isValidPassword(password)) {
    signupError.innerText = "Weak password";
    return;
  }

  localStorage.setItem("userEmail", email);
  localStorage.setItem("userPassword", password);
  alert("Signup successful! Please login.");
  showLogin();
}

function login() {
  const email = loginEmail.value;
  const password = loginPassword.value;

  if (
    email === localStorage.getItem("userEmail") &&
    password === localStorage.getItem("userPassword")
  ) {
    localStorage.setItem("isLoggedIn", "true");
    window.location.href = "home.html";
  } else {
    loginError.innerText = "Invalid credentials";
  }
}
function logout() {
  // remove login state
  localStorage.removeItem("isLoggedIn");

  // redirect to login page
  window.location.href = "index.html"; 
  // or login.html (use your actual login file name)
}
