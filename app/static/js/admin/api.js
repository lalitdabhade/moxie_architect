/* Shared admin helpers: CSRF-aware fetch, flash messages, logout. */
(function () {
  "use strict";

  function csrfToken() {
    var meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }

  /**
   * fetch wrapper for /api/admin. Returns parsed JSON (or null for empty bodies).
   * Throws an Error with .status and .fields on non-2xx responses.
   * A 401 sends the user back to the login page.
   */
  async function request(method, url, body) {
    var opts = { method: method, headers: { "Accept": "application/json" }, credentials: "same-origin" };
    if (method !== "GET") opts.headers["X-CSRF-Token"] = csrfToken();
    if (body instanceof FormData) {
      opts.body = body;
    } else if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    var res = await fetch(url, opts);
    var data = null;
    var text = await res.text();
    if (text) {
      try { data = JSON.parse(text); } catch (e) { data = null; }
    }
    if (!res.ok) {
      if (res.status === 401 && !url.endsWith("/login")) {
        window.location.href = "/admin/login";
      }
      var err = new Error((data && data.error && data.error.message) || "Request failed (" + res.status + ").");
      err.status = res.status;
      err.fields = (data && data.error && data.error.fields) || {};
      throw err;
    }
    return data;
  }

  var flashTimer;
  function flash(message, kind) {
    var el = document.getElementById("flash");
    if (!el) return;
    el.textContent = message;
    el.className = "flash flash-" + (kind || "success");
    el.hidden = false;
    clearTimeout(flashTimer);
    flashTimer = setTimeout(function () { el.hidden = true; }, 5000);
  }

  // Flash messages that survive a redirect.
  function flashNext(message, kind) {
    try { sessionStorage.setItem("admin-flash", JSON.stringify({ m: message, k: kind || "success" })); } catch (e) {}
  }
  document.addEventListener("DOMContentLoaded", function () {
    try {
      var saved = sessionStorage.getItem("admin-flash");
      if (saved) {
        sessionStorage.removeItem("admin-flash");
        var f = JSON.parse(saved);
        flash(f.m, f.k);
      }
    } catch (e) {}
  });

  document.addEventListener("click", async function (e) {
    var btn = e.target.closest("[data-logout]");
    if (!btn) return;
    btn.disabled = true;
    try { await request("POST", "/api/admin/logout"); } catch (err) { /* session may already be gone */ }
    window.location.href = "/admin/login";
  });

  window.AdminApi = {
    get: function (url) { return request("GET", url); },
    post: function (url, body) { return request("POST", url, body); },
    put: function (url, body) { return request("PUT", url, body); },
    patch: function (url, body) { return request("PATCH", url, body); },
    del: function (url) { return request("DELETE", url); },
    flash: flash,
    flashNext: flashNext
  };
})();
