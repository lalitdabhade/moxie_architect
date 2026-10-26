/* Inquiry form: switches fields by service type, validates on the client (the server re-validates),
   and submits as multipart/form-data to POST /api/inquiries. */
(function () {
  "use strict";

  var form = document.getElementById("inquiry-form");
  if (!form) return;
  var success = document.getElementById("inquiry-success");
  var successText = document.getElementById("success-text");
  var errorEl = document.getElementById("inquiry-error");
  var submitBtn = form.querySelector("button[type=submit]");
  var branches = {
    interior: form.querySelector('[data-branch="interior"]'),
    bungalow_apartment: form.querySelector('[data-branch="bungalow_apartment"]'),
    budget: form.querySelector('[data-branch="budget"]')
  };
  var otherWrap = document.getElementById("other-wrap");
  var otherInput = document.getElementById("house_type_other");
  var layoutInput = document.getElementById("layout");
  var layoutName = document.getElementById("layout-name");
  var maxBytes = parseInt(form.dataset.maxBytes, 10);
  var areaMin = parseInt(form.dataset.areaMin, 10);
  var areaMax = parseInt(form.dataset.areaMax, 10);
  var EMAIL_RE = /^[^\s@]+@[^\s@]+\.[A-Za-z]{2,}$/;
  var fields = {
    name: document.getElementById("name"),
    mobile: document.getElementById("mobile"),
    email: document.getElementById("email"),
    address: document.getElementById("address"),
    area: document.getElementById("area_sqft")
  };

  function checked(name) {
    var el = form.querySelector('input[name="' + name + '"]:checked');
    return el ? el.value : "";
  }

  /* ---------- dynamic sections ---------- */

  // Hidden sections are also disabled, so their fields are neither validated nor submitted.
  function setBranch(fieldset, on) {
    fieldset.hidden = !on;
    fieldset.disabled = !on;
  }

  function syncBranches() {
    var service = checked("service_type");
    setBranch(branches.interior, service === "interior");
    setBranch(branches.bungalow_apartment, service === "bungalow_apartment");
    setBranch(branches.budget, service !== "");
    syncOther();
  }

  function syncOther() {
    var on = !branches.interior.hidden && checked("house_type") === "other";
    otherWrap.hidden = !on;
    otherInput.disabled = !on;
  }

  /* ---------- errors ---------- */

  function setFieldError(name, message) {
    var wrap = form.querySelector('[data-field="' + name + '"]');
    if (!wrap) return;
    clearFieldError(name);
    wrap.classList.add("has-error");
    var p = document.createElement("p");
    p.className = "field-error";
    p.id = "err-" + name;
    p.textContent = message;
    wrap.appendChild(p);
    wrap.querySelectorAll("input, textarea, select").forEach(function (input) {
      input.setAttribute("aria-invalid", "true");
      input.setAttribute("aria-describedby", p.id);
    });
  }

  function clearFieldError(name) {
    var wrap = form.querySelector('[data-field="' + name + '"]');
    if (!wrap) return;
    wrap.classList.remove("has-error");
    var p = wrap.querySelector(".field-error");
    if (p) p.remove();
    wrap.querySelectorAll("[aria-invalid]").forEach(function (input) {
      input.removeAttribute("aria-invalid");
      input.removeAttribute("aria-describedby");
    });
  }

  function clearAllErrors() {
    form.querySelectorAll(".has-error").forEach(function (wrap) { clearFieldError(wrap.dataset.field); });
    errorEl.hidden = true;
  }

  function focusFirstError() {
    var wrap = form.querySelector(".has-error");
    if (!wrap) return;
    var input = wrap.querySelector("input:not([type=radio]), textarea") || wrap.querySelector("input");
    wrap.scrollIntoView({ behavior: "smooth", block: "center" });
    if (input) input.focus({ preventScroll: true });
  }

  /* ---------- validation (mirrors the server rules) ---------- */

  function sniff(bytes) {
    if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return "jpeg";
    if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) return "png";
    if (bytes[0] === 0x25 && bytes[1] === 0x50 && bytes[2] === 0x44 && bytes[3] === 0x46 && bytes[4] === 0x2d) return "pdf";
    return null;
  }

  async function validateLayout(file) {
    if (!file) return "Upload your layout (JPG, PNG or PDF).";
    var ext = (file.name.match(/\.[^.]+$/) || [""])[0].toLowerCase();
    var allowed = { ".jpg": "jpeg", ".jpeg": "jpeg", ".png": "png", ".pdf": "pdf" };
    if (!allowed[ext]) return "Only JPG, PNG or PDF files are allowed.";
    if (file.size === 0) return "The file is empty.";
    if (file.size > maxBytes) return "Maximum file size is " + Math.round(maxBytes / 1048576) + " MB.";
    var kind = sniff(new Uint8Array(await file.slice(0, 8).arrayBuffer()));
    if (!kind) return "File content is not a valid JPG, PNG or PDF file.";
    if (kind !== allowed[ext]) return "File extension does not match its content.";
    return null;
  }

  function textRule(value, label, min) {
    var v = value.trim();
    if (!v) return label + " is required.";
    if (v.length < min) return label + " must be at least " + min + " characters.";
    return null;
  }

  async function validate() {
    var errors = {};
    var e;
    if ((e = textRule(fields.name.value, "Name", 2))) errors.name = e;
    var mobile = fields.mobile.value.replace(/[\s-]/g, "");
    if (!mobile) errors.mobile = "Mobile number is required.";
    else if (!/^\d{10}$/.test(mobile)) errors.mobile = "Enter a valid 10-digit mobile number.";
    var email = fields.email.value.trim();
    if (!email) errors.email = "Email is required.";
    else if (!EMAIL_RE.test(email)) errors.email = "Enter a valid email address.";
    if ((e = textRule(fields.address.value, "Address", 5))) errors.address = e;

    var service = checked("service_type");
    if (!service) errors.service_type = "Choose the service you need.";
    if (service === "interior") {
      var house = checked("house_type");
      if (!house) errors.house_type = "Choose a house type.";
      if (house === "other" && (e = textRule(otherInput.value, "House type", 2))) errors.house_type_other = e;
    }
    if (service === "bungalow_apartment") {
      var area = fields.area.value.trim();
      if (!area) errors.area_sqft = "Area is required.";
      else if (!/^\d+$/.test(area)) errors.area_sqft = "Enter the area as a whole number of square feet.";
      else if (+area < areaMin || +area > areaMax) {
        errors.area_sqft = "Area must be between " + areaMin.toLocaleString("en-IN") + " and " +
          areaMax.toLocaleString("en-IN") + " sq ft.";
      }
      var layoutError = await validateLayout(layoutInput.files[0]);
      if (layoutError) errors.layout = layoutError;
    }
    if (service && !checked("budget_range")) errors.budget_range = "Choose a budget range.";
    return errors;
  }

  /* ---------- events ---------- */

  form.addEventListener("change", function (e) {
    var name = e.target.name;
    if (name === "service_type") {
      syncBranches();
      clearFieldError("service_type");
    } else if (name === "house_type") {
      syncOther();
      clearFieldError("house_type");
      if (checked("house_type") === "other") otherInput.focus();
    } else if (name === "budget_range") {
      clearFieldError("budget_range");
    }
  });

  form.addEventListener("input", function (e) {
    if (e.target === fields.mobile) {
      // Digits only, max 10.
      var digits = fields.mobile.value.replace(/\D/g, "").slice(0, 10);
      if (digits !== fields.mobile.value) fields.mobile.value = digits;
    }
    if (e.target.name && e.target.type !== "radio") clearFieldError(e.target.name);
  });

  layoutInput.addEventListener("change", async function () {
    var file = layoutInput.files[0];
    layoutName.textContent = file ? file.name + " (" + formatSize(file.size) + ")" : "No file chosen";
    clearFieldError("layout");
    if (file) {
      var problem = await validateLayout(file);
      if (problem) setFieldError("layout", problem);
    }
  });

  function formatSize(n) {
    return n < 1048576 ? Math.max(1, Math.round(n / 1024)) + " KB" : (n / 1048576).toFixed(1) + " MB";
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    clearAllErrors();
    var errors = await validate();
    var names = Object.keys(errors);
    if (names.length) {
      names.forEach(function (n) { setFieldError(n, errors[n]); });
      errorEl.textContent = "Please correct the highlighted fields.";
      errorEl.hidden = false;
      focusFirstError();
      return;
    }

    submitBtn.disabled = true;
    submitBtn.textContent = "Sending…";
    try {
      // FormData skips disabled controls, so only the visible section's fields are sent.
      var res = await fetch("/api/inquiries", {
        method: "POST",
        body: new FormData(form),
        headers: { "Accept": "application/json" }
      });
      var data = await res.json().catch(function () { return null; });
      if (!res.ok) {
        var err = (data && data.error) || {};
        Object.keys(err.fields || {}).forEach(function (n) { setFieldError(n, err.fields[n]); });
        errorEl.textContent = err.message || "Something went wrong. Please try again.";
        errorEl.hidden = false;
        focusFirstError();
        return;
      }
      showSuccess(data.message);
    } catch (err) {
      errorEl.textContent = "Could not reach the server. Please check your connection and try again.";
      errorEl.hidden = false;
    } finally {
      submitBtn.disabled = false;
      submitBtn.textContent = "Send inquiry";
    }
  });

  function resetForm() {
    form.reset();
    clearAllErrors();
    layoutName.textContent = "No file chosen";
    syncBranches();
  }

  function showSuccess(message) {
    resetForm();
    successText.textContent = message;
    form.hidden = true;
    success.hidden = false;
    success.scrollIntoView({ behavior: "smooth", block: "center" });
    success.focus({ preventScroll: true });
  }

  document.getElementById("send-another").addEventListener("click", function () {
    success.hidden = true;
    form.hidden = false;
    fields.name.focus();
  });

  syncBranches(); // handles browsers that restore radio state on back/forward
})();
