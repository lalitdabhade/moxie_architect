(function () {
  "use strict";
  var api = window.AdminApi;
  var project = JSON.parse(document.getElementById("project-data").textContent);
  var base = "/api/admin/projects/" + project.id;

  /* ---------- details ---------- */
  var details = document.getElementById("details-form");
  var detailsError = details.querySelector(".form-error");

  details.addEventListener("submit", async function (e) {
    e.preventDefault();
    detailsError.hidden = true;
    var title = details.title.value.trim();
    if (title.length < 2) {
      api.showFieldErrors(details, { title: "Title must be at least 2 characters." });
      return;
    }
    api.clearFieldErrors(details);
    var btn = details.querySelector("button[type=submit]");
    btn.disabled = true;
    try {
      var res = await api.patch(base, { title: title, section_id: parseInt(details.section_id.value, 10) });
      project = res.project;
      document.getElementById("page-title").textContent = project.title;
      api.flash("Details saved.");
    } catch (err) {
      api.showFieldErrors(details, err.fields);
      detailsError.textContent = err.message;
      detailsError.hidden = false;
    } finally {
      btn.disabled = false;
    }
  });

  /* ---------- image grid ---------- */
  var grid = document.getElementById("image-grid");
  var noImages = document.getElementById("no-images");
  var countEl = document.getElementById("image-count");
  var busy = false;

  function renderImages() {
    grid.textContent = "";
    var n = project.images.length;
    project.images.forEach(function (img, i) {
      var li = document.createElement("li");
      li.className = "image-card";
      li.draggable = true;
      li.dataset.id = String(img.id);

      var pic = document.createElement("img");
      pic.src = img.url;
      pic.alt = "Image " + (i + 1);
      pic.loading = "lazy";
      pic.draggable = false;

      var badge = document.createElement("span");
      badge.className = "image-pos";
      badge.textContent = i === 0 ? "1 · Cover" : String(i + 1);

      var tools = document.createElement("div");
      tools.className = "image-tools";
      tools.append(
        toolButton("←", "Move earlier", "left", i === 0),
        toolButton("→", "Move later", "right", i === n - 1),
        toolButton("Remove", "Remove image " + (i + 1), "remove", false)
      );
      li.append(pic, badge, tools);
      grid.appendChild(li);
    });
    noImages.hidden = n > 0;
    countEl.textContent = String(n);
  }

  function toolButton(text, label, action, disabled) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "image-tool" + (action === "remove" ? " image-tool-danger" : "");
    b.textContent = text;
    b.setAttribute("aria-label", label);
    b.dataset.action = action;
    b.disabled = disabled;
    return b;
  }

  async function saveOrder(ids) {
    var previous = project.images.slice();
    // Optimistic update so the grid responds instantly.
    var byId = {};
    project.images.forEach(function (img) { byId[img.id] = img; });
    project.images = ids.map(function (id) { return byId[id]; });
    renderImages();
    busy = true;
    try {
      var res = await api.put(base + "/images/order", { image_ids: ids });
      project = res.project;
      renderImages();
      api.flash("Order saved.");
    } catch (err) {
      project.images = previous;
      renderImages();
      api.flash(err.message, "error");
    } finally {
      busy = false;
    }
  }

  function currentIds() {
    return project.images.map(function (img) { return img.id; });
  }

  grid.addEventListener("click", async function (e) {
    var btn = e.target.closest("[data-action]");
    if (!btn || busy) return;
    var card = btn.closest(".image-card");
    var id = parseInt(card.dataset.id, 10);
    var ids = currentIds();
    var i = ids.indexOf(id);

    if (btn.dataset.action === "left" || btn.dataset.action === "right") {
      var j = btn.dataset.action === "left" ? i - 1 : i + 1;
      if (j < 0 || j >= ids.length) return;
      ids[i] = ids[j];
      ids[j] = id;
      await saveOrder(ids);
      var moved = grid.querySelector('[data-id="' + id + '"] [data-action="' + btn.dataset.action + '"]');
      if (moved && !moved.disabled) moved.focus();
      return;
    }

    if (btn.dataset.action === "remove") {
      if (!window.confirm("Remove this image? This cannot be undone.")) return;
      busy = true;
      btn.disabled = true;
      try {
        var res = await api.del(base + "/images/" + id);
        project = res.project;
        renderImages();
        api.flash("Image removed.");
      } catch (err) {
        api.flash(err.message, "error");
        btn.disabled = false;
      } finally {
        busy = false;
      }
    }
  });

  // Drag and drop reordering (desktop). Touch users use the arrow buttons.
  var dragId = null;
  grid.addEventListener("dragstart", function (e) {
    var card = e.target.closest(".image-card");
    if (!card || busy) { e.preventDefault(); return; }
    dragId = parseInt(card.dataset.id, 10);
    card.classList.add("is-dragging");
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", String(dragId));
  });
  grid.addEventListener("dragover", function (e) {
    if (dragId === null) return;
    e.preventDefault();
    var over = e.target.closest(".image-card");
    var dragging = grid.querySelector(".is-dragging");
    if (!over || !dragging || over === dragging) return;
    var rect = over.getBoundingClientRect();
    var after = (e.clientX - rect.left) > rect.width / 2;
    grid.insertBefore(dragging, after ? over.nextSibling : over);
  });
  grid.addEventListener("dragend", function () {
    var dragging = grid.querySelector(".is-dragging");
    if (dragging) dragging.classList.remove("is-dragging");
    if (dragId === null) return;
    dragId = null;
    var ids = Array.prototype.map.call(grid.querySelectorAll(".image-card"), function (el) {
      return parseInt(el.dataset.id, 10);
    });
    if (ids.join(",") !== currentIds().join(",")) saveOrder(ids);
  });

  renderImages();

  /* ---------- add images ---------- */
  var addForm = document.getElementById("add-images-form");
  var addError = addForm.querySelector(".form-error");
  var progress = addForm.querySelector(".progress");
  var bar = addForm.querySelector(".progress-bar");
  var addBtn = addForm.querySelector("button[type=submit]");
  var picker = new window.ImagePicker(document.getElementById("add-images"), function (n) {
    addBtn.disabled = n === 0;
    addBtn.textContent = n ? "Upload " + n + " image" + (n === 1 ? "" : "s") : "Upload images";
  });
  addBtn.disabled = true;

  addForm.addEventListener("submit", async function (e) {
    e.preventDefault();
    addError.hidden = true;
    var files = picker.files();
    if (!files.length) return;
    var data = new FormData();
    files.forEach(function (f) { data.append("images", f, f.name); });
    addBtn.disabled = true;
    progress.hidden = false;
    bar.style.width = "0%";
    try {
      var res = await api.upload(base + "/images", data, function (p) {
        bar.style.width = Math.round(p * 100) + "%";
      });
      project = res.project;
      renderImages();
      picker.clear();
      api.flash(files.length + " image" + (files.length === 1 ? "" : "s") + " added.");
    } catch (err) {
      addError.textContent = err.message;
      addError.hidden = false;
      addBtn.disabled = false;
    } finally {
      progress.hidden = true;
    }
  });

  /* ---------- delete project ---------- */
  document.getElementById("delete-project").addEventListener("click", async function () {
    if (!window.confirm("Delete “" + project.title + "” and all its images? This cannot be undone.")) return;
    this.disabled = true;
    try {
      await api.del(base);
      api.flashNext("Project “" + project.title + "” deleted.");
      window.location.href = "/admin/projects?section=" + project.section.slug;
    } catch (err) {
      api.flash(err.message, "error");
      this.disabled = false;
    }
  });
})();
