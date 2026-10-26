(function () {
  "use strict";
  var api = window.AdminApi;
  var list = document.getElementById("project-list");
  if (!list) return;

  function decrementCount(key) {
    var el = document.querySelector('[data-count-for="' + key + '"]');
    if (el) el.textContent = String(Math.max(0, parseInt(el.textContent, 10) - 1));
  }

  list.addEventListener("click", async function (e) {
    var btn = e.target.closest("[data-delete-project]");
    if (!btn) return;
    var title = btn.dataset.title;
    if (!window.confirm("Delete “" + title + "” and all its images? This cannot be undone.")) return;
    btn.disabled = true;
    try {
      await api.del("/api/admin/projects/" + btn.dataset.deleteProject);
      var row = btn.closest(".project-row");
      decrementCount("all");
      decrementCount(row.dataset.section);
      row.remove();
      api.flash("Project “" + title + "” deleted.");
      if (!list.children.length) {
        list.remove();
        document.getElementById("empty-state").hidden = false;
      }
    } catch (err) {
      api.flash(err.message, "error");
      btn.disabled = false;
    }
  });
})();
