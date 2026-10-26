(function () {
  "use strict";
  var api = window.AdminApi;
  var list = document.getElementById("project-list");
  if (!list) return;

  list.addEventListener("click", async function (e) {
    var btn = e.target.closest("[data-delete-project]");
    if (!btn) return;
    var title = btn.dataset.title;
    if (!window.confirm("Delete “" + title + "” and all its images? This cannot be undone.")) return;
    btn.disabled = true;
    try {
      await api.del("/api/admin/projects/" + btn.dataset.deleteProject);
      btn.closest(".project-row").remove();
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
