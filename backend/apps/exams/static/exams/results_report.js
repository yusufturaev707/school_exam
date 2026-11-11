/*
 * Results report in the admin (apps/exams/templates/admin/exams/examresult/report.html).
 * Draws the charts and the sortable tables from the report data the page carries as JSON,
 * the same data the downloadable files are made from.
 */
(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  var esc = function (value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  };
  var num = function (value) {
    if (value == null) return "—";
    var fixed = Number.isInteger(value) ? String(value) : value.toFixed(1);
    var parts = fixed.split(".");
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return parts.join(",");
  };
  var pct = function (value) {
    return value == null ? "—" : value.toFixed(1).replace(".", ",") + "%";
  };
  var band = function (value) {
    return value >= 80 ? "high" : value >= 50 ? "mid" : "growing";
  };
  var bar = function (value) {
    if (value == null) return "—";
    return (
      '<span class="rr-meter rr-meter--' + band(value) + '"><span style="width:' + Math.max(value, 1.5) +
      '%"></span></span><span class="rr-pct rr-pct--' + band(value) + '">' + pct(value) + "</span>"
    );
  };

  /* ------------------------------------------------------------ sortable, paged table */

  function Table(el, options) {
    this.el = el;
    this.columns = options.columns;
    this.rows = options.rows;
    this.view = this.rows.slice();
    this.sortKey = options.sortKey;
    this.sortDir = options.sortDir || 1;
    this.pageSize = options.pageSize || 0;
    this.page = 0;
    this.onRow = options.onRow;
    this.rowLabel = options.rowLabel;
    this.pager = options.pager;
    this.counter = options.counter;
    this.countText = options.countText;
    this.filterFn = null;
    this.query = "";
    this.searchText = options.searchText;
    this.renderHead();
    this.apply();
  }

  Table.prototype.column = function (key) {
    return this.columns.filter(function (c) { return c.key === key; })[0];
  };

  Table.prototype.renderHead = function () {
    var self = this;
    var head = this.columns
      .map(function (c) {
        return (
          '<th scope="col" class="' + (c.num ? "num" : "") + '" data-key="' + esc(c.key) + '">' +
          '<button type="button" class="rr-sort" title="Saralash">' + esc(c.label) + '<span class="rr-sort__icon" aria-hidden="true"></span></button></th>'
        );
      })
      .join("");
    this.el.innerHTML = "<thead><tr>" + head + "</tr></thead><tbody></tbody>";
    this.body = this.el.tBodies[0];
    this.el.tHead.addEventListener("click", function (event) {
      var th = event.target.closest("th");
      if (!th) return;
      var key = th.getAttribute("data-key");
      if (self.sortKey === key) self.sortDir = -self.sortDir;
      else {
        self.sortKey = key;
        var col = self.column(key);
        self.sortDir = col.firstDir || (col.num ? -1 : 1);
      }
      self.page = 0;
      self.apply();
    });
    if (this.onRow) {
      this.el.classList.add("rr-table--clickable");
      this.body.addEventListener("click", function (event) {
        var tr = event.target.closest("tr[data-index]");
        if (tr) self.onRow(self.view[Number(tr.getAttribute("data-index"))]);
      });
      this.body.addEventListener("keydown", function (event) {
        if (event.key !== "Enter" && event.key !== " ") return;
        var tr = event.target.closest("tr[data-index]");
        if (!tr) return;
        event.preventDefault();
        self.onRow(self.view[Number(tr.getAttribute("data-index"))]);
      });
    }
  };

  Table.prototype.apply = function () {
    var self = this;
    var query = this.query.trim().toLocaleLowerCase();
    this.view = this.rows.filter(function (row) {
      if (self.filterFn && !self.filterFn(row)) return false;
      return !query || self.searchText(row).toLocaleLowerCase().indexOf(query) !== -1;
    });
    var column = this.column(this.sortKey);
    if (column) {
      var value = column.sort || function (row) { return row[column.key]; };
      var dir = this.sortDir;
      this.view.sort(function (a, b) {
        var x = value(a), y = value(b);
        if (x == null && y == null) return 0;
        if (x == null) return 1; // empty values always last
        if (y == null) return -1;
        if (typeof x === "string") return dir * x.localeCompare(y, "uz");
        return dir * (x - y);
      });
    }
    Array.prototype.forEach.call(this.el.tHead.rows[0].cells, function (th) {
      var key = th.getAttribute("data-key");
      th.setAttribute("aria-sort", key === self.sortKey ? (self.sortDir > 0 ? "ascending" : "descending") : "none");
    });
    this.render();
  };

  Table.prototype.render = function () {
    var self = this;
    var pages = this.pageSize ? Math.max(1, Math.ceil(this.view.length / this.pageSize)) : 1;
    this.page = Math.min(this.page, pages - 1);
    var start = this.pageSize ? this.page * this.pageSize : 0;
    var end = this.pageSize ? start + this.pageSize : this.view.length;
    var html = "";
    for (var i = start; i < Math.min(end, this.view.length); i++) {
      var row = this.view[i];
      html += '<tr data-index="' + i + '"' + (this.onRow ? ' tabindex="0" title="' + esc(this.rowLabel(row)) + '"' : "") + ">";
      for (var c = 0; c < this.columns.length; c++) {
        var col = this.columns[c];
        html += '<td class="' + (col.num ? "num " : "") + (col.cls || "") + '">' + (col.render ? col.render(row) : esc(row[col.key])) + "</td>";
      }
      html += "</tr>";
    }
    if (!this.view.length) {
      html = '<tr><td colspan="' + this.columns.length + '" class="rr-empty">Hech narsa topilmadi.</td></tr>';
    }
    this.body.innerHTML = html;
    if (this.counter) this.counter.textContent = this.countText(this.view.length, this.rows.length);
    if (this.pager) this.renderPager(pages, start, end);
  };

  Table.prototype.renderPager = function (pages, start, end) {
    var self = this;
    if (pages <= 1) {
      this.pager.hidden = true;
      return;
    }
    this.pager.hidden = false;
    this.pager.innerHTML =
      '<button type="button" class="rr-page-btn" data-step="-1"' + (this.page === 0 ? " disabled" : "") + ">‹ Oldingi</button>" +
      "<span>" + (start + 1) + "–" + Math.min(end, this.view.length) + " / " + this.view.length + " · " + (this.page + 1) + "-sahifa (" + pages + " dan)</span>" +
      '<button type="button" class="rr-page-btn" data-step="1"' + (this.page >= pages - 1 ? " disabled" : "") + ">Keyingi ›</button>";
    this.pager.onclick = function (event) {
      var button = event.target.closest("button[data-step]");
      if (!button) return;
      self.page += Number(button.getAttribute("data-step"));
      self.render();
      self.el.closest(".md-table-scroll").scrollTop = 0;
    };
  };

  /* ------------------------------------------------------------------------- the page */

  ready(function () {
    var dataNode = document.getElementById("rr-data");
    if (!dataNode) return;
    var report = JSON.parse(dataNode.textContent);
    var drill = JSON.parse(document.getElementById("rr-drill").textContent);

    document.querySelectorAll("[data-stat]").forEach(function (el) {
      var value = report.summary[el.getAttribute("data-stat")];
      el.textContent = el.getAttribute("data-kind") === "pct" ? pct(value) : num(value);
    });

    document.querySelectorAll("[data-download]").forEach(function (link) {
      link.addEventListener("click", function () {
        link.classList.add("is-busy");
        setTimeout(function () { link.classList.remove("is-busy"); }, 4000);
      });
    });

    if (!report.summary.count) return;

    /* pupils first: the charts filter it */
    var subjectColumns = report.subjectColumns.map(function (s) {
      return {
        key: "s_" + s.code, label: s.name, num: true,
        sort: function (row) { return row.subjects[s.code]; },
        render: function (row) {
          var v = row.subjects[s.code];
          return v == null ? "—" : '<span class="rr-pct rr-pct--' + band(v) + '">' + pct(v) + "</span>";
        },
      };
    });
    var pupils = new Table(document.getElementById("rr-pupils"), {
      rows: report.pupils,
      sortKey: "rank",
      sortDir: 1,
      pageSize: 50,
      pager: document.getElementById("rr-pager"),
      counter: document.getElementById("rr-pupils-count"),
      countText: function (shown, all) {
        return shown === all ? all + " ta o‘quvchi" : shown + " ta ko‘rsatilmoqda (" + all + " tadan)";
      },
      searchText: function (row) { return row.name + " " + row.school + " " + row.classroom + " " + row.district; },
      columns: [
        { key: "rank", label: "O‘rin", num: true },
        { key: "name", label: "F.I.Sh.", cls: "rr-strong" },
        { key: "school", label: "Maktab", render: function (r) { return esc(r.school) + '<small class="rr-sub">' + esc(r.district) + "</small>"; } },
        { key: "classroom", label: "Sinf" },
        { key: "correct", label: "To‘g‘ri", num: true, render: function (r) { return r.correct + '<small class="rr-sub">' + r.incorrect + " xato · " + r.unanswered + " javobsiz</small>"; } },
        { key: "score", label: "Ball", num: true, render: function (r) { return "<b>" + r.score + "</b>/" + r.maxScore; } },
        { key: "percent", label: "Foiz", num: true, cls: "rr-meter-cell", render: function (r) { return bar(r.percent); } },
      ].concat(subjectColumns, [
        { key: "durationMinutes", label: "Vaqt (daq.)", num: true, render: function (r) { return num(r.durationMinutes); } },
        { key: "finishReason", label: "Yakunlash", render: function (r) { return '<span class="rr-tag">' + esc(r.finishReason) + "</span>"; } },
      ]),
    });

    var activeFilter = document.getElementById("rr-active-filter");
    var activeKey = null;
    function setFilter(key, label, fn) {
      if (activeKey === key) key = null;
      activeKey = key;
      pupils.filterFn = key ? fn : null;
      pupils.page = 0;
      pupils.apply();
      document.querySelectorAll("[data-filter]").forEach(function (el) {
        el.setAttribute("aria-pressed", el.getAttribute("data-filter") === key ? "true" : "false");
      });
      activeFilter.hidden = !key;
      activeFilter.innerHTML = key ? esc(label) + ' <button type="button" class="rr-chip-x" aria-label="Filtrni olib tashlash">×</button>' : "";
      if (key) document.getElementById("rr-pupils").closest("section").scrollIntoView({ behavior: "smooth", block: "start" });
    }
    activeFilter.addEventListener("click", function (event) {
      if (event.target.closest(".rr-chip-x")) setFilter(activeKey);
    });

    var search = document.getElementById("rr-search");
    var timer;
    search.addEventListener("input", function () {
      clearTimeout(timer);
      timer = setTimeout(function () {
        pupils.query = search.value;
        pupils.page = 0;
        pupils.apply();
      }, 150);
    });

    /* histogram */
    var histogram = document.getElementById("rr-histogram");
    var top = Math.max.apply(null, report.distribution.map(function (b) { return b.count; }).concat([1]));
    histogram.innerHTML = report.distribution
      .map(function (b) {
        var key = "bucket:" + b.from;
        return (
          '<button type="button" class="rr-col" role="listitem" data-filter="' + key + '" aria-pressed="false" ' +
          'aria-label="' + b.label + "%: " + b.count + ' ta o‘quvchi" title="' + b.label + "%: " + b.count + ' ta o‘quvchi">' +
          '<span class="rr-col__track" style="--h:' + (b.count / top) * 100 + '%">' +
          '<span class="rr-col__bar rr-col__bar--' + band(b.from) + '"></span>' +
          '<span class="rr-col__count">' + b.count + "</span></span>" +
          '<span class="rr-col__label">' + b.label + "</span></button>"
        );
      })
      .join("");
    histogram.addEventListener("click", function (event) {
      var button = event.target.closest("[data-filter]");
      if (!button) return;
      var b = report.distribution.filter(function (x) { return "bucket:" + x.from === button.getAttribute("data-filter"); })[0];
      setFilter("bucket:" + b.from, "Natija " + b.label + "%", function (row) {
        return row.percent >= b.from && (b.to === 100 ? row.percent <= 100 : row.percent < b.to + 1);
      });
    });

    /* bands and subjects */
    var total = report.summary.count;
    var bands = document.getElementById("rr-bands");
    bands.innerHTML = report.bands
      .map(function (b) {
        var share = (b.count / total) * 100;
        return (
          '<button type="button" class="rr-hbar" data-filter="band:' + b.code + '" aria-pressed="false">' +
          '<span class="rr-hbar__label">' + esc(b.label) + " <small>" + esc(b.range) + "</small></span>" +
          '<span class="rr-hbar__value">' + b.count + " <small>(" + pct(share) + ")</small></span>" +
          '<span class="rr-meter rr-meter--wide rr-meter--' + b.code + '"><span style="width:' + share + '%"></span></span></button>'
        );
      })
      .join("");
    bands.addEventListener("click", function (event) {
      var button = event.target.closest("[data-filter]");
      if (!button) return;
      var code = button.getAttribute("data-filter").slice(5);
      var b = report.bands.filter(function (x) { return x.code === code; })[0];
      setFilter("band:" + code, b.label + " (" + b.range + ")", function (row) { return row.band === code; });
    });
    document.getElementById("rr-subjects").innerHTML = report.subjects
      .map(function (s) {
        var v = s.averagePercent || 0;
        return (
          '<div class="rr-hbar rr-hbar--static" title="' + s.correct + " to‘g‘ri, " + s.incorrect + " xato, " + s.unanswered + ' javobsiz">' +
          '<span class="rr-hbar__label">' + esc(s.name) + "</span>" +
          '<span class="rr-hbar__value rr-pct--' + band(v) + '">' + pct(s.averagePercent) + "</span>" +
          '<span class="rr-meter rr-meter--wide rr-meter--' + band(v) + '"><span style="width:' + v + '%"></span></span></div>'
        );
      })
      .join("");

    /* places */
    var groupsEl = document.getElementById("rr-groups");
    if (groupsEl && report.groups) {
      new Table(groupsEl, {
        rows: report.groups.rows,
        sortKey: "averagePercent",
        sortDir: -1,
        rowLabel: function (row) { return row.name + ": batafsil"; },
        onRow: function (row) {
          var query = drill[String(row.id)];
          if (query) window.location.href = window.location.pathname + query;
        },
        searchText: function (row) { return row.name; },
        columns: [
          { key: "name", label: report.groups.label, cls: "rr-strong", render: function (r) { return esc(r.name) + ' <span class="rr-go" aria-hidden="true">›</span>'; } },
          { key: "count", label: "O‘quvchilar", num: true },
          { key: "averagePercent", label: "O‘rtacha", num: true, cls: "rr-meter-cell", render: function (r) { return bar(r.averagePercent); } },
          { key: "maxPercent", label: "Eng yuqori", num: true, render: function (r) { return pct(r.maxPercent); } },
          { key: "minPercent", label: "Eng past", num: true, render: function (r) { return pct(r.minPercent); } },
          { key: "averageScore", label: "O‘rtacha ball", num: true, render: function (r) { return num(r.averageScore); } },
          { key: "high", label: "A’lo (80%+)", num: true },
        ],
      });
    }

    /* questions */
    new Table(document.getElementById("rr-questions"), {
      rows: report.questions,
      sortKey: "number",
      sortDir: 1,
      searchText: function () { return ""; },
      columns: [
        { key: "number", label: "№", num: true },
        { key: "subjectName", label: "Fan" },
        { key: "difficulty", label: "Qiyinlik", render: function (r) { return esc(r.difficulty || "—"); } },
        // First click: the hardest question on top.
        { key: "correctPercent", label: "To‘g‘ri", num: true, firstDir: 1, cls: "rr-meter-cell", render: function (r) { return bar(r.correctPercent); } },
        { key: "incorrect", label: "Xato", num: true },
        { key: "unanswered", label: "Javobsiz", num: true },
        {
          key: "options", label: "Kim qaysi variantni tanladi", sort: function (r) { return r.correctPercent; },
          render: function (r) {
            var wrong = r.options.filter(function (o) { return !o.isCorrect; });
            var trap = wrong.reduce(function (best, o) { return o.count > (best ? best.count : 0) ? o : best; }, null);
            var answered = r.correct + r.incorrect;
            return '<span class="rr-options">' + r.options
              .map(function (o) {
                var share = answered ? Math.round((o.count / answered) * 100) : 0;
                var kind = o.isCorrect ? " rr-option--correct" : trap === o && o.count > r.correct ? " rr-option--trap" : "";
                var hint = o.isCorrect ? "to‘g‘ri javob" : kind ? "ko‘pchilik shu xato javobni tanlagan" : "";
                return '<span class="rr-option' + kind + '" title="' + o.label + ": " + o.count + " ta (" + share + "%)" + (hint ? ", " + hint : "") + '"><b>' + esc(o.label) + "</b> " + o.count + "</span>";
              })
              .join("") + "</span>";
          },
        },
      ],
    });
  });
})();
