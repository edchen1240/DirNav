// DirNav client app. Renders the grouped grid, attribute chips, the dim
// toggle, and the fuzzy item finder from window.DIRNAV_DATA (injected by
// generate.ts). All open actions go through the kickoff:// protocol.
(function () {
  "use strict";

  var data = window.DIRNAV_DATA || { attributePool: [], statusPool: [], projects: [] };
  var pool = data.attributePool;
  var projects = data.projects;
  var statusByValue = {};
  data.statusPool.forEach(function (s) { statusByValue[s.value] = s; });

  // Attribute colors live in style.css :root as --attr-<name>. This returns a
  // reference to that var, so colors are defined in one place (the CSS).
  function colorFor(a) { return "var(--attr-" + a + ", #888888)"; }

  var app = document.getElementById("app");
  var chipsEl = document.getElementById("dn-chips");
  var searchEl = document.getElementById("dn-search");
  var finderEl = document.getElementById("dn-finder");
  var hideDimEl = document.getElementById("dn-hide-dim");
  var resetEl = document.getElementById("dn-reset");

  var selectedChips = new Set();
  var hideDim = false;

  // ---------- helpers ----------
  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function primary(p) { return p.attributes[0] || "other"; }
  function isParked(p) { return p.priority === null || p.priority < 2; }
  function isDim(p) { var s = statusByValue[p.status]; return !!(s && s.dim); }
  function pr(p) { return p.priority === null ? -1 : p.priority; }
  function baseName(path) {
    var parts = String(path).replace(/[\\/]+$/, "").split(/[\\/]/);
    return parts[parts.length - 1] || path;
  }
  function urlLabel(u) {
    try { var x = new URL(u); return x.hostname + (x.pathname !== "/" ? x.pathname : ""); }
    catch (e) { return u; }
  }
  function kickoffUrl(slug, items) {
    return "kickoff://" + encodeURIComponent(slug) + (items && items.length ? "?items=" + items.join(",") : "");
  }
  function go(url) { window.location.href = url; }

  // ---------- card ----------
  function itemsHtml(slug, arr, kind, labelFn) {
    if (!arr.length) return '<div class="dn-empty">none</div>';
    return arr.map(function (path, i) {
      var ref = kind + i;
      // Web URLs open directly in a new browser tab, skipping kickoff.ps1.
      var link = (kind === "u" && /^https?:\/\//i.test(path))
        ? '<a class="dn-link" href="' + esc(path) + '" target="_blank" rel="noopener noreferrer" title="' + esc(path) + '">' + esc(labelFn(path)) + "</a>"
        : '<a class="dn-link" data-act="item" data-slug="' + esc(slug) + '" data-ref="' + ref + '" title="' + esc(path) + '">' + esc(labelFn(path)) + "</a>";
      return '<div class="dn-item"><input type="checkbox" class="dn-chk" data-ref="' + ref + '" checked>' + link + "</div>";
    }).join("");
  }
  function section(title, inner) {
    return '<div class="dn-sec"><div class="dn-sec-h">' + title + "</div>" + inner + "</div>";
  }
  function cardHtml(p) {
    var sm = statusByValue[p.status] || { label: p.status };
    var dimClass = isDim(p) ? " dn-dim" : "";
    var tags = p.attributes.map(function (a) {
      return '<span class="dn-tag" style="--tag:' + colorFor(a) + '; --tag-font: var(--attr-' + esc(a) + '-font, var(--attr-font-general))">' + esc(a) + "</span>";
    }).join(" ");
    // Wrap each date in a span so CSS can accent lastWorkDate.
    var dates = [
      '<span class="dn-date" title="start">' + esc(p.startDate || "-") + "</span>",
      '<span class="dn-date" title="P00 init">' + esc(p.p00InitiationDate || "-") + "</span>",
      '<span class="dn-date dn-date-last" title="last work">' + esc(p.lastWorkDate || "-") + "</span>"
    ].join(" | ");
    var related = p.related.length
      ? '<div class="dn-related">related: ' + p.related.map(function (r) {
          return '<a data-act="related" data-slug="' + esc(r) + '">' + esc(r) + "</a>";
        }).join(" ") + "</div>"
      : "";
    return '<article class="dn-card' + dimClass + '" id="card-' + esc(p.projectSlug) + '">' +
      '<h3 class="dn-name">' + esc(p.projectName) + "</h3>" +
      '<div class="dn-tags">' + tags + "</div>" +
      '<div class="dn-meta">' + esc(p.projectSlug) +
        ' | <span class="dn-pri">' + (p.priority === null ? "-" : p.priority) + "</span>" +
        ' | <span class="dn-status">' + esc(sm.label) + "</span></div>" +
      '<div class="dn-dates">' + dates + "</div>" +
      '<div class="dn-actions">' +
        '<button data-act="kickoff" data-slug="' + esc(p.projectSlug) + '">Kickoff</button>' +
        '<button data-act="p00" data-slug="' + esc(p.projectSlug) + '" title="Click: open P00 in VSCode. Ctrl+click: open the P00 folder.">Open P00</button>' +
      "</div>" +
      section("Folders", itemsHtml(p.projectSlug, p.folders, "d", baseName)) +
      section("URLs", itemsHtml(p.projectSlug, p.urls, "u", urlLabel)) +
      section("Files", itemsHtml(p.projectSlug, p.files, "f", baseName)) +
      related +
      "</article>";
  }

  // ---------- grouping ----------
  function buildGroups(list) {
    var groups = new Map();
    list.forEach(function (p) {
      var a = primary(p);
      if (!groups.has(a)) groups.set(a, []);
      groups.get(a).push(p);
    });
    groups.forEach(function (arr) { arr.sort(function (x, y) { return pr(y) - pr(x); }); });
    return Array.from(groups.entries()).sort(function (g1, g2) {
      var m1 = Math.max.apply(null, g1[1].map(pr));
      var m2 = Math.max.apply(null, g2[1].map(pr));
      return m2 - m1;
    });
  }
  function passesChips(p) {
    if (selectedChips.size === 0) return true;
    return p.attributes.some(function (a) { return selectedChips.has(a); });
  }
  function passesDim(p) { return !(hideDim && isDim(p)); }

  // ---------- render ----------
  function groupSection(heading, headingColor, cards, extraClass) {
    var sec = document.createElement("section");
    sec.className = "dn-group" + (extraClass || "");
    var hStyle = headingColor ? ' style="--tag:' + headingColor + '"' : "";
    sec.innerHTML = '<h2 class="dn-group-h"' + hStyle + ">" + esc(heading) + "</h2>" +
      '<div class="dn-grid">' + cards.map(cardHtml).join("") + "</div>";
    app.appendChild(sec);
  }
  function render(animateCards) {
    app.innerHTML = "";
    var visible = projects.filter(function (p) { return passesChips(p) && passesDim(p); });
    var active = visible.filter(function (p) { return !isParked(p); });
    var parked = visible.filter(isParked).sort(function (x, y) { return pr(y) - pr(x); });
    buildGroups(active).forEach(function (g) { groupSection(g[0], colorFor(g[0]), g[1]); });
    if (parked.length) groupSection("Low priority / parked", "", parked, " dn-parked");
    if (!active.length && !parked.length) app.innerHTML = '<div class="dn-empty">no projects match the current filter</div>';
    if (animateCards) {
      Array.prototype.forEach.call(app.querySelectorAll(".dn-card"), function (card, i) {
        card.style.animationDelay = Math.min(i, 10) * 18 + "ms";
        card.classList.add("dn-filter-enter");
      });
    }
  }

  // ---------- chips ----------
  chipsEl.innerHTML = pool.map(function (a) {
    return '<button class="dn-chip" data-chip="' + esc(a) + '" style="--tag:' + colorFor(a) + '; --tag-font: var(--attr-' + esc(a) + '-font, var(--attr-font-general))">' + esc(a) + "</button>";
  }).join("");
  chipsEl.addEventListener("click", function (e) {
    var c = e.target.closest("[data-chip]");
    if (!c) return;
    var a = c.dataset.chip;
    if (selectedChips.has(a)) { selectedChips.delete(a); c.classList.remove("on"); }
    else { selectedChips.add(a); c.classList.add("on"); }
    c.classList.remove("dn-chip-pop");
    void c.offsetWidth;
    c.classList.add("dn-chip-pop");
    c.addEventListener("animationend", function () { c.classList.remove("dn-chip-pop"); }, { once: true });
    render(true);
  });
  hideDimEl.addEventListener("change", function () { hideDim = hideDimEl.checked; render(); });
  resetEl.addEventListener("click", function () {
    selectedChips.clear();
    Array.prototype.forEach.call(chipsEl.querySelectorAll(".on"), function (c) { c.classList.remove("on"); });
    searchEl.value = ""; runFinder("");
    hideDim = false; hideDimEl.checked = false;
    render(); // rebuilds the cards, so every checkbox returns to checked
  });

  // ---------- finder ----------
  var STOP = new Set(["of", "the", "a", "an", "in", "on", "to", "for", "and", "or"]);
  function tokens(q) { return q.toLowerCase().split(/\s+/).filter(function (t) { return t && !STOP.has(t); }); }
  var ITEMS = [];
  projects.forEach(function (p) {
    p.folders.forEach(function (path, i) { ITEMS.push({ slug: p.projectSlug, ref: "d" + i, kind: "folder", path: path, name: p.projectName }); });
    p.urls.forEach(function (path, i) { ITEMS.push({ slug: p.projectSlug, ref: "u" + i, kind: "url", path: path, name: p.projectName }); });
    p.files.forEach(function (path, i) { ITEMS.push({ slug: p.projectSlug, ref: "f" + i, kind: "file", path: path, name: p.projectName }); });
    if (p.p00) ITEMS.push({ slug: p.projectSlug, ref: "p", kind: "p00", path: p.p00, name: p.projectName });
  });
  function runFinder(q) {
    var toks = tokens(q);
    if (!toks.length) { finderEl.hidden = true; finderEl.innerHTML = ""; return; }
    var hits = ITEMS.filter(function (it) {
      var hay = (it.path + " " + it.name + " " + it.slug).toLowerCase();
      return toks.every(function (t) { return hay.indexOf(t) !== -1; });
    }).slice(0, 40);
    finderEl.hidden = false;
    finderEl.innerHTML = hits.length
      ? hits.map(function (it) {
          // Web URLs open directly in a new tab; other items route through kickoff.ps1.
          var attrs = (it.kind === "url" && /^https?:\/\//i.test(it.path))
            ? 'href="' + esc(it.path) + '" target="_blank" rel="noopener noreferrer"'
            : 'data-act="item" data-slug="' + esc(it.slug) + '" data-ref="' + it.ref + '"';
          return '<a class="dn-result" ' + attrs + ' title="' + esc(it.path) + '">' +
            '<span class="dn-result-kind">' + it.kind + "</span>" +
            '<span class="dn-result-name">' + esc(it.name) + "</span>" +
            '<span class="dn-result-path">' + esc(it.path) + "</span></a>";
        }).join("")
      : '<div class="dn-empty">no matches</div>';
  }
  searchEl.addEventListener("input", function () { runFinder(searchEl.value); });

  // ---------- jump to related ----------
  function jumpTo(slug) {
    selectedChips.clear();
    Array.prototype.forEach.call(chipsEl.querySelectorAll(".on"), function (c) { c.classList.remove("on"); });
    hideDim = false; hideDimEl.checked = false;
    render();
    var el = document.getElementById("card-" + slug);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add("dn-flash");
      setTimeout(function () { el.classList.remove("dn-flash"); }, 1500);
    }
  }

  // ---------- one delegated click handler ----------
  document.addEventListener("click", function (e) {
    var t = e.target.closest("[data-act]");
    if (!t) return;
    var act = t.dataset.act;
    var slug = t.dataset.slug;
    if (act === "kickoff") {
      var kcard = document.getElementById("card-" + slug);
      var allBoxes = kcard.querySelectorAll(".dn-chk");
      var checked = Array.prototype.filter.call(allBoxes, function (c) { return c.checked; })
        .map(function (c) { return c.dataset.ref; });
      if (!checked.length) return;                                  // nothing selected: do nothing
      if (checked.length === allBoxes.length) go(kickoffUrl(slug)); // all checked: full kickoff (folders open as tabs)
      else go(kickoffUrl(slug, checked));                           // subset: open just the checked items
    }
    else if (act === "p00") go(kickoffUrl(slug, [e.ctrlKey ? "pd" : "p"]));
    else if (act === "item") { e.preventDefault(); go(kickoffUrl(slug, [t.dataset.ref])); }
    else if (act === "related") { e.preventDefault(); jumpTo(slug); }
  });

  render();
})();
