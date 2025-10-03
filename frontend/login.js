function login(event) {
  event.preventDefault();

  const role = document.getElementById("role").value;
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  // Dummy login (replace with Flask API later)
  if (username && password) {
    localStorage.setItem("userRole", role);
    localStorage.setItem("username", username);
    window.location.href = "dashboard.html"; 
  } else {
    document.getElementById("login-message").textContent = "❌ Invalid login!";
  }
}
