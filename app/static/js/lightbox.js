/* Full-screen image lightbox built on <dialog> (native focus trapping + Esc to close). */
(function () {
  "use strict";

  var SWIPE_PX = 40;
  var dialog, img, caption, counter, prevBtn, nextBtn;
  var items = [];
  var index = 0;
  var title = "";
  var opener = null;

  function build() {
    dialog = document.createElement("dialog");
    dialog.className = "lightbox";
    dialog.setAttribute("aria-label", "Image viewer");
    dialog.innerHTML =
      '<div class="lightbox-stage">' +
        '<figure class="lightbox-figure">' +
          '<img class="lightbox-img" alt="">' +
          '<figcaption class="lightbox-caption"><span class="lightbox-title"></span>' +
          '<span class="lightbox-counter"></span></figcaption>' +
        '</figure>' +
      '</div>' +
      '<button type="button" class="lightbox-btn lightbox-close" aria-label="Close">' +
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg></button>' +
      '<button type="button" class="lightbox-btn lightbox-prev" aria-label="Previous image">' +
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 5l-7 7 7 7"/></svg></button>' +
      '<button type="button" class="lightbox-btn lightbox-next" aria-label="Next image">' +
        '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5l7 7-7 7"/></svg></button>';
    document.body.appendChild(dialog);

    img = dialog.querySelector(".lightbox-img");
    caption = dialog.querySelector(".lightbox-title");
    counter = dialog.querySelector(".lightbox-counter");
    prevBtn = dialog.querySelector(".lightbox-prev");
    nextBtn = dialog.querySelector(".lightbox-next");

    dialog.querySelector(".lightbox-close").addEventListener("click", close);
    prevBtn.addEventListener("click", function () { show(index - 1); });
    nextBtn.addEventListener("click", function () { show(index + 1); });
    img.addEventListener("load", function () { img.classList.remove("is-loading"); });

    dialog.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") { e.preventDefault(); show(index - 1); }
      else if (e.key === "ArrowRight") { e.preventDefault(); show(index + 1); }
    });
    dialog.addEventListener("close", afterClose);

    // Clicking the dark area around the image closes the viewer.
    var stage = dialog.querySelector(".lightbox-stage");
    var downOnStage = false;
    stage.addEventListener("pointerdown", function (e) { downOnStage = e.target === stage || e.target.classList.contains("lightbox-figure"); });
    stage.addEventListener("click", function (e) {
      if (downOnStage && (e.target === stage || e.target.classList.contains("lightbox-figure"))) close();
    });

    // Swipe left/right.
    var startX = 0, startY = 0, tracking = false;
    stage.addEventListener("pointerdown", function (e) {
      if (!e.isPrimary) return;
      tracking = true;
      startX = e.clientX;
      startY = e.clientY;
    });
    stage.addEventListener("pointerup", function (e) {
      if (!tracking) return;
      tracking = false;
      var dx = e.clientX - startX;
      var dy = e.clientY - startY;
      if (Math.abs(dx) > SWIPE_PX && Math.abs(dx) > Math.abs(dy) * 1.2) {
        downOnStage = false; // don't treat the end of a swipe as a click-to-close
        show(dx < 0 ? index + 1 : index - 1);
      }
    });
    stage.addEventListener("pointercancel", function () { tracking = false; });
    img.addEventListener("dragstart", function (e) { e.preventDefault(); });
  }

  function preload(i) {
    if (items.length < 2) return;
    var pre = new Image();
    pre.src = items[(i + items.length) % items.length];
  }

  function show(i) {
    index = (i + items.length) % items.length;
    var url = items[index];
    if (img.getAttribute("src") !== url) {
      img.classList.add("is-loading");
      img.src = url;
      if (img.complete) img.classList.remove("is-loading");
    }
    img.alt = title + " — image " + (index + 1) + " of " + items.length;
    caption.textContent = title;
    counter.textContent = items.length > 1 ? (index + 1) + " / " + items.length : "";
    preload(index + 1);
    preload(index - 1);
  }

  function open(urls, start, projectTitle, openerEl) {
    if (!dialog) build();
    items = urls;
    title = projectTitle || "";
    opener = openerEl || null;
    var multiple = items.length > 1;
    prevBtn.hidden = !multiple;
    nextBtn.hidden = !multiple;
    show(start || 0);
    document.body.classList.add("lightbox-open");
    dialog.showModal();
    dialog.querySelector(".lightbox-close").focus();
  }

  function close() {
    if (dialog && dialog.open) dialog.close();
  }

  function afterClose() {
    document.body.classList.remove("lightbox-open");
    if (opener && document.contains(opener)) opener.focus({ preventScroll: true });
    opener = null;
    document.dispatchEvent(new CustomEvent("lightbox:close"));
  }

  window.Lightbox = { open: open, close: close };
})();
