(function () {
  "use strict";
  var form = document.getElementById("login-form");
  var errorEl = document.getElementById("login-error");

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.hidden = false;
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    errorEl.hidden = true;
    var username = form.username.value.trim();
    var password = form.password.value;
    if (!username || !password) {
      showError("Please enter your username and password.");
      return;
    }
    var button = form.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      var res = await fetch("/api/admin/login", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "Accept": "application/json",
          "X-CSRF-Token": form.dataset.csrf
        },
        body: JSON.stringify({ username: username, password: password })
      });
      if (res.ok) {
        window.location.href = "/admin";
        return;
      }
      var data = await res.json().catch(function () { return null; });
      showError((data && data.error && data.error.message) || "Login failed. Please try again.");
      form.password.value = "";
      form.password.focus();
    } catch (err) {
      showError("Could not reach the server. Please try again.");
    } finally {
      button.disabled = false;
    }
  });
})();
