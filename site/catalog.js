/* Journal Articles catalog browser.
   Loads data/journals.json, then one journal shard on demand.
   Site-wide search (no journal selected, q= set) loads
   data/search/research.json and, when other items are included,
   data/search/other.json. Those files store the same display names
   as the shards (including the TOC byline-prefix rule).
   An issue link may include item=<n>, the 0-based position of the
   item within that issue's TOC order, used only to highlight it.
   On an issue, Previous and Next follow shard.issues order
   (year, volume, issue as sorted at build time), including across
   a year or volume. Cite copies a plain-text citation and BibTeX
   from the fields already on the item.
   A query that is a DOI (10.…, https://doi.org/…, or http://dx.doi.org/…)
   looks up data/search/doi.json and opens that issue with item=.
   A DOI that is not in the file is reported as missing.
   Each displayed author name links to a site-wide search for that
   name string. The label is "Search for this name". It is not an
   author page and does not use a person id. */
(function () {
  "use strict";

  var TYPE_LABEL = { a: "Research article", o: "Other", p: "Proceedings" };
  var TYPE_CLASS = { a: "t-article", o: "t-other", p: "t-proceedings" };
  var SRC_LABEL = { s: "as printed in the TOC", o: "OpenAlex (name only)", d: "OpenAlex by DOI (name only)",
    c: "Crossref by DOI (name only)", q: "official article page" };
  var SRC_TITLE = {
    s: "Author names as printed in the publisher table of contents.",
    o: "Author names from OpenAlex, recorded as names only. Not a person registry.",
    d: "Author names from the OpenAlex work for this DOI, names only. Not a person registry.",
    c: "Author names from the Crossref record for this DOI, names only. Not a person registry.",
    q: "Author names from the journal's official article page."
  };
  var PAGE = 250;
  var SEARCH_PAGE = 40;

  var els = {
    journal: document.getElementById("f-journal"),
    jlist: document.getElementById("f-journal-list"),
    year: document.getElementById("f-year"),
    issue: document.getElementById("f-issue"),
    q: document.getElementById("f-q"),
    qLabel: document.getElementById("f-q-label"),
    types: document.getElementById("f-type"),
    reset: document.getElementById("f-reset"),
    all: document.getElementById("f-all"),
    yearRow: document.getElementById("year-row"),
    issueRow: document.getElementById("issue-row"),
    crumbs: document.getElementById("crumbs"),
    heading: document.getElementById("results-title"),
    count: document.getElementById("count"),
    results: document.getElementById("results")
  };

  var index = null;
  var bySlug = {};
  var shards = {};
  var searchCache = {};
  var searchInflight = {};
  var searchGen = 0;
  var doiCache = null;
  var doiInflight = null;
  var doiTimer = null;
  var doiImmediate = false;
  var journalFilter = "";
  var combo = { open: false, active: -1, matches: [] };
  var limit = SEARCH_PAGE;
  var state = readState();
  var scrollToIssue = false;
  limit = pageSize();

  function readState() {
    var p = new URLSearchParams(location.search);
    var t = p.get("type");
    var item = p.get("item") || "";
    if (!/^\d+$/.test(item)) item = "";
    return {
      journal: p.get("journal") || "",
      year: p.get("year") || "",
      volume: p.get("volume") || "",
      issue: p.get("issue") || "",
      type: (t === "all" || t === "other" || t === "research") ? t : "research",
      q: p.get("q") || "",
      item: item
    };
  }

  function queryText() { return (state.q || "").trim(); }

  function parseDoiQuery(q) {
    var s = String(q || "").replace(/^\s+|\s+$/g, "");
    if (!s) return "";
    var m = s.match(/^(?:https?:\/\/(?:dx\.)?doi\.org\/|doi:)?(10\.\d{4,9}\/\S+)$/i);
    if (!m) return "";
    var doi = m[1];
    if (/^https?:\/\//i.test(s)) doi = doi.replace(/[?#].*$/, "");
    doi = doi.replace(/\/+$/, "");
    if (!/^10\.\d{4,9}\/\S+$/i.test(doi)) return "";
    return doi.toLowerCase();
  }

  function pageSize() { return (!state.journal && queryText()) ? SEARCH_PAGE : PAGE; }

  function buildQuery(s) {
    var p = new URLSearchParams();
    if (s.journal) p.set("journal", s.journal);
    if (s.journal && s.year) p.set("year", s.year);
    if (s.journal && s.year && s.issue) { p.set("volume", s.volume); p.set("issue", s.issue); }
    if (s.type && s.type !== "research") p.set("type", s.type);
    if (s.q) p.set("q", s.q);
    if (s.item && s.journal && s.year && s.issue) p.set("item", s.item);
    var str = p.toString();
    return "catalog.html" + (str ? "?" + str : "");
  }

  function commit(push) {
    var url = buildQuery(state);
    if (push) history.pushState(null, "", url); else history.replaceState(null, "", url);
    limit = pageSize();
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

  function trimField(s) {
    return s == null ? "" : String(s).trim();
  }

  function doiBare(doi) {
    return trimField(doi).replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "");
  }

  function bibEscape(s) {
    return String(s)
      .replace(/\\/g, "\u0000")
      .replace(/([#$%&_{}])/g, "\\$1")
      .replace(/~/g, "\\textasciitilde{}")
      .replace(/\^/g, "\\textasciicircum{}")
      .replace(/\u0000/g, "\\textbackslash{}");
  }

  function citeKey(doi, slug, year, volume, issue, n) {
    var raw = doiBare(doi);
    var base = raw ? raw : [slug, year, volume, issue, "n" + n].join("-");
    base = base.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
    return base || "article";
  }

  function plainCitation(o) {
    var authors = trimField(o.authors);
    var year = trimField(o.year);
    var title = trimField(o.title);
    var journal = trimField(o.journal);
    var volume = trimField(o.volume);
    var issue = trimField(o.issue);
    var pages = trimField(o.pages);
    var doi = doiBare(o.doi);
    var chunks = [];
    if (authors) chunks.push(/[.!?]$/.test(authors) ? authors : authors + ".");
    if (year) chunks.push(year + ".");
    if (title) {
      var end = ".";
      if (/[!?]$/.test(title)) {
        end = title.slice(-1);
        title = title.slice(0, -1).trim();
      } else {
        title = title.replace(/\.+$/, "").trim();
      }
      chunks.push("\u201c" + title + end + "\u201d");
    }
    var loc = journal;
    var vi = "";
    if (volume && issue) vi = volume + "(" + issue + ")";
    else if (volume) vi = volume;
    else if (issue) vi = "no. " + issue;
    if (vi) loc = loc ? (loc + " " + vi) : vi;
    if (pages) loc = loc ? (loc + ": " + pages) : pages;
    if (loc) {
      if (!/[.!?]$/.test(loc)) loc += ".";
      chunks.push(loc);
    }
    if (doi) chunks.push("https://doi.org/" + doi);
    return chunks.join(" ");
  }

  function bibtexCitation(o) {
    var doi = doiBare(o.doi);
    var fields = [
      ["author", trimField(o.authors)],
      ["title", trimField(o.title)],
      ["journal", trimField(o.journal)],
      ["year", trimField(o.year)],
      ["volume", trimField(o.volume)],
      ["number", trimField(o.issue)],
      ["pages", trimField(o.pages)],
      ["doi", doi]
    ];
    var lines = [];
    fields.forEach(function (pair) {
      if (!pair[1]) return;
      lines.push("  " + pair[0] + " = {" + bibEscape(pair[1]) + "}");
    });
    return "@article{" + o.key + ",\n" + lines.join(",\n") + "\n}";
  }

  function currentIssueIndex(shard) {
    if (!state.issue) return -1;
    for (var i = 0; i < shard.issues.length; i++) {
      var row = shard.issues[i];
      if (row[0] === state.year && row[1] === state.volume && row[2] === state.issue) return i;
    }
    return -1;
  }

  function issueStep(dir, iss, journal) {
    var forward = dir === "next";
    var dest = iss
      ? iss[0] + " \u00b7 " + issueLabel(iss[1], iss[2])
      : (forward ? "No later issue" : "No earlier issue");
    var label = (forward ? "Next issue, " : "Previous issue, ") + dest;
    var kids = [
      el("span", { class: "step-dir", text: forward ? "Next issue" : "Previous issue" }),
      el("span", { class: "step-dest", text: dest })
    ];
    if (!iss) {
      return el("button", {
        type: "button",
        class: "issue-step" + (forward ? " next" : ""),
        disabled: true,
        "aria-label": label
      }, kids);
    }
    return el("a", {
      class: "issue-step" + (forward ? " next" : ""),
      href: buildQuery({
        journal: journal, year: iss[0], volume: iss[1], issue: iss[2],
        type: state.type, q: state.q
      }),
      "aria-label": label
    }, kids);
  }

  function issueNav(shard, idx, place) {
    var prev = idx > 0 ? shard.issues[idx - 1] : null;
    var next = idx + 1 < shard.issues.length ? shard.issues[idx + 1] : null;
    return el("nav", {
      class: "issue-nav " + place,
      "aria-label": place === "end" ? "Adjacent issues, end of issue" : "Adjacent issues"
    }, [
      issueStep("prev", prev, shard.slug),
      issueStep("next", next, shard.slug)
    ]);
  }

  function goToIssue(href) {
    var nextUrl = new URL(href, location.href);
    var p = nextUrl.searchParams;
    state.year = p.get("year") || "";
    state.volume = p.get("volume") || "";
    state.issue = p.get("issue") || "";
    state.item = "";
    scrollToIssue = true;
    commit(true);
  }

  function finishIssueScroll() {
    if (!scrollToIssue) return;
    scrollToIssue = false;
    var title = document.getElementById("results-title");
    if (!title || !title.scrollIntoView) return;
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    title.scrollIntoView({ block: "start", behavior: reduce ? "auto" : "smooth" });
  }

  function typeFor(itemType) {
    if (state.type === "all") return "all";
    if (state.type === "research" && itemType === "a") return "research";
    if (state.type === "other" && itemType !== "a") return "other";
    return itemType === "a" ? "research" : "other";
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
      var seq = {};
      d.items.forEach(function (it) {
        var k = it[0];
        var n = seq[k] || 0;
        seq[k] = n + 1;
        it._n = n;
        it.push(fold(it[1] + " " + it[5]));
      });
      shards[slug] = d;
      return d;
    });
  }

  function loadSearchKind(kind) {
    if (searchCache[kind]) return Promise.resolve(searchCache[kind]);
    if (searchInflight[kind]) return searchInflight[kind];
    var url = "data/search/" + kind + ".json";
    searchInflight[kind] = fetch(url).then(function (r) {
      if (!r.ok) throw new Error(url + " " + r.status);
      return r.json();
    }).then(function (d) {
      d.kind = kind;
      d.hay = new Array(d.items.length);
      for (var i = 0; i < d.items.length; i++) {
        var it = d.items[i];
        d.hay[i] = fold((it[4] || "") + " " + (it[5] || ""));
      }
      searchCache[kind] = d;
      return d;
    }).catch(function (e) {
      delete searchInflight[kind];
      throw e;
    });
    return searchInflight[kind];
  }

  function neededKinds() {
    var kinds = [];
    if (state.type !== "other") kinds.push("research");
    if (state.type !== "research") kinds.push("other");
    if (searchCache.research && kinds.indexOf("research") < 0) kinds.push("research");
    if (searchCache.other && kinds.indexOf("other") < 0) kinds.push("other");
    return kinds;
  }

  function termsOf(q) {
    var f = fold(q);
    return f ? f.split(/\s+/).filter(Boolean) : [];
  }

  function matches(hay, terms) {
    if (!terms.length) return true;
    for (var i = 0; i < terms.length; i++) if (hay.indexOf(terms[i]) < 0) return false;
    return true;
  }

  function journalMatches(q) {
    var terms = termsOf(q);
    return index.journals.filter(function (j) {
      return matches(fold(j.name + " " + j.slug), terms);
    });
  }

  function selectedJournalName() {
    return state.journal && bySlug[state.journal] ? bySlug[state.journal].name : "";
  }

  function comboQuery() {
    var raw = els.journal.value.trim();
    if (state.journal && raw === selectedJournalName()) return "";
    if (!state.journal) return journalFilter.trim();
    return raw;
  }

  function renderCombo() {
    var list = els.jlist;
    combo.matches = journalMatches(comboQuery());
    list.innerHTML = "";
    if (!combo.matches.length) {
      list.appendChild(el("li", { class: "empty", role: "presentation", text: "No journal matches" }));
    }
    combo.matches.forEach(function (j, i) {
      var attrs = {
        role: "option",
        id: "jopt-" + j.slug,
        "aria-selected": i === combo.active ? "true" : "false"
      };
      if (i === combo.active) attrs.class = "active";
      var li = el("li", attrs, [
        el("span", { class: "jname", text: j.name }),
        el("span", { class: "jcount", text: fmt(j.research) + " research · " + fmt(j.items) + " items" })
      ]);
      li.addEventListener("pointerdown", function (e) {
        e.preventDefault();
        chooseJournal(j.slug);
      });
      list.appendChild(li);
    });
    var show = combo.open && document.activeElement === els.journal;
    list.hidden = !show;
    els.journal.setAttribute("aria-expanded", show ? "true" : "false");
    if (show && combo.active >= 0 && combo.matches[combo.active]) {
      els.journal.setAttribute("aria-activedescendant", "jopt-" + combo.matches[combo.active].slug);
      var node = document.getElementById("jopt-" + combo.matches[combo.active].slug);
      if (node && node.scrollIntoView) node.scrollIntoView({ block: "nearest" });
    } else {
      els.journal.removeAttribute("aria-activedescendant");
    }
  }

  function chooseJournal(slug) {
    journalFilter = "";
    state.journal = slug;
    state.year = "";
    state.volume = "";
    state.issue = "";
    state.q = "";
    state.item = "";
    combo.open = false;
    combo.active = -1;
    commit(true);
    els.journal.value = bySlug[slug] ? bySlug[slug].name : "";
    els.journal.blur();
  }

  function revealPressed(container) {
    var pressed = container.querySelector('[aria-pressed="true"]');
    if (!pressed || container.scrollWidth <= container.clientWidth) return;
    container.scrollLeft = Math.max(0, pressed.offsetLeft - 12);
  }

  function fillPicks(shard) {
    els.year.innerHTML = "";
    els.issue.innerHTML = "";
    if (!shard) {
      els.year.appendChild(el("span", { class: "pick-note", text: state.journal ? "Loading years…" : "Choose a journal to see years" }));
      els.issue.appendChild(el("span", { class: "pick-note", text: state.year ? "Loading issues…" : "Choose a year to see issues" }));
      return;
    }
    var years = [];
    var byYear = {};
    shard.issues.forEach(function (i) {
      if (!byYear[i[0]]) { byYear[i[0]] = []; years.push(i[0]); }
      byYear[i[0]].push(i);
    });
    function chip(label, pressed, attrs, count, aria) {
      attrs.type = "button";
      attrs.class = "chip";
      attrs["aria-pressed"] = pressed ? "true" : "false";
      if (aria) attrs["aria-label"] = aria;
      var b = el("button", attrs, [label]);
      if (count != null) b.appendChild(el("span", { class: "c", text: fmt(count) }));
      return b;
    }
    els.year.appendChild(chip("All years", !state.year, { "data-year": "" }, null, "All years"));
    years.forEach(function (y) {
      var res = 0;
      byYear[y].forEach(function (i) { res += i[5]; });
      els.year.appendChild(chip(y, state.year === y, { "data-year": y }, res, y + ", " + fmt(res) + " research articles"));
    });
    revealPressed(els.year);
    if (!state.year) {
      els.issue.appendChild(el("span", { class: "pick-note", text: "Choose a year to pick an issue" }));
      return;
    }
    els.issue.appendChild(chip("All issues", !state.issue, { "data-issue": "" }, null, "All issues in " + state.year));
    var list = byYear[state.year] || [];
    var multiVol = false;
    var seenVol = null;
    list.forEach(function (i) {
      if (seenVol == null) seenVol = i[1];
      else if (seenVol !== i[1]) multiVol = true;
    });
    list.forEach(function (i) {
      var label = multiVol ? i[1] + "(" + i[2] + ")" : i[2];
      var pressed = !!(state.issue && state.volume === i[1] && state.issue === i[2]);
      els.issue.appendChild(chip(label, pressed, { "data-volume": i[1], "data-issue": i[2] }, null,
        state.year + " " + issueLabel(i[1], i[2]) + ", " + fmt(i[5]) + " research articles"));
    });
    revealPressed(els.issue);
  }

  function syncControls() {
    if (document.activeElement !== els.journal) {
      els.journal.value = state.journal ? selectedJournalName() : journalFilter;
    }
    if (els.q.value !== state.q) els.q.value = state.q;
    if (state.journal && bySlug[state.journal]) {
      els.qLabel.textContent = "Search titles and names in this journal, or paste a DOI";
      els.q.placeholder = "e.g. minimum wage, Duflo, or a DOI";
    } else {
      els.qLabel.textContent = "Search titles, author names, or a DOI";
      els.q.placeholder = "e.g. minimum wage, Duflo, or a DOI";
    }
    els.all.hidden = !state.journal;
    els.all.textContent = queryText() ? "Search all journals" : "Show all journals";
    els.yearRow.hidden = !state.journal;
    els.issueRow.hidden = !(state.journal && state.year);
    Array.prototype.forEach.call(els.types.querySelectorAll("button"), function (b) {
      b.setAttribute("aria-pressed", b.getAttribute("data-type") === state.type ? "true" : "false");
    });
  }

  function setTypeCounts(counts) {
    Array.prototype.forEach.call(els.types.querySelectorAll("button"), function (b) {
      var c = b.querySelector(".c");
      var t = b.getAttribute("data-type");
      c.textContent = counts && counts[t] != null ? fmt(counts[t]) : "";
    });
  }

  function crumbs(j) {
    els.crumbs.innerHTML = "";
    var parts = [el("a", { href: "catalog.html", text: "All journals" })];
    if (!j && queryText()) {
      parts.push(" › ");
      parts.push(el("span", { text: "Search" }));
    }
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
    var terms = termsOf(journalFilter);
    var shown = journalMatches(journalFilter);
    var noun = shown.length === 1 ? "journal" : "journals";
    var extra = terms.length ? " matching “" + journalFilter.trim() + "”" : "";
    els.count.textContent = fmt(shown.length) + " " + noun + extra + ". Pick one to load its table of contents.";
    if (!shown.length) {
      els.results.appendChild(el("p", { class: "empty", text: "No journal name matches." }));
      return;
    }
    var list = el("div", { class: "jlist" });
    shown.forEach(function (j) {
      list.appendChild(el("a", {
        class: "jrow",
        href: buildQuery({ journal: j.slug, year: "", issue: "", volume: "", type: state.type, q: "" })
      }, [
        el("span", { class: "jname", text: j.name }),
        el("span", { class: "jmeta", text: j.year_start + "–" + j.year_end + " · " + fmt(j.issues) + " issues · " + fmt(j.other) + " other" }),
        el("span", { class: "jnums" }, [
          el("span", null, [el("strong", { text: fmt(j.research) }), " research"]),
          el("span", null, [el("strong", { text: fmt(j.items) }), " items"])
        ])
      ]));
    });
    els.results.appendChild(list);
  }

  function paintJournalList() {
    els.results.innerHTML = "";
    renderJournalList();
  }

  function typeOk(t) {
    if (state.type === "all") return true;
    if (state.type === "research") return t === "a";
    return t !== "a";
  }

  /* NAME_RANGES_START
     Split a displayed author string into the names already in that string.
     Separators stay in the gaps, so the visible line is unchanged.
     A single "Last, First" name is not split. "Jr." stays with its name. */
  function nameRange(s, start, end) {
    return { start: start, end: end, text: s.slice(start, end) };
  }

  function trimRange(s, start, end) {
    while (start < end && /\s/.test(s.charAt(start))) start++;
    while (end > start && /\s/.test(s.charAt(end - 1))) end--;
    return end > start ? nameRange(s, start, end) : null;
  }

  function semicolonRanges(s) {
    var parts = [];
    var re = /[^;]+/g;
    var m;
    while ((m = re.exec(s))) {
      var raw = m[0];
      var lead = raw.length - raw.replace(/^\s+/, "").length;
      var trail = raw.length - raw.replace(/\s+$/, "").length;
      var hit = trimRange(s, m.index + lead, m.index + raw.length - trail);
      if (hit) parts.push(hit);
    }
    if (parts.length >= 3) {
      var first = parts[0].text;
      var rest = parts.slice(1);
      var duplicated = rest.every(function (p) { return p.text && first.indexOf(p.text) !== -1; })
        && (first.indexOf("\u24e1") !== -1 || first.indexOf(" and ") !== -1);
      if (duplicated) {
        var sub = [];
        var cursor = parts[0].start;
        var limit = parts[0].end;
        var ok = true;
        for (var i = 0; i < rest.length; i++) {
          var n = rest[i].text;
          var idx = s.indexOf(n, cursor);
          if (idx < 0 || idx + n.length > limit) { ok = false; break; }
          sub.push(nameRange(s, idx, idx + n.length));
          cursor = idx + n.length;
        }
        if (ok) return sub.concat(rest);
      }
    }
    return parts;
  }

  function maskSuffixes(s) {
    return s.replace(/,\s+(?:Jr\.?|Sr\.?|III|II|IV|Esq\.?)(?=,|\s+and\s+|$)/gi, function (m) {
      return new Array(m.length + 1).join("\u0001");
    });
  }

  function bylineRanges(s) {
    var masked = maskSuffixes(s);
    var re = /,\s+and\s+|,\s+|\s+and\s+|\s*\u24e1\s*/g;
    var ranges = [];
    var last = 0;
    var m;
    while ((m = re.exec(masked))) {
      var hit = trimRange(s, last, m.index);
      if (hit) ranges.push(hit);
      last = m.index + m[0].length;
    }
    var tail = trimRange(s, last, s.length);
    if (tail) ranges.push(tail);
    return ranges.length ? ranges : [nameRange(s, 0, s.length)];
  }

  function nameRanges(s) {
    if (!s) return [];
    if (s.indexOf(";") !== -1) return semicolonRanges(s);
    if (s.indexOf(" and ") !== -1 || s.indexOf("\u24e1") !== -1) return bylineRanges(s);
    return [nameRange(s, 0, s.length)];
  }
  /* NAME_RANGES_END */

  function authorLine(authors, src) {
    if (!authors) return el("div", { class: "authors muted", text: "No author names in this release" });
    var kids = [];
    var ranges = nameRanges(authors);
    var cursor = 0;
    ranges.forEach(function (r) {
      if (r.start > cursor) kids.push(authors.slice(cursor, r.start));
      var name = authors.slice(r.start, r.end);
      kids.push(el("a", {
        class: "author-name",
        href: buildQuery({ journal: "", year: "", volume: "", issue: "", type: "research", q: name, item: "" }),
        "data-name": name,
        title: "Search for this name",
        "aria-label": "Search for this name: " + name
      }, [name]));
      cursor = r.end;
    });
    if (cursor < authors.length) kids.push(authors.slice(cursor));
    if (src && SRC_LABEL[src]) kids.push(el("span", { class: "src", title: SRC_TITLE[src], text: SRC_LABEL[src] }));
    return el("div", { class: "authors" }, kids);
  }

  function doiLine(doi, citeBtn) {
    var kids = [];
    if (doi) {
      kids.push("DOI ");
      kids.push(el("a", { class: "doi", href: "https://doi.org/" + doi, rel: "noopener", text: doi }));
    } else {
      kids.push(el("span", { text: "No DOI in the TOC record" }));
    }
    var actions = [];
    if (doi) {
      actions.push(el("button", {
        type: "button",
        class: "copy-doi",
        "data-doi": doi,
        "aria-label": "Copy DOI " + doi,
        text: "Copy DOI"
      }));
    }
    if (citeBtn) actions.push(citeBtn);
    if (actions.length) kids.push(el("span", { class: "item-actions" }, actions));
    return el("span", { class: "doi-line" }, kids);
  }

  function citeField(label, text, copyLabel) {
    return el("div", { class: "cite-field" }, [
      el("div", { class: "cite-field-head" }, [
        el("span", { class: "cite-label", text: label }),
        el("button", {
          type: "button",
          class: "copy-cite",
          "data-label": copyLabel,
          "aria-label": copyLabel,
          text: copyLabel
        })
      ]),
      el("pre", { class: "cite-block", text: text })
    ]);
  }

  function citeControl(info) {
    var plain = plainCitation(info);
    var bib = bibtexCitation(info);
    var id = "cite-" + info.slug + "-" + info.issueIdx + "-" + info.n;
    var btn = el("button", {
      type: "button",
      class: "cite-btn",
      id: id + "-btn",
      "aria-expanded": "false",
      "aria-controls": id,
      text: "Cite"
    });
    var panel = el("div", {
      class: "cite-panel",
      id: id,
      role: "region",
      "aria-labelledby": id + "-btn",
      hidden: true
    }, [
      citeField("Citation", plain, "Copy citation"),
      citeField("BibTeX", bib, "Copy BibTeX"),
      el("p", { class: "cite-status", role: "status", "aria-live": "polite" }),
      el("p", { class: "cite-note", text: "Copied as shown: author names, title, journal, year, volume, issue, pages, and DOI. Empty fields are left out." })
    ]);
    return { button: btn, panel: panel };
  }

  function renderItem(it, shard, showWhere) {
    var title = it[1], doi = it[2], pages = it[3], t = it[4], authors = it[5], src = it[6], pub = it[7];
    var n = it._n;
    var iss = shard.issues[it[0]];
    var target = !!(state.item !== "" && state.issue && String(n) === String(state.item));
    var kids = [];
    if (target) kids.push(el("span", { class: "sr-only", text: "Highlighted item." }));
    if (showWhere) {
      var href = buildQuery({
        journal: shard.slug, year: iss[0], volume: iss[1], issue: iss[2],
        type: typeFor(t), q: "", item: String(n)
      });
      kids.push(el("div", { class: "where" }, [
        el("a", { href: href, text: iss[0] + " · " + issueLabel(iss[1], iss[2]) })
      ]));
    }
    kids.push(el("h4", { class: "title" + (title ? "" : " untitled") }, [
      el("span", { class: "badge " + TYPE_CLASS[t], text: TYPE_LABEL[t] }),
      title || "(No title in the TOC record)"
    ]));
    kids.push(authorLine(authors, src));
    var cite = citeControl({
      authors: authors,
      title: title,
      journal: shard.name || "",
      year: iss[0],
      volume: iss[1],
      issue: iss[2],
      pages: pages,
      doi: doi,
      slug: shard.slug,
      issueIdx: it[0],
      n: n,
      key: citeKey(doi, shard.slug, iss[0], iss[1], iss[2], n)
    });
    var meta = [];
    if (pages) meta.push(el("span", { text: "Pages " + pages }));
    meta.push(doiLine(doi, cite.button));
    if (pub) meta.push(el("a", { href: pub, rel: "noopener", text: "Publisher page" }));
    kids.push(el("div", { class: "meta" }, meta));
    kids.push(cite.panel);
    return el("li", {
      class: "item" + (target ? " target" : ""),
      id: "item-" + it[0] + "-" + n,
      "data-n": String(n)
    }, kids);
  }

  function focusTarget() {
    if (!state.item || !state.issue) return;
    var nodes = els.results.querySelectorAll("li.item[data-n]");
    var node = null;
    for (var i = 0; i < nodes.length; i++) {
      if (nodes[i].getAttribute("data-n") === state.item) { node = nodes[i]; break; }
    }
    if (!node) {
      var note = el("p", { class: "hint", text: "The linked item is hidden by the item-type filter. Choose “All items” to show it." });
      if (els.results.firstChild) els.results.insertBefore(note, els.results.firstChild);
      else els.results.appendChild(note);
      return;
    }
    node.setAttribute("tabindex", "-1");
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    node.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
    if (node.focus) node.focus({ preventScroll: true });
  }

  function renderShard(shard) {
    var j = bySlug[shard.slug];
    var terms = termsOf(state.q);
    var issueOk = {};
    shard.issues.forEach(function (i, k) {
      issueOk[k] = (!state.year || i[0] === state.year) && (!state.issue || (i[1] === state.volume && i[2] === state.issue));
    });
    var counts = { research: 0, other: 0, all: 0 };
    var hits = [];
    shard.items.forEach(function (it) {
      if (!issueOk[it[0]]) return;
      if (!matches(it[8], terms)) return;
      counts.all++;
      if (it[4] === "a") counts.research++; else counts.other++;
      if (typeOk(it[4])) hits.push(it);
    });
    setTypeCounts(counts);

    var scope = j.name + (state.year ? ", " + state.year : "") + (state.issue ? ", " + issueLabel(state.volume, state.issue) : "");
    els.heading.textContent = scope;
    document.title = scope + " — Journal Articles";
    var typeWord = state.type === "research" ? "research articles" : state.type === "other" ? "other and proceedings items" : "items";

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
        var multiVol = false;
        var seenVol = null;
        list.forEach(function (z) {
          if (seenVol == null) seenVol = z[1];
          else if (seenVol !== z[1]) multiVol = true;
        });
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

    els.count.textContent = fmt(hits.length) + " " + typeWord + (terms.length ? " matching “" + queryText() + "”" : "") + " in this view.";
    var issueIdx = currentIssueIndex(shard);
    if (!hits.length) {
      if (issueIdx >= 0) els.results.appendChild(issueNav(shard, issueIdx, "solo"));
      els.results.appendChild(el("p", { class: "empty", text: counts.all ? "No items of this type here. Try “All items”." : "No items match." }));
      focusTarget();
      finishIssueScroll();
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
        var sectionKids = [head];
        if (issueIdx >= 0 && g.k === issueIdx) sectionKids.push(issueNav(shard, issueIdx, "start"));
        sectionKids.push(ol2);
        if (issueIdx >= 0 && g.k === issueIdx) sectionKids.push(issueNav(shard, issueIdx, "end"));
        els.results.appendChild(el("section", { class: "issue" }, sectionKids));
      });
    }
    if (hits.length > limit) {
      var more = el("button", { type: "button", class: "btn", text: "Show more (" + fmt(hits.length - limit) + " left)" });
      more.addEventListener("click", function () { limit += pageSize(); render(); });
      els.results.appendChild(el("div", { class: "pager" }, [more]));
    }
    focusTarget();
    finishIssueScroll();
  }

  function natPieces(s) {
    var bits = String(s).match(/\d+|\D+/g) || [];
    return bits.map(function (t) { return /^\d+$/.test(t) ? [0, parseInt(t, 10)] : [1, t]; });
  }

  function cmpNat(a, b) {
    var pa = natPieces(a), pb = natPieces(b);
    var n = Math.max(pa.length, pb.length);
    for (var i = 0; i < n; i++) {
      if (!pa[i]) return -1;
      if (!pb[i]) return 1;
      if (pa[i][0] !== pb[i][0]) return pa[i][0] - pb[i][0];
      if (pa[i][1] < pb[i][1]) return -1;
      if (pa[i][1] > pb[i][1]) return 1;
    }
    return 0;
  }

  function hitSortKey(file, it) {
    var iss = file.issues[it[0]];
    return [iss[0], iss[1], iss[2], iss[3], it[1]];
  }

  function cmpHits(a, b) {
    var ka = hitSortKey(a.file, a.it);
    var kb = hitSortKey(b.file, b.it);
    if (ka[0] !== kb[0]) return ka[0] - kb[0];
    if (ka[1] !== kb[1]) return ka[1] < kb[1] ? -1 : 1;
    var c = cmpNat(ka[2], kb[2]);
    if (c) return c;
    c = cmpNat(ka[3], kb[3]);
    if (c) return c;
    return ka[4] - kb[4];
  }

  function renderSearchHit(file, it) {
    var iss = file.issues[it[0]];
    var slug = file.journals[iss[0]];
    var jname = bySlug[slug] ? bySlug[slug].name : slug;
    var year = iss[1], vol = iss[2], issue = iss[3];
    var n = it[1], typ = it[2], src = it[3], title = it[4], authors = it[5];
    var href = buildQuery({
      journal: slug, year: year, volume: vol, issue: issue,
      type: typeFor(typ), q: "", item: String(n)
    });
    var where = jname + " · " + year + " · " + issueLabel(vol, issue);
    return el("li", { class: "item" }, [
      el("div", { class: "where" }, [el("a", { href: href, text: where })]),
      el("h2", { class: "title" + (title ? "" : " untitled") }, [
        el("span", { class: "badge " + TYPE_CLASS[typ], text: TYPE_LABEL[typ] }),
        el("a", { href: href, text: title || "(No title in the TOC record)" })
      ]),
      authorLine(authors, src)
    ]);
  }

  function renderSiteSearch() {
    var q = queryText();
    var gen = searchGen;
    var kinds = neededKinds();
    els.heading.textContent = "Results for “" + q + "”";
    document.title = "“" + q + "” — Journal Articles";
    var warm = kinds.every(function (k) { return !!searchCache[k]; });
    if (!warm) {
      els.count.textContent = state.type === "research"
        ? "Loading the search index…"
        : "Loading other and proceedings items…";
      els.results.setAttribute("aria-busy", "true");
    }
    Promise.all(kinds.map(loadSearchKind)).then(function (files) {
      if (gen !== searchGen) return;
      if (state.journal || queryText() !== q) return;
      els.results.removeAttribute("aria-busy");
      els.results.innerHTML = "";
      var terms = termsOf(q);
      var haveR = false, haveO = false;
      files.forEach(function (f) { if (f.kind === "research") haveR = true; else haveO = true; });
      var counts = { research: haveR ? 0 : null, other: haveO ? 0 : null, all: null };
      var hits = [];
      files.forEach(function (file) {
        for (var i = 0; i < file.items.length; i++) {
          if (!matches(file.hay[i], terms)) continue;
          var it = file.items[i];
          if (it[2] === "a") { if (counts.research != null) counts.research++; }
          else if (counts.other != null) counts.other++;
          if (typeOk(it[2])) hits.push({ file: file, it: it });
        }
      });
      if (haveR && haveO) counts.all = counts.research + counts.other;
      if (files.length > 1) hits.sort(cmpHits);
      setTypeCounts(counts);
      var typeWord = state.type === "research" ? "research articles" : state.type === "other" ? "other and proceedings items" : "items";
      els.count.textContent = fmt(hits.length) + " " + typeWord + " matching “" + q + "” in all journals.";
      els.results.appendChild(el("p", {
        class: "hint",
        text: "This searches titles and author-name strings. The same display name is not one person."
      }));
      if (!hits.length) {
        var empty = "No titles or author names match.";
        if (state.type === "research") empty = "No research articles match. Choose “Other and proceedings” or “All items” to include the rest.";
        else if (counts.all) empty = "No items of this type match. Try “All items”.";
        els.results.appendChild(el("p", { class: "empty", text: empty }));
        return;
      }
      var shown = hits.slice(0, limit);
      var ol = el("ol", { class: "items search-hits" });
      shown.forEach(function (h) { ol.appendChild(renderSearchHit(h.file, h.it)); });
      els.results.appendChild(el("section", { class: "issue", "aria-label": "Search results" }, [ol]));
      if (hits.length > limit) {
        var more = el("button", { type: "button", class: "btn", text: "Show more (" + fmt(hits.length - limit) + " left)" });
        more.addEventListener("click", function () { limit += pageSize(); render(); });
        els.results.appendChild(el("div", { class: "pager" }, [more]));
      }
    }).catch(function (e) {
      if (gen !== searchGen) return;
      els.results.removeAttribute("aria-busy");
      els.count.textContent = "Could not load the search index (" + e.message + "). Serve the site over HTTP.";
    });
  }

  function loadDoiIndex() {
    if (doiCache) return Promise.resolve(doiCache);
    if (doiInflight) return doiInflight;
    doiInflight = fetch("data/search/doi.json").then(function (r) {
      if (!r.ok) throw new Error("doi.json " + r.status);
      return r.json();
    }).then(function (d) {
      doiCache = d;
      return d;
    }).catch(function (e) {
      doiInflight = null;
      throw e;
    });
    return doiInflight;
  }

  function openDoi(rec) {
    var slug = doiCache && doiCache.journals ? doiCache.journals[rec[0]] : "";
    if (!slug) return;
    var typ = rec[5];
    journalFilter = "";
    state.journal = slug;
    state.year = String(rec[1]);
    state.volume = String(rec[2]);
    state.issue = String(rec[3]);
    state.item = String(rec[4]);
    state.q = "";
    state.type = state.type === "all" ? "all" : (typ === "a" ? "research" : "other");
    commit(false);
  }

  function showDoiMissing(doi) {
    els.results.removeAttribute("aria-busy");
    els.results.innerHTML = "";
    els.heading.textContent = "DOI not in this catalog";
    document.title = "DOI not in this catalog — Journal Articles";
    els.count.textContent = doi + " is not in this catalog.";
    setTypeCounts(null);
    els.results.appendChild(el("p", {
      class: "empty",
      text: doi + " is not in the 2012–2025 catalog. Nothing was added from outside this release."
    }));
  }

  function renderDoiLookup(doi) {
    var gen = searchGen;
    var immediate = doiImmediate;
    doiImmediate = false;
    els.yearRow.hidden = true;
    els.issueRow.hidden = true;
    els.crumbs.innerHTML = "";
    els.crumbs.appendChild(el("a", { href: "catalog.html", text: "All journals" }));
    els.crumbs.appendChild(document.createTextNode(" \u203a "));
    els.crumbs.appendChild(el("span", { text: "DOI" }));
    els.heading.textContent = "Looking up DOI";
    document.title = "Looking up DOI — Journal Articles";
    els.count.textContent = "Looking up " + doi + "\u2026";
    setTypeCounts(null);
    els.results.setAttribute("aria-busy", "true");
    loadDoiIndex().then(function (data) {
      if (gen !== searchGen) return;
      if (parseDoiQuery(queryText()) !== doi) return;
      var rec = data.items ? data.items[doi] : null;
      var delay = immediate || document.activeElement !== els.q ? 0 : 600;
      doiTimer = setTimeout(function () {
        doiTimer = null;
        if (gen !== searchGen) return;
        if (parseDoiQuery(queryText()) !== doi) return;
        if (rec) openDoi(rec);
        else showDoiMissing(doi);
      }, delay);
    }).catch(function (e) {
      if (gen !== searchGen) return;
      els.results.removeAttribute("aria-busy");
      els.count.textContent = "Could not load the DOI index (" + e.message + "). Serve the site over HTTP.";
    });
  }

  function render() {
    searchGen++;
    if (doiTimer) { clearTimeout(doiTimer); doiTimer = null; }
    syncControls();
    els.results.innerHTML = "";
    els.results.removeAttribute("aria-busy");
    var doi = parseDoiQuery(queryText());
    if (doi) {
      renderDoiLookup(doi);
      return;
    }
    var j = bySlug[state.journal];
    if (state.journal && !j) {
      crumbs(null);
      fillPicks(null);
      els.heading.textContent = "Journal not found";
      document.title = "Journal not found — Journal Articles";
      els.count.textContent = "";
      setTypeCounts(null);
      els.results.appendChild(el("p", { class: "empty", text: "No journal with the slug “" + state.journal + "” in this release." }));
      return;
    }
    crumbs(j);
    if (!j) {
      fillPicks(null);
      if (queryText()) renderSiteSearch();
      else renderJournalList();
      return;
    }
    els.count.textContent = "Loading " + j.name + "…";
    els.results.setAttribute("aria-busy", "true");
    fillPicks(null);
    loadShard(j.slug).then(function (shard) {
      if (state.journal !== shard.slug) return;
      els.results.removeAttribute("aria-busy");
      els.results.innerHTML = "";
      fillPicks(shard);
      renderShard(shard);
    }).catch(function (e) {
      els.results.removeAttribute("aria-busy");
      els.count.textContent = "Could not load this journal (" + e.message + ").";
    });
  }

  function copyText(text) {
    function legacy() {
      return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.top = "0";
      ta.style.left = "0";
      ta.style.width = "1px";
      ta.style.height = "1px";
      ta.style.fontSize = "16px";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.focus();
      ta.select();
      ta.setSelectionRange(0, text.length);
      var ok = false;
      try { ok = document.execCommand("copy"); } catch (err) { ok = false; }
      document.body.removeChild(ta);
      if (ok) resolve(); else reject(new Error("copy"));
      });
    }
    if (!(navigator.clipboard && navigator.clipboard.writeText)) return legacy();
    return new Promise(function (resolve, reject) {
      var settled = false;
      var timer = setTimeout(function () {
        if (settled) return;
        settled = true;
        reject(new Error("timeout"));
      }, 800);
      navigator.clipboard.writeText(text).then(function () {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        resolve();
      }, function () {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        legacy().then(resolve, reject);
      });
    });
  }

  function startCopy(b) {
    if (!b || b.getAttribute("data-state") === "busy" || b.getAttribute("data-state") === "copied") return;
    var doi = b.getAttribute("data-doi");
    var label = b.getAttribute("aria-label");
    b.setAttribute("data-state", "busy");
    b.textContent = "Copying…";
    copyText(doi).then(function () {
      b.textContent = "Copied";
      b.setAttribute("data-state", "copied");
      b.setAttribute("aria-label", "Copied");
      setTimeout(function () {
        if (b.getAttribute("data-state") === "copied") {
          b.textContent = "Copy DOI";
          b.removeAttribute("data-state");
          if (label) b.setAttribute("aria-label", label);
        }
      }, 1600);
    }, function () {
      var line = b.closest && b.closest(".doi-line");
      var link = line && line.querySelector("a.doi");
      if (link) {
        var sel = window.getSelection();
        var range = document.createRange();
        range.selectNodeContents(link);
        sel.removeAllRanges();
        sel.addRange(range);
      }
      b.textContent = "Selected";
      b.setAttribute("data-state", "selected");
    });
  }
  function copyFromEvent(e) {
    var b = e.target.closest && e.target.closest(".copy-doi");
    if (!b) return;
    if (e.type === "click") e.preventDefault();
    startCopy(b);
  }
  function closeCite(b) {
    b.setAttribute("aria-expanded", "false");
    var panel = document.getElementById(b.getAttribute("aria-controls"));
    if (panel) panel.setAttribute("hidden", "");
  }
  function toggleCite(b) {
    var open = b.getAttribute("aria-expanded") === "true";
    var others = els.results.querySelectorAll(".cite-btn[aria-expanded='true']");
    for (var i = 0; i < others.length; i++) if (others[i] !== b) closeCite(others[i]);
    if (open) { closeCite(b); return; }
    b.setAttribute("aria-expanded", "true");
    var panel = document.getElementById(b.getAttribute("aria-controls"));
    if (panel) panel.removeAttribute("hidden");
  }
  function startCiteCopy(b) {
    if (!b || b.getAttribute("data-state") === "busy" || b.getAttribute("data-state") === "copied") return;
    var field = b.closest && b.closest(".cite-field");
    var pre = field && field.querySelector(".cite-block");
    var text = pre ? pre.textContent : "";
    if (!text) return;
    var idle = b.getAttribute("data-label") || "Copy";
    var panel = b.closest(".cite-panel");
    var status = panel && panel.querySelector(".cite-status");
    function setStatus(msg) { if (status) status.textContent = msg; }
    b.setAttribute("data-state", "busy");
    b.textContent = "Copying\u2026";
    setStatus("Copying\u2026");
    copyText(text).then(function () {
      var done = idle === "Copy BibTeX" ? "BibTeX copied." : "Citation copied.";
      b.textContent = "Copied";
      b.setAttribute("data-state", "copied");
      b.setAttribute("aria-label", done);
      setStatus(done);
      setTimeout(function () {
        if (b.getAttribute("data-state") === "copied") {
          b.textContent = idle;
          b.removeAttribute("data-state");
          b.setAttribute("aria-label", idle);
        }
      }, 1600);
    }, function () {
      if (pre) {
        var sel = window.getSelection();
        var range = document.createRange();
        range.selectNodeContents(pre);
        sel.removeAllRanges();
        sel.addRange(range);
      }
      b.textContent = "Selected";
      b.setAttribute("data-state", "selected");
      setStatus("Could not copy. The text is selected.");
    });
  }
  function citeFromEvent(e) {
    var copyBtn = e.target.closest && e.target.closest(".copy-cite");
    if (copyBtn) {
      if (e.type === "click") e.preventDefault();
      startCiteCopy(copyBtn);
      return;
    }
    if (e.type !== "click") return;
    var citeBtn = e.target.closest && e.target.closest(".cite-btn");
    if (citeBtn) { toggleCite(citeBtn); return; }
    var step = e.target.closest && e.target.closest("a.issue-step");
    if (!step) return;
    if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
    e.preventDefault();
    goToIssue(step.getAttribute("href"));
  }
  els.results.addEventListener("pointerdown", function (e) {
    copyFromEvent(e);
    var copyBtn = e.target.closest && e.target.closest(".copy-cite");
    if (copyBtn) startCiteCopy(copyBtn);
  });
  els.results.addEventListener("click", function (e) {
    var nameLink = e.target.closest && e.target.closest("a.author-name");
    if (nameLink) {
      if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;
      e.preventDefault();
      journalFilter = "";
      state = {
        journal: "", year: "", volume: "", issue: "",
        type: "research", q: nameLink.getAttribute("data-name") || "", item: ""
      };
      commit(true);
      return;
    }
    copyFromEvent(e);
    citeFromEvent(e);
  });

  els.journal.addEventListener("focus", function () {
    combo.open = true;
    combo.active = -1;
    els.journal.select();
    renderCombo();
  });
  els.journal.addEventListener("input", function () {
    if (!state.journal) journalFilter = els.journal.value;
    combo.open = true;
    combo.active = -1;
    renderCombo();
    if (!state.journal && !queryText()) paintJournalList();
  });
  els.journal.addEventListener("search", function () {
    if (els.journal.value) return;
    journalFilter = "";
    if (state.journal) {
      state.journal = "";
      state.year = "";
      state.volume = "";
      state.issue = "";
      state.item = "";
      combo.open = false;
      commit(true);
    } else if (!queryText()) {
      paintJournalList();
    }
    renderCombo();
  });
  els.journal.addEventListener("keydown", function (e) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      combo.open = true;
      combo.active = Math.min(combo.active + 1, combo.matches.length - 1);
      renderCombo();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      combo.open = true;
      combo.active = Math.max(combo.active - 1, 0);
      renderCombo();
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (combo.active >= 0 && combo.matches[combo.active]) chooseJournal(combo.matches[combo.active].slug);
      else if (combo.matches.length === 1 && els.journal.value.trim() && els.journal.value.trim() !== selectedJournalName()) {
        chooseJournal(combo.matches[0].slug);
      }
    } else if (e.key === "Escape") {
      combo.open = false;
      combo.active = -1;
      if (state.journal) els.journal.value = selectedJournalName();
      renderCombo();
      els.journal.blur();
    }
  });
  els.journal.addEventListener("blur", function () {
    combo.open = false;
    if (els.jlist) els.jlist.hidden = true;
    els.journal.setAttribute("aria-expanded", "false");
    els.journal.removeAttribute("aria-activedescendant");
    if (state.journal && bySlug[state.journal]) els.journal.value = bySlug[state.journal].name;
    else els.journal.value = journalFilter;
  });

  els.year.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("button[data-year]");
    if (!b) return;
    state.year = b.getAttribute("data-year") || "";
    state.volume = "";
    state.issue = "";
    state.item = "";
    commit(true);
  });
  els.issue.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("button[data-issue]");
    if (!b) return;
    state.volume = b.getAttribute("data-volume") || "";
    state.issue = b.getAttribute("data-issue") || "";
    state.item = "";
    commit(true);
  });
  var timer = null;
  els.q.addEventListener("input", function (e) {
    if (e.inputType === "insertFromPaste" && parseDoiQuery(els.q.value)) doiImmediate = true;
    clearTimeout(timer);
    timer = setTimeout(function () {
      state.q = els.q.value;
      state.item = "";
      commit(false);
    }, 200);
  });
  els.q.addEventListener("keydown", function (e) {
    if (e.key !== "Enter") return;
    if (!parseDoiQuery(els.q.value)) return;
    e.preventDefault();
    doiImmediate = true;
    clearTimeout(timer);
    state.q = els.q.value;
    state.item = "";
    commit(false);
  });
  els.types.addEventListener("click", function (e) {
    var b = e.target.closest && e.target.closest("button[data-type]");
    if (!b) return;
    state.type = b.getAttribute("data-type");
    state.item = "";
    commit(false);
  });
  els.reset.addEventListener("click", function () {
    journalFilter = "";
    state = { journal: state.journal, year: "", volume: "", issue: "", type: "research", q: "", item: "" };
    commit(true);
  });
  els.all.addEventListener("click", function () {
    journalFilter = "";
    state.journal = "";
    state.year = "";
    state.volume = "";
    state.issue = "";
    state.item = "";
    commit(true);
  });
  window.addEventListener("popstate", function () {
    state = readState();
    journalFilter = "";
    limit = pageSize();
    render();
  });

  loadIndex().then(function (d) {
    index = d;
    d.journals.forEach(function (j) { bySlug[j.slug] = j; });
    render();
  }).catch(function (e) {
    els.count.textContent = "Could not load the journal index (" + e.message + "). Serve the site over HTTP, e.g. python -m http.server.";
  });
})();
