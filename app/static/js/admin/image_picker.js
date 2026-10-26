/* Image picker: drag/drop or browse, client-side validation (incl. file signature), previews. */
(function () {
  "use strict";

  var ALLOWED = {
    jpeg: [".jpg", ".jpeg"],
    png: [".png"],
    webp: [".webp"]
  };

  function extensionOf(name) {
    var i = name.lastIndexOf(".");
    return i === -1 ? "" : name.slice(i).toLowerCase();
  }

  // Mirrors the server's sniffing so users get instant feedback; the server still re-checks.
  function sniff(bytes) {
    if (bytes[0] === 0xff && bytes[1] === 0xd8 && bytes[2] === 0xff) return "jpeg";
    if (bytes[0] === 0x89 && bytes[1] === 0x50 && bytes[2] === 0x4e && bytes[3] === 0x47) return "png";
    if (bytes[0] === 0x52 && bytes[1] === 0x49 && bytes[2] === 0x46 && bytes[3] === 0x46 &&
        bytes[8] === 0x57 && bytes[9] === 0x45 && bytes[10] === 0x42 && bytes[11] === 0x50) return "webp";
    return null;
  }

  async function validate(file, maxBytes) {
    var ext = extensionOf(file.name);
    var allExts = [].concat(ALLOWED.jpeg, ALLOWED.png, ALLOWED.webp);
    if (allExts.indexOf(ext) === -1) return "only JPG, PNG or WEBP images are allowed.";
    if (file.size === 0) return "the file is empty.";
    if (file.size > maxBytes) return "larger than " + Math.round(maxBytes / 1048576) + " MB.";
    var head = new Uint8Array(await file.slice(0, 12).arrayBuffer());
    var kind = sniff(head);
    if (!kind) return "the file content is not a valid image.";
    if (ALLOWED[kind].indexOf(ext) === -1) return "the extension does not match the file content.";
    return null;
  }

  function ImagePicker(root, onChange) {
    this.root = root;
    this.input = root.querySelector(".picker-input");
    this.grid = root.querySelector(".preview-grid");
    this.errors = root.querySelector(".picker-errors");
    this.dropzone = root.querySelector(".dropzone");
    this.maxBytes = parseInt(root.dataset.maxBytes, 10);
    this.maxFiles = parseInt(root.dataset.maxFiles, 10);
    this.items = []; // { file, url }
    this.onChange = onChange || function () {};
    this._bind();
  }

  ImagePicker.prototype._bind = function () {
    var self = this;
    this.input.addEventListener("change", function () {
      self.add(Array.prototype.slice.call(self.input.files));
      self.input.value = ""; // allow re-selecting the same file
    });
    ["dragenter", "dragover"].forEach(function (type) {
      self.dropzone.addEventListener(type, function (e) {
        e.preventDefault();
        self.dropzone.classList.add("is-dragover");
      });
    });
    ["dragleave", "drop"].forEach(function (type) {
      self.dropzone.addEventListener(type, function (e) {
        e.preventDefault();
        self.dropzone.classList.remove("is-dragover");
      });
    });
    this.dropzone.addEventListener("drop", function (e) {
      if (e.dataTransfer && e.dataTransfer.files) self.add(Array.prototype.slice.call(e.dataTransfer.files));
    });
    this.grid.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-remove]");
      if (btn) self.remove(parseInt(btn.dataset.remove, 10));
    });
  };

  ImagePicker.prototype.add = async function (files) {
    var problems = [];
    for (var i = 0; i < files.length; i++) {
      var file = files[i];
      if (this.items.length >= this.maxFiles) {
        problems.push("Only " + this.maxFiles + " images can be uploaded at a time; the rest were skipped.");
        break;
      }
      var duplicate = this.items.some(function (it) {
        return it.file.name === file.name && it.file.size === file.size && it.file.lastModified === file.lastModified;
      });
      if (duplicate) continue;
      var problem = await validate(file, this.maxBytes);
      if (problem) {
        problems.push(file.name + ": " + problem);
        continue;
      }
      this.items.push({ file: file, url: URL.createObjectURL(file) });
    }
    this._renderErrors(problems);
    this.render();
  };

  ImagePicker.prototype.remove = function (index) {
    var item = this.items.splice(index, 1)[0];
    if (item) URL.revokeObjectURL(item.url);
    this.render();
  };

  ImagePicker.prototype.clear = function () {
    this.items.forEach(function (it) { URL.revokeObjectURL(it.url); });
    this.items = [];
    this._renderErrors([]);
    this.render();
  };

  ImagePicker.prototype.files = function () {
    return this.items.map(function (it) { return it.file; });
  };

  ImagePicker.prototype._renderErrors = function (problems) {
    this.errors.textContent = "";
    var self = this;
    problems.forEach(function (msg) {
      var li = document.createElement("li");
      li.textContent = msg;
      self.errors.appendChild(li);
    });
  };

  ImagePicker.prototype.render = function () {
    var grid = this.grid;
    grid.textContent = "";
    this.items.forEach(function (item, index) {
      var li = document.createElement("li");
      li.className = "preview";
      var img = document.createElement("img");
      img.src = item.url;
      img.alt = "";
      var meta = document.createElement("span");
      meta.className = "preview-meta";
      meta.textContent = item.file.name + " · " + window.AdminApi.formatBytes(item.file.size);
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "preview-remove";
      btn.dataset.remove = String(index);
      btn.setAttribute("aria-label", "Remove " + item.file.name);
      btn.textContent = "×";
      li.append(img, meta, btn);
      grid.appendChild(li);
    });
    this.onChange(this.items.length);
  };

  window.ImagePicker = ImagePicker;
})();
