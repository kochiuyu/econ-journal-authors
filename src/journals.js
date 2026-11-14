/* Sort the journals index. Row order is read from data-* attributes
   written by scripts/build_site.py. No extra records are loaded. */
(function () {
  "use strict";

  var table = document.getElementById("journal-table");
  var keySel = document.getElementById("journal-sort");
  var dirBtn = document.getElementById("journal-sort-dir");
  var status = document.getElementById("journal-sort-status");
  if (!table || !keySel || !dirBtn) return;

  var tbody = table.querySelector("tbody");
  var headers = table.querySelectorAll("thead button[data-sort]");
  var countKeys = {
    "journal-years": 1, issues: 1, items: 1, research: 1, other: 1,
    doi: 1, "item-names": 1, "research-names": 1
  };
  var numericKeys = { years: 1 };
  Object.keys(countKeys).forEach(function (k) { numericKeys[k] = 1; });
  var labels = {
    name: "journal name",
    publisher: "publisher",
    years: "years covered",
    "journal-years": "journal-years",
    issues: "issues",
    items: "items",
    research: "research articles",
    other: "other items",
    doi: "items with a DOI",
    "item-names": "items with names",
    "research-names": "research articles with names"
  };
  var state = { key: "name", dir: "asc" };

  function dirPhrase() {
    if (state.key === "name" || state.key === "publisher") {
      return state.dir === "asc" ? "A to Z" : "Z to A";
    }
    if (state.key === "years") {
      return state.dir === "asc" ? "Earliest first" : "Latest first";
    }
    return state.dir === "asc" ? "Smallest first" : "Largest first";
  }

  function defaultDir(key) {
    return countKeys[key] ? "desc" : "asc";
  }

  function compare(a, b) {
    var va = a.getAttribute("data-" + state.key) || "";
    var vb = b.getAttribute("data-" + state.key) || "";
    var c;
    if (numericKeys[state.key]) {
      c = Number(va) - Number(vb);
      if (isNaN(c)) c = 0;
    } else {
      c = va < vb ? -1 : va > vb ? 1 : 0;
    }
    if (state.dir === "desc") c = -c;
    if (c) return c;
    var na = a.getAttribute("data-name") || "";
    var nb = b.getAttribute("data-name") || "";
    return na < nb ? -1 : na > nb ? 1 : 0;
  }

  function apply() {
    var rows = Array.prototype.slice.call(tbody.querySelectorAll("tr"));
    rows.sort(compare);
    rows.forEach(function (tr) { tbody.appendChild(tr); });
    Array.prototype.forEach.call(headers, function (btn) {
      var on = btn.getAttribute("data-sort") === state.key;
      var th = btn.closest("th");
      btn.setAttribute("aria-pressed", on ? "true" : "false");
      if (on) th.setAttribute("aria-sort", state.dir === "asc" ? "ascending" : "descending");
      else th.removeAttribute("aria-sort");
    });
    keySel.value = state.key;
    var phrase = dirPhrase();
    var sentence = (state.key === "name" || state.key === "publisher")
      ? phrase
      : phrase.charAt(0).toLowerCase() + phrase.slice(1);
    dirBtn.textContent = phrase;
    dirBtn.setAttribute("aria-label", "Reverse sort direction. Currently " + phrase + ".");
    if (status) status.textContent = "Sorted by " + (labels[state.key] || state.key) + ", " + sentence + ".";
  }

  function syncHeaderTab() {
    var narrow = window.matchMedia("(max-width: 720px)").matches;
    Array.prototype.forEach.call(headers, function (btn) {
      if (narrow) btn.setAttribute("tabindex", "-1");
      else btn.removeAttribute("tabindex");
    });
  }

  Array.prototype.forEach.call(headers, function (btn) {
    btn.addEventListener("click", function () {
      var key = btn.getAttribute("data-sort");
      if (state.key === key) state.dir = state.dir === "asc" ? "desc" : "asc";
      else {
        state.key = key;
        state.dir = defaultDir(key);
      }
      apply();
    });
  });
  keySel.addEventListener("change", function () {
    state.key = keySel.value;
    state.dir = defaultDir(state.key);
    apply();
  });
  dirBtn.addEventListener("click", function () {
    state.dir = state.dir === "asc" ? "desc" : "asc";
    apply();
  });
  var mq = window.matchMedia("(max-width: 720px)");
  if (mq.addEventListener) mq.addEventListener("change", syncHeaderTab);
  else if (mq.addListener) mq.addListener(syncHeaderTab);
  syncHeaderTab();
  apply();
})();
