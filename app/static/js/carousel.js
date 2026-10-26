/* Project image carousel: fade/slide transition, arrows, dots, swipe, keyboard,
   autoplay (paused on hover/focus, when off-screen, or with reduced motion), lazy images. */
(function () {
  "use strict";

  var AUTOPLAY_MS = 5000;
  var TRANSITION_MS = 900;
  var SWIPE_PX = 40;
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  function loadImage(slide) {
    if (!slide) return;
    var img = slide.querySelector("img[data-src]");
    if (img) {
      img.src = img.getAttribute("data-src");
      img.removeAttribute("data-src");
    }
  }

  function imageUrl(slide) {
    var img = slide.querySelector("img");
    return img.getAttribute("src") || img.getAttribute("data-src");
  }

  function Carousel(root) {
    this.root = root;
    this.slides = Array.prototype.slice.call(root.querySelectorAll(".carousel-slide"));
    this.dots = Array.prototype.slice.call(root.querySelectorAll(".carousel-dot"));
    this.counter = root.querySelector(".carousel-current");
    this.status = root.querySelector(".carousel-status");
    this.n = this.slides.length;
    this.index = 0;
    this.timer = null;
    this.visible = false;
    this.hovered = false;
    this.focused = false;
    root.classList.add("is-enhanced");
    if (this.n > 1) this._bind();
    this._bindOpen();
    this._observe();
  }

  Carousel.prototype.go = function (target, direction, userAction) {
    var i = (target + this.n) % this.n;
    if (i === this.index) return;
    var prev = this.slides[this.index];
    var next = this.slides[i];
    if (!direction) direction = i > this.index ? "next" : "prev";

    loadImage(next);
    loadImage(this.slides[(i + 1) % this.n]); // preload the following image

    // Set direction first and force a reflow so the incoming slide starts from the correct side.
    this.root.setAttribute("data-dir", direction);
    void next.offsetWidth;

    prev.classList.remove("is-active");
    prev.classList.add("is-leaving");
    next.classList.add("is-active");
    window.setTimeout(function () { prev.classList.remove("is-leaving"); }, TRANSITION_MS);

    this._setA11y(prev, false);
    this._setA11y(next, true);
    if (this.dots.length) {
      this.dots[this.index].classList.remove("is-active");
      this.dots[this.index].removeAttribute("aria-current");
      this.dots[i].classList.add("is-active");
      this.dots[i].setAttribute("aria-current", "true");
    }
    this.index = i;
    if (this.counter) this.counter.textContent = String(i + 1);
    if (userAction) {
      if (this.status) this.status.textContent = "Image " + (i + 1) + " of " + this.n;
      this._schedule();
    }
  };

  Carousel.prototype.next = function (user) { this.go(this.index + 1, "next", user); };
  Carousel.prototype.prev = function (user) { this.go(this.index - 1, "prev", user); };

  Carousel.prototype._setA11y = function (slide, active) {
    var btn = slide.querySelector(".carousel-open");
    if (active) {
      slide.removeAttribute("aria-hidden");
      btn.removeAttribute("tabindex");
    } else {
      slide.setAttribute("aria-hidden", "true");
      btn.setAttribute("tabindex", "-1");
    }
  };

  Carousel.prototype._canAutoplay = function () {
    return this.n > 1 && this.visible && !this.hovered && !this.focused &&
      !document.hidden && !reducedMotion.matches && !document.body.classList.contains("lightbox-open");
  };

  // (Re)start or stop the autoplay timer based on current conditions.
  Carousel.prototype._schedule = function () {
    window.clearTimeout(this.timer);
    this.timer = null;
    if (!this._canAutoplay()) return;
    var self = this;
    this.timer = window.setTimeout(function () {
      self.next(false);
      self._schedule();
    }, AUTOPLAY_MS);
  };

  Carousel.prototype._bind = function () {
    var self = this;
    var root = this.root;
    root.querySelector(".carousel-prev").addEventListener("click", function () { self.prev(true); });
    root.querySelector(".carousel-next").addEventListener("click", function () { self.next(true); });
    this.dots.forEach(function (dot) {
      dot.addEventListener("click", function () {
        self.go(parseInt(dot.getAttribute("data-go"), 10), null, true);
      });
    });

    root.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft") { e.preventDefault(); self.prev(true); }
      else if (e.key === "ArrowRight") { e.preventDefault(); self.next(true); }
    });

    // Only real mouse hovers pause; a tap on a phone would otherwise "hover" forever.
    root.addEventListener("pointerenter", function (e) {
      if (e.pointerType === "mouse") { self.hovered = true; self._schedule(); }
    });
    root.addEventListener("pointerleave", function (e) {
      if (e.pointerType === "mouse") { self.hovered = false; self._schedule(); }
    });
    root.addEventListener("focusin", function () { self.focused = true; self._schedule(); });
    root.addEventListener("focusout", function (e) {
      if (!root.contains(e.relatedTarget)) { self.focused = false; self._schedule(); }
    });
    document.addEventListener("visibilitychange", function () { self._schedule(); });
    document.addEventListener("lightbox:close", function () { self._schedule(); });
    reducedMotion.addEventListener("change", function () { self._schedule(); });

    // Swipe (touch, pen or mouse drag). Vertical scrolling stays native via touch-action: pan-y.
    var viewport = root.querySelector(".carousel-viewport");
    var startX = 0, startY = 0, tracking = false;
    this.suppressClick = false;
    viewport.addEventListener("pointerdown", function (e) {
      if (!e.isPrimary || (e.pointerType === "mouse" && e.button !== 0)) return;
      tracking = true;
      startX = e.clientX;
      startY = e.clientY;
      self.suppressClick = false;
    });
    viewport.addEventListener("pointerup", function (e) {
      if (!tracking) return;
      tracking = false;
      var dx = e.clientX - startX;
      var dy = e.clientY - startY;
      if (Math.abs(dx) > SWIPE_PX && Math.abs(dx) > Math.abs(dy) * 1.2) {
        self.suppressClick = true; // a swipe is not a click on the image
        if (dx < 0) self.next(true); else self.prev(true);
      }
    });
    viewport.addEventListener("pointercancel", function () { tracking = false; });
    viewport.addEventListener("dragstart", function (e) { e.preventDefault(); });
  };

  Carousel.prototype._bindOpen = function () {
    var self = this;
    this.root.addEventListener("click", function (e) {
      var btn = e.target.closest(".carousel-open");
      if (!btn || !window.Lightbox) return;
      if (self.suppressClick) { self.suppressClick = false; return; }
      var title = self.root.closest(".project").querySelector(".project-name").textContent;
      window.Lightbox.open(self.slides.map(imageUrl), self.index, title, btn);
      self._schedule();
    });
  };

  Carousel.prototype._observe = function () {
    var self = this;
    if (!("IntersectionObserver" in window)) {
      this.visible = true;
      loadImage(this.slides[1]);
      this._schedule();
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        self.visible = entry.isIntersecting;
        // Load the next image shortly before the carousel scrolls into view.
        if (entry.isIntersecting) loadImage(self.slides[(self.index + 1) % self.n]);
        self._schedule();
      });
    }, { rootMargin: "200px 0px" });
    io.observe(this.root);
  };

  document.querySelectorAll("[data-carousel]").forEach(function (el) { new Carousel(el); });
})();
