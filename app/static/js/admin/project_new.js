(function () {
  "use strict";
  var api = window.AdminApi;
  var form = document.getElementById("project-form");
  var picker = new window.ImagePicker(document.getElementById("new-images"));
  var errorEl = form.querySelector(".form-error");
  var progress = form.querySelector(".progress");
  var bar = form.querySelector(".progress-bar");
  var submit = form.querySelector("button[type=submit]");

  function showError(msg) {
    errorEl.textContent = msg;
    errorEl.hidden = !msg;
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    showError("");
    var fields = {};
    if (!form.section_id.value) fields.section_id = "Choose a section.";
    var title = form.title.value.trim();
    if (title.length < 2) fields.title = "Title must be at least 2 characters.";
    if (picker.files().length === 0) fields.images = "Add at least one image.";
    if (api.showFieldErrors(form, fields)) return;

    var data = new FormData();
    data.append("section_id", form.section_id.value);
    data.append("title", title);
    picker.files().forEach(function (f) { data.append("images", f, f.name); });

    submit.disabled = true;
    progress.hidden = false;
    bar.style.width = "0%";
    try {
      var res = await api.upload("/api/admin/projects", data, function (p) {
        bar.style.width = Math.round(p * 100) + "%";
      });
      api.flashNext("Project “" + res.project.title + "” created.");
      window.location.href = "/admin/projects/" + res.project.id;
    } catch (err) {
      api.showFieldErrors(form, err.fields);
      showError(err.message);
      submit.disabled = false;
      progress.hidden = true;
    }
  });
})();
