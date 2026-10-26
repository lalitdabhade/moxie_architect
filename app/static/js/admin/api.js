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

  /** Multipart upload with progress (fetch cannot report upload progress). */
  function upload(url, formData, onProgress) {
    return new Promise(function (resolve, reject) {
      var xhr = new XMLHttpRequest();
      xhr.open("POST", url);
      xhr.setRequestHeader("Accept", "application/json");
      xhr.setRequestHeader("X-CSRF-Token", csrfToken());
      if (onProgress) {
        xhr.upload.addEventListener("progress", function (e) {
          if (e.lengthComputable) onProgress(e.loaded / e.total);
        });
      }
      xhr.onload = function () {
        var data = null;
        try { data = JSON.parse(xhr.responseText); } catch (e) { data = null; }
        if (xhr.status >= 200 && xhr.status < 300) return resolve(data);
        if (xhr.status === 401) window.location.href = "/admin/login";
        var err = new Error((data && data.error && data.error.message) || "Upload failed (" + xhr.status + ").");
        err.status = xhr.status;
        err.fields = (data && data.error && data.error.fields) || {};
        reject(err);
      };
      xhr.onerror = function () { reject(new Error("Network error - could not reach the server.")); };
      xhr.send(formData);
    });
  }

  /** Show per-field errors on elements with data-field="name"; returns true if any were shown. */
  function showFieldErrors(form, fields) {
    clearFieldErrors(form);
    var shown = false;
    Object.keys(fields || {}).forEach(function (name) {
      var wrap = form.querySelector('[data-field="' + name + '"]');
      if (!wrap) return;
      wrap.classList.add("has-error");
      var p = document.createElement("p");
      p.className = "field-error";
      p.textContent = fields[name];
      wrap.appendChild(p);
      shown = true;
    });
    return shown;
  }

  function clearFieldErrors(form) {
    form.querySelectorAll(".has-error").forEach(function (el) { el.classList.remove("has-error"); });
    form.querySelectorAll(".field-error").forEach(function (el) { el.remove(); });
  }

  function formatBytes(n) {
    if (n < 1024) return n + " B";
    if (n < 1048576) return Math.round(n / 1024) + " KB";
    return (n / 1048576).toFixed(1) + " MB";
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
    upload: upload,
    showFieldErrors: showFieldErrors,
    clearFieldErrors: clearFieldErrors,
    formatBytes: formatBytes,
    flash: flash,
    flashNext: flashNext
  };
})();
