(function () {
  "use strict";
  var api = window.AdminApi;
  var btn = document.getElementById("delete-inquiry");

  btn.addEventListener("click", async function () {
    var name = btn.dataset.name;
    if (!window.confirm("Delete the inquiry from " + name + "? Any uploaded layout will also be deleted. This cannot be undone.")) return;
    btn.disabled = true;
    try {
      await api.del("/api/admin/inquiries/" + btn.dataset.id);
      api.flashNext("Inquiry from " + name + " deleted.");
      window.location.href = "/admin/inquiries";
    } catch (err) {
      api.flash(err.message, "error");
      btn.disabled = false;
    }
  });
})();
