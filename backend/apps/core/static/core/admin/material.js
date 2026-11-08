"use strict";
// Small helpers for the md-* admin pages. Everything works without them; they only add feedback.
(function () {
  function formatSize(bytes) {
    if (bytes < 1024) return bytes + " B";
    if (bytes < 1024 * 1024) return Math.round(bytes / 1024) + " KB";
    return (bytes / (1024 * 1024)).toFixed(1) + " MB";
  }

  // Drop zone: show the chosen file's name and size, and highlight while a file is dragged over.
  function initDropzone(zone) {
    const input = zone.querySelector('input[type="file"]');
    const title = zone.querySelector("[data-file-title]");
    const hint = zone.querySelector("[data-file-hint]");
    if (!input || !title) return;
    const emptyTitle = title.innerHTML;
    const emptyHint = hint ? hint.textContent : "";

    function update() {
      const file = input.files && input.files[0];
      zone.classList.toggle("has-file", Boolean(file));
      if (file) {
        title.textContent = file.name;
        if (hint) hint.textContent = formatSize(file.size) + " · boshqa fayl tanlash uchun bosing";
      } else {
        title.innerHTML = emptyTitle;
        if (hint) hint.textContent = emptyHint;
      }
    }

    input.addEventListener("change", update);
    ["dragenter", "dragover"].forEach(function (type) {
      zone.addEventListener(type, function () {
        zone.classList.add("is-dragging");
      });
    });
    ["dragleave", "drop"].forEach(function (type) {
      zone.addEventListener(type, function () {
        zone.classList.remove("is-dragging");
      });
    });
    update();
  }

  // A long-running submit (file check, promotion, tickets) shows a spinner and can't be clicked
  // twice. The button is not disabled: a disabled button would drop its own name from the POST.
  function initSubmitOnce(form) {
    form.addEventListener("submit", function (event) {
      const button = event.submitter;
      if (form.dataset.submitted) {
        event.preventDefault();
        return;
      }
      form.dataset.submitted = "1";
      if (button && button.classList.contains("md-btn")) button.classList.add("is-loading");
      // A download (CSV) leaves the page open, so let the form be used again after a while.
      window.setTimeout(function () {
        delete form.dataset.submitted;
        if (button) button.classList.remove("is-loading");
      }, 8000);
    });
  }

  // Place pickers that follow each other: once a district is chosen in a form row, that row's
  // school list shows only its schools (and region -> district, school -> class the same way).
  // Django builds every autocomplete through $.fn.djangoAdminSelect2 when the page is ready; this
  // deferred script runs before that, so wrapping it here covers every row, new ones included.
  const PLACES = ["region", "district", "school", "classroom"];
  const $ = window.django && window.django.jQuery;
  if ($ && $.fn.djangoAdminSelect2) {
    $.fn.djangoAdminSelect2 = function () {
      $.each(this, function (i, element) {
        $(element).select2({
          ajax: {
            data: function (params) {
              const field = element.dataset.fieldName;
              const data = {
                term: params.term,
                page: params.page,
                app_label: element.dataset.appLabel,
                model_name: element.dataset.modelName,
                field_name: field,
              };
              const level = PLACES.indexOf(field);
              // "targets-0-school" -> "targets-0-": the wider places of the same row.
              if (level > 0 && element.form && element.name.endsWith(field)) {
                const prefix = element.name.slice(0, -field.length);
                PLACES.slice(0, level).forEach(function (parent) {
                  const input = element.form.elements.namedItem(prefix + parent);
                  if (input && input.value) data[parent] = input.value;
                });
              }
              return data;
            },
          },
        });
      });
      return this;
    };
  }

  // Coming back with the browser's Back button restores the page as it was: clear the spinner.
  window.addEventListener("pageshow", function () {
    document.querySelectorAll("form[data-submitted]").forEach(function (form) {
      delete form.dataset.submitted;
    });
    document.querySelectorAll(".md-btn.is-loading").forEach(function (button) {
      button.classList.remove("is-loading");
    });
  });

  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll("[data-dropzone]").forEach(initDropzone);
    document.querySelectorAll("form[data-submit-once]").forEach(initSubmitOnce);
  });
})();
