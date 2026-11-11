/* Journal Articles catalog browser.
   Loads data/journals.json (small index), then only the shard for the selected
   journal: data/journals/{slug}.json. All paths are relative. */
(function () {
  "use strict";

  var TYPE_LABEL = { a: "Research article", o: "Other", p: "Proceedings" };
  var TYPE_CLASS = { a: "t-article", o: "t-other", p: "t-proceedings" };
  var SRC_LABEL = { s: "as printed in the TOC", o: "OpenAlex (name only)" };
  var SRC_TITLE = {
    s: "Author names as printed in the publisher table of contents.",
    o: "Author names from OpenAlex, recorded as names only. Not a person registry."
  };
  var PAGE = 250;

  var els = {
    journal: document.getElementById("f-journal"),
    year: document.getElementById("f-year"),
    issue: document.getElementById("f-issue"),
    q: document.getElementById("f-q"),
    types: document.getElementById("f-type"),
    reset: document.getElementById("f-reset"),
    crumbs: document.getElementById("crumbs"),
    heading: document.getElementById("results-title"),
    count: document.getElementById("count"),
    results: document.getElementById("results")
  };

  var index = null;          // journals.json
  var bySlug = {};
  var shards = {};           // slug -> shard
  var limit = PAGE;
  var state = readState();

  function readState() {
    var p = new URLSearchParams(location.search);
    var t = p.get("type");
    return {
      journal: p.get("journal") || "",
      year: p.get("year") || "",
      volume: p.get("volume") || "",
      issue: p.get("issue") || "",
      type: (t === "all" || t === "other" || t === "research") ? t : "research",
      q: p.get("q") || ""
    };
  }

  function buildQuery(s) {
    var p = new URLSearchParams();
    if (s.journal) p.set("journal", s.journal);
    if (s.journal && s.year) p.set("year", s.year);
    if (s.journal && s.year && s.issue) { p.set("volume", s.volume); p.set("issue", s.issue); }
    if (s.type !== "research") p.set("type", s.type);
    if (s.q) p.set("q", s.q);
    var str = p.toString();
    return "catalog.html" + (str ? "?" + str : "");
  }

  function commit(push) {
    var url = buildQuery(state);
    if (push) history.pushState(null, "", url); else history.replaceState(null, "", url);
    limit = PAGE;
    render();
  }

  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    if (attrs) for (var k in attrs) {
      if (attrs[k] == null || attrs[k] === false) continue;
      if (k === "text") n.textContent = attrs[k];
      else if (k === "class") n.className = attrs[k];
      else n.setAttribute(k, attrs[k]);
    }
    (kids || []).forEach(function (c) {
      if (c == null) return;
      n.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return n;
  }

  function fmt(n) { return Number(n).toLocaleString("en-US"); }

  function fold(s) {
    return (s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
  }

  function issueLabel(vol, iss) {
    return "Vol. " + vol + ", Issue " + iss;
  }

  function loadIndex() {
    return fetch("data/journals.json").then(function (r) {
      if (!r.ok) throw new Error("journals.json " + r.status);
      return r.json();
    });
  }

  function loadShard(slug) {
    if (shards[slug]) return Promise.resolve(shards[slug]);
    return fetch("data/journals/" + encodeURIComponent(slug) + ".json").then(function (r) {
      if (!r.ok) throw new Error(slug + ".json " + r.status);
      return r.json();
    }).then(function (d) {
      // Precompute search text once per shard.
      d.items.forEach(function (it) { it.push(fold(it[1] + " " + it[5])); });
      shards[slug] = d;
      return d;
    });
  }

  function fillJournalSelect() {
    els.journal.innerHTML = "";
    els.journal.appendChild(el("option", { value: "", text: "Choose a journal…" }));
    index.journals.forEach(function (j) {
      els.journal.appendChild(el("option", { value: j.slug, text: j.name }));
    });
  }

  function fillYearIssue(shard) {
    els.year.innerHTML = "";
    els.issue.innerHTML = "";
    if (!shard) {
      els.year.appendChild(el("option", { value: "", text: "All years" }));
      els.issue.appendChild(el("option", { value: "", text: "All issues" }));
      els.year.disabled = true; els.issue.disabled = true;
      return;
    }
    els.year.disabled = false;
    els.year.appendChild(el("option", { value: "", text: "All years" }));
    var years = [];
    shard.issues.forEach(function (i) { if (years.indexOf(i[0]) < 0) years.push(i[0]); });
    years.forEach(function (y) { els.year.appendChild(el("option", { value: y, text: y })); });
    els.year.value = state.year;
    els.issue.appendChild(el("option", { value: "", text: "All issues" }));
    if (state.year) {
      shard.issues.forEach(function (i) {
        if (i[0] !== state.year) return;
        els.issue.appendChild(el("option", { value: i[1] + "|" + i[2], text: issueLabel(i[1], i[2]) }));
      });
      els.issue.disabled = false;
      els.issue.value = state.issue ? state.volume + "|" + state.issue : "";
    } else {
      els.issue.disabled = true;
    }
  }

  function syncControls() {
    els.journal.value = state.journal;
    els.q.value = state.q;
    Array.prototype.forEach.call(els.types.querySelectorAll("button"), function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-type") === state.type ? "true" : "false");
    });
  }

  function setTypeCounts(counts) {
    Array.prototype.forEach.call(els.types.querySelectorAll("button"), function (b) {
      var c = b.querySelector(".c");
      var t = b.getAttribute("data-type");
      c.textContent = counts ? fmt(counts[t]) : "";
    });
  }

  function crumbs(j) {
    els.crumbs.innerHTML = "";
    var parts = [el("a", { href: "catalog.html", text: "All journals" })];
    if (j) {
      parts.push(" › ");
      parts.push(state.year ? el("a", { href: buildQuery({ journal: j.slug, year: "", issue: "", volume: "", type: state.type, q: "" }), text: j.name }) : el("span", { text: j.name }));
      if (state.year) {
        parts.push(" › ");
        parts.push(state.issue ? el("a", { href: buildQuery({ journal: j.slug, year: state.year, issue: "", volume: "", type: state.type, q: "" }), text: state.year }) : el("span", { text: state.year }));
        if (state.issue) { parts.push(" › "); parts.push(el("span", { text: issueLabel(state.volume, state.issue) })); }
      }
    }
    parts.forEach(function (p) { els.crumbs.appendChild(typeof p === "string" ? document.createTextNode(p) : p); });
  }

  function renderJournalList() {
    els.heading.textContent = "Choose a journal";
    document.title = "Catalog — Journal Articles";
    setTypeCounts(null);
    els.count.textContent = fmt(index.journals.length) + " journals. Pick one to load its table of contents.";
    var tbody = el("tbody");
    index.journals.forEach(function (j) {
      tbody.appendChild(el("tr", null, [
        el("td", null, [el("a", { class: "jname", href: buildQuery({ journal: j.slug, year: "", issue: "", volume: "", type: state.type, q: "" }), text: j.name })]),
        el("td", { class: "num", text: j.year_start + "–" + j.year_end }),
        el("td", { class: "num", text: fmt(j.issues) }),
        el("td", { class: "num", text: fmt(j.research) }),
        el("td", { class: "num", text: fmt(j.other) })
      ]));
    });
    els.results.appendChild(el("div", { class: "tbl-wrap" }, [
      el("table", null, [
        el("caption", { text: "Journals in the core 49, with TOC coverage 2012–2025" }),
        el("thead", null, [el("tr", null, [
          el("th", { scope: "col", text: "Journal" }), el("th", { scope: "col", class: "num", text: "Years" }),
          el("th", { scope: "col", class: "num", text: "Issues" }), el("th", { scope: "col", class: "num", text: "Research" }),
          el("th", { scope: "col", class: "num", text: "Other" })
        ])]),
        tbody
      ])
    ]));
  }

  function typeOk(t) {
    if (state.type === "all") return true;
    if (state.type === "research") return t === "a";
    return t !== "a";
  }

  function renderItem(it, shard, showWhere) {
    var title = it[1], doi = it[2], pages = it[3], t = it[4], authors = it[5], src = it[6], pub = it[7];
    var kids = [];
    if (showWhere) {
      var iss = shard.issues[it[0]];
      kids.push(el("div", { class: "where", text: iss[0] + " · " + issueLabel(iss[1], iss[2]) }));
    }
    kids.push(el("h4", { class: "title" + (title ? "" : " untitled") }, [
      el("span", { class: "badge " + TYPE_CLASS[t], text: TYPE_LABEL[t] }),
      title || "(No title in the TOC record)"
    ]));
    if (authors) {
      kids.push(el("div", { class: "authors" }, [
        el("span", { text: authors }),
        el("span", { class: "src", title: SRC_TITLE[src], text: SRC_LABEL[src] })
      ]));
    } else {
      kids.push(el("div", { class: "authors muted", text: "No author names in this release" }));
    }
    var meta = [];
    if (pages) meta.push(el("span", { text: "Pages " + pages }));
    if (doi) meta.push(el("span", null, ["DOI ", el("a", { href: "https://doi.org/" + doi, rel: "noopener", text: doi })]));
    else meta.push(el("span", { text: "No DOI in the TOC record" }));
    if (pub) meta.push(el("a", { href: pub, rel: "noopener", text: "Publisher page" }));
    kids.push(el("div", { class: "meta" }, meta));
    return el("li", { class: "item" }, kids);
  }

  function renderShard(shard) {
    var j = bySlug[shard.slug];
    var q = fold(state.q.trim());
    var terms = q ? q.split(/\s+/) : [];
    var issueOk = {};
    shard.issues.forEach(function (i, k) {
      issueOk[k] = (!state.year || i[0] === state.year) && (!state.issue || (i[1] === state.volume && i[2] === state.issue));
    });
    var counts = { research: 0, other: 0, all: 0 };
    var hits = [];
    shard.items.forEach(function (it) {
      if (!issueOk[it[0]]) return;
      if (terms.length) {
        for (var x = 0; x < terms.length; x++) if (it[8].indexOf(terms[x]) < 0) return;
      }
      counts.all++;
      if (it[4] === "a") counts.research++; else counts.other++;
      if (typeOk(it[4])) hits.push(it);
    });
    setTypeCounts(counts);

    var scope = j.name + (state.year ? ", " + state.year : "") + (state.issue ? ", " + issueLabel(state.volume, state.issue) : "");
    els.heading.textContent = scope;
    document.title = scope + " — Journal Articles";
    var typeWord = state.type === "research" ? "research articles" : state.type === "other" ? "other and proceedings items" : "items";

    // Journal overview: years and issues (no year, no search).
    if (!state.year && !terms.length) {
      els.count.textContent = fmt(shard.issues.length) + " issues, " + fmt(j.items) + " TOC items (" +
        fmt(j.research) + " research, " + fmt(j.other) + " other). Choose a year or issue, or search titles and names.";
      var grid = el("div", { class: "years" });
      var byYear = {};
      var order = [];
      shard.issues.forEach(function (i) {
        if (!byYear[i[0]]) { byYear[i[0]] = []; order.push(i[0]); }
        byYear[i[0]].push(i);
      });
      order.forEach(function (y) {
        var list = byYear[y];
        var tot = 0, res = 0;
        list.forEach(function (i) { tot += i[4]; res += i[5]; });
        var ul = el("ul", { class: "issue-links" });
        var multiVol = new Set(list.map(function (z) { return z[1]; })).size > 1;
        list.forEach(function (i) {
          ul.appendChild(el("li", null, [el("a", {
            href: buildQuery({ journal: shard.slug, year: y, volume: i[1], issue: i[2], type: state.type, q: "" }),
            "aria-label": y + " " + issueLabel(i[1], i[2]),
            text: multiVol ? i[1] + "(" + i[2] + ")" : i[2]
          })]));
        });
        grid.appendChild(el("div", { class: "year-card" }, [
          el("h3", null, [el("a", { href: buildQuery({ journal: shard.slug, year: y, volume: "", issue: "", type: state.type, q: "" }), text: y })]),
          el("div", { class: "sub", text: list.length + (list.length === 1 ? " issue · " : " issues · ") + fmt(tot) + " items · " + fmt(res) + " research" }),
          ul
        ]));
      });
      els.results.appendChild(grid);
      els.results.appendChild(el("p", { class: "hint", text: "Issue links show the issue label used in the TOC; a volume prefix appears when a year spans more than one volume. Elsevier continuous-publication volumes are labelled issue “C”." }));
      return;
    }

    els.count.textContent = fmt(hits.length) + " " + typeWord + (terms.length ? " matching “" + state.q.trim() + "”" : "") + " in this view.";
    if (!hits.length) {
      els.results.appendChild(el("p", { class: "empty", text: counts.all ? "No items of this type here. Try “All items”." : "No items match." }));
      return;
    }
    var shown = hits.slice(0, limit);
    var flat = !!terms.length && !state.year;
    if (flat) {
      var ol = el("ol", { class: "items" });
      shown.forEach(function (it) { ol.appendChild(renderItem(it, shard, true)); });
      els.results.appendChild(el("section", { class: "issue", "aria-label": "Search results" }, [ol]));
    } else {
      var groups = [], cur = null;
      shown.forEach(function (it) {
        if (!cur || cur.k !== it[0]) { cur = { k: it[0], items: [] }; groups.push(cur); }
        cur.items.push(it);
      });
      groups.forEach(function (g) {
        var iss = shard.issues[g.k];
        var ol2 = el("ol", { class: "items" });
        g.items.forEach(function (it) { ol2.appendChild(renderItem(it, shard, false)); });
        var head = el("div", { class: "issue-head" }, [
          el("h3", null, [state.issue ? issueLabel(iss[1], iss[2]) : el("a", {
            href: buildQuery({ journal: shard.slug, year: iss[0], volume: iss[1], issue: iss[2], type: state.type, q: state.q }),
            text: issueLabel(iss[1], iss[2])
          })]),
          el("span", { class: "sub" }, [
            iss[0] + " · " + fmt(iss[4]) + " items (" + fmt(iss[5]) + " research, " + fmt(iss[6]) + " other) · ",
            el("a", { href: iss[3], rel: "noopener", text: "Issue TOC" })
          ])
        ]);
        els.results.appendChild(el("section", { class: "issue" }, [head, ol2]));
      });
    }
    if (hits.length > limit) {
      var more = el("button", { type: "button", class: "btn", text: "Show more (" + fmt(hits.length - limit) + " left)" });
      more.addEventListener("click", function () { limit += PAGE; render(); });
      els.results.appendChild(el("div", { class: "pager" }, [more]));
    }
  }

  function render() {
    syncControls();
    els.results.innerHTML = "";
    var j = bySlug[state.journal];
    if (state.journal && !j) {
      crumbs(null); fillYearIssue(null);
      els.heading.textContent = "Journal not found";
      els.count.textContent = "";
      els.results.appendChild(el("p", { class: "empty", text: "No journal with the slug “" + state.journal + "” in this release." }));
      return;
    }
    crumbs(j);
    if (!j) { fillYearIssue(null); renderJournalList(); return; }
    els.count.textContent = "Loading " + j.name + "…";
    els.results.setAttribute("aria-busy", "true");
    loadShard(j.slug).then(function (shard) {
      if (state.journal !== shard.slug) return;
      els.results.removeAttribute("aria-busy");
      els.results.innerHTML = "";
      fillYearIssue(shard);
      renderShard(shard);
    }).catch(function (e) {
      els.results.removeAttribute("aria-busy");
      els.count.textContent = "Could not load this journal (" + e.message + ").";
    });
  }

  // Events
  els.journal.addEventListener("change", function () {
    state.journal = els.journal.value; state.year = ""; state.volume = ""; state.issue = ""; state.q = "";
    commit(true);
  });
  els.year.addEventListener("change", function () {
    state.year = els.year.value; state.volume = ""; state.issue = "";
    commit(true);
  });
  els.issue.addEventListener("change", function () {
    var v = els.issue.value.split("|");
    state.volume = v[0] || ""; state.issue = v[1] || "";
    commit(true);
  });
  var timer = null;
  els.q.addEventListener("input", function () {
    clearTimeout(timer);
    timer = setTimeout(function () { state.q = els.q.value; commit(false); }, 200);
  });
  els.types.addEventListener("click", function (e) {
    var b = e.target.closest("button[data-type]");
    if (!b) return;
    state.type = b.getAttribute("data-type");
    commit(false);
  });
  els.reset.addEventListener("click", function () {
    state = { journal: state.journal, year: "", volume: "", issue: "", type: "research", q: "" };
    commit(true);
  });
  window.addEventListener("popstate", function () { state = readState(); limit = PAGE; render(); });

  loadIndex().then(function (d) {
    index = d;
    d.journals.forEach(function (j) { bySlug[j.slug] = j; });
    fillJournalSelect();
    render();
  }).catch(function (e) {
    els.count.textContent = "Could not load the journal index (" + e.message + "). Serve the site over HTTP, e.g. python -m http.server.";
  });
})();
