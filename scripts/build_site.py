#!/usr/bin/env python3
"""Build the Journal Articles static site from the public TOC freeze.

Only input: releases/articles_toc_2012_2025/ (articles.csv, issues.csv,
journals.csv, coverage.csv, summary.json, README.md).
Output: site/ (static GitHub Pages site, relative asset paths only).

No person_ids, conflict files, or QS handoffs are read or written.
"""
from __future__ import annotations

import csv
import html
import json
import shutil
import sys
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FREEZE = ROOT / "releases" / "articles_toc_2012_2025"
SRC = ROOT / "src"
SITE = ROOT / "site"

ARTICLE_SITE = "https://kochiuyu.github.io/econ-journal-authors/"
ARTICLE_REPO = "https://github.com/kochiuyu/econ-journal-authors"

TYPE_CODE = {"article": "a", "other": "o", "proceedings": "p"}
SRC_CODE = {"spine": "s", "openalex_via_registry": "o", "openalex": "d", "crossref": "c",
            "toc_official_qe": "q", "": ""}
FORBIDDEN = ("person_id", "conflict", "qs_", "handoff", "spine_id")

PUBLISHER_LABEL = {
    "aea": "AEA", "elsevier": "Elsevier", "wiley": "Wiley", "springer": "Springer",
    "oup": "Oxford UP", "cambridge": "Cambridge UP", "uchicago": "U. Chicago Press",
    "mit": "MIT Press", "tandfonline": "Taylor & Francis", "uwpress": "U. Wisconsin Press",
    "econometric_society": "Econometric Society",
}


def read_csv(name):
    with open(FREEZE / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def display_authors(raw: str, source: str, stats: Counter) -> str:
    """Return the author string to display, without rewriting names.

    Spine rows from some publishers store the printed byline followed by the
    individual names, e.g. "A, B, and C; A; B; C". When the first segment is
    such a byline (contains " and " and every later segment appears verbatim in
    it), show just the printed byline. Otherwise show the stored string as-is.
    """
    if not raw:
        stats["authors_empty"] += 1
        return ""
    if source == "spine":
        segs = [s.strip() for s in raw.split(";")]
        if len(segs) >= 3 and " and " in segs[0] and all(s and s in segs[0] for s in segs[1:]):
            stats["spine_byline_prefix"] += 1
            return segs[0]
        stats["spine_as_stored"] += 1
        return raw
    stats[f"{source}_as_stored"] += 1
    return raw


def natural_key(s: str):
    """Sort '2' before '10' and 'S1' after numbers; keeps labels unchanged."""
    import re
    return [(0, int(t), "") if t.isdigit() else (1, 0, t) for t in re.findall(r"\d+|\D+", s or "")]


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def fmt(n) -> str:
    return f"{int(n):,}"


def page(title, description, active, body, canonical_path="", extra_head="", scripts=""):
    nav_items = [("./", "Home", "home"), ("catalog.html", "Catalog", "catalog"),
                 ("index.html#journals", "Journals", "journals"), ("index.html#about", "About", "about"),
                 (ARTICLE_REPO + "#readme", "GitHub", "github")]
    nav = "\n        ".join(
        f'<a href="{esc(h)}"{" aria-current=\"page\"" if k == active else ""}>{esc(l)}</a>'
        for h, l, k in nav_items)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <link rel="canonical" href="{ARTICLE_SITE}{canonical_path}">
  <meta property="og:title" content="{esc(title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta property="og:type" content="website">
  <!-- Project Pages base: /econ-journal-authors/. Asset URLs are relative so the
       site also works under `python -m http.server` from site/. -->
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%23142833'/%3E%3Ctext x='16' y='22' text-anchor='middle' font-family='Georgia,serif' font-size='15' fill='%23f4f1ea'%3EJa%3C/text%3E%3C/svg%3E">
  {extra_head or '<link rel="stylesheet" href="style.css">'}
</head>
<body>
  <a class="skip" href="#main">Skip to content</a>
  <header class="topbar">
    <div class="wrap bar">
      <a class="brand" href="./">
        <span class="logo" aria-hidden="true">Ja</span>
        <span>
          <span class="t1">Journal Articles</span>
          <span class="t2">49 core economics journals · 2012–2025</span>
        </span>
      </a>
      <nav class="nav" aria-label="Site">
        {nav}
      </nav>
    </div>
  </header>

  <main class="wrap" id="main" tabindex="-1">
{body}
  </main>

  <footer class="footer wrap">
    <p>
      Article catalog · TOC freeze <code>articles_toc_2012_2025</code>.
      Repository: <a href="{ARTICLE_REPO}">kochiuyu/econ-journal-authors</a>.
      Compiled catalog, site, and documentation: <a href="https://creativecommons.org/licenses/by/4.0/">CC-BY-4.0</a>.
      Titles and bylines remain the publishers’.
    </p>
  </footer>
{scripts}
</body>
</html>
"""


ABOUT_HTML = """    <section class="prose" id="about" aria-labelledby="about-title">
      <h2 id="about-title">About this release</h2>
      <p>
        This is the first public release of the article catalog: the publisher
        table of contents (TOC) for the core 49 economics journals, {window}. The TOC is the article list.
        Every item in an issue is kept. Research articles are marked <em>Research article</em>; front matter,
        editorials, comments, replies, and similar items are marked <em>Other</em>; conference papers are
        marked <em>Proceedings</em>. The catalog shows research articles first, and the filter shows the rest.
      </p>
      <p>
        Author names are shown as recorded, with their source. <strong>As printed in the TOC</strong> means the
        names come from the publisher’s TOC. <strong>OpenAlex (name only)</strong> means the TOC had no names and the
        names come from OpenAlex names recorded by the collector. <strong>OpenAlex by DOI (name only)</strong> means neither the TOC nor that record had names, so the names come from the OpenAlex work for the item’s DOI. <strong>Crossref by DOI (name only)</strong> means the names come from the Crossref record for the DOI. <strong>From the official article page</strong> means the names were read from the journal’s own article page (Quantitative Economics). All are names only, not linked identities. When neither source has names, none are shown.
        Names are not merged, cleaned, or completed. For TOC bylines stored as “A, B, and C” followed by each
        name, the printed byline is shown.
      </p>
      <p>
        Not in this release: a person registry, author identifiers, affiliations, author pages, and any
        working files from the collection process. Affiliation panels and unique-author pages are planned
        for later releases. DOIs link to <code>doi.org</code>. When a TOC record has no DOI, the catalog says so.
      </p>
      <p>
        The compiled catalog, site code, and documentation are licensed under
        <a href="https://creativecommons.org/licenses/by/4.0/">CC-BY-4.0</a>.
        Article titles, author bylines, and publisher tables of contents remain the publishers’.
      </p>
      <p class="small">
        Built {built} (Asia/Taipei) from <code>releases/articles_toc_2012_2025/</code> with
        <code>python scripts/build_site.py</code>. Journal-level tables are under <a href="downloads/">downloads</a>
        (<a href="downloads/journals.csv">journals.csv</a>, <a href="downloads/issues.csv">issues.csv</a>,
        <a href="downloads/coverage.csv">coverage.csv</a>, <a href="downloads/authors_missing_by_journal_year.csv">authors_missing_by_journal_year.csv</a>, <a href="downloads/summary.json">summary.json</a>).
        The repository is <a href="{repo}">kochiuyu/econ-journal-authors</a>.
      </p>
    </section>
"""


def main() -> int:
    summary = json.loads((FREEZE / "summary.json").read_text(encoding="utf-8"))
    articles = read_csv("articles.csv")
    issues = read_csv("issues.csv")
    journals = read_csv("journals.csv")
    coverage = read_csv("coverage.csv")

    # ---- Verify the freeze against its own summary ------------------------
    checks = {
        "journals": len(journals),
        "journal_years": len(coverage),
        "issues": len(issues),
        "items": len(articles),
        "research_articles": sum(r["is_research"] == "1" for r in articles),
        "other_items": sum(r["is_research"] != "1" for r in articles),
        "items_with_doi": sum(bool(r["doi"]) for r in articles),
        "items_with_authors": sum(bool(r["authors"]) for r in articles),
        "research_with_authors": sum(bool(r["authors"]) and r["is_research"] == "1" for r in articles),
    }
    bad = {k: (v, summary[k]) for k, v in checks.items() if v != summary[k]}
    src_counts = Counter(r["authors_source"] for r in articles if r["authors_source"])
    if dict(src_counts) != summary["authors_source_counts"]:
        bad["authors_source_counts"] = (dict(src_counts), summary["authors_source_counts"])
    if summary.get("person_ids_included") is not False:
        bad["person_ids_included"] = summary.get("person_ids_included")
    for r in articles:
        t = r["article_type"]
        if t not in TYPE_CODE or (t == "article") != (r["is_research"] == "1"):
            bad.setdefault("type_mismatch", 0)
            bad["type_mismatch"] += 1
        if r["authors_source"] not in SRC_CODE or bool(r["authors"]) != bool(r["authors_source"]):
            bad.setdefault("authors_source_mismatch", 0)
            bad["authors_source_mismatch"] += 1
    if bad:
        print("Freeze does not match summary.json:", bad, file=sys.stderr)
        return 1

    # ---- Fresh output dir -------------------------------------------------
    if SITE.exists():
        shutil.rmtree(SITE)
    (SITE / "data" / "journals").mkdir(parents=True)
    (SITE / "downloads").mkdir()

    # ---- Shards -----------------------------------------------------------
    stats = Counter()
    issues_by_j: dict[str, list] = OrderedDict()
    issue_index: dict[tuple, int] = {}
    # Order issues by year, volume, issue (natural sort: 2 before 10).
    issues_sorted = sorted(issues, key=lambda r: (r["journal_slug"], int(r["year"]),
                                                  natural_key(r["volume"]), natural_key(r["issue"])))
    for r in issues_sorted:
        lst = issues_by_j.setdefault(r["journal_slug"], [])
        issue_index[(r["journal_slug"], r["year"], r["volume"], r["issue"])] = len(lst)
        lst.append([r["year"], r["volume"], r["issue"], r["toc_url"],
                    int(r["items"]), int(r["research_articles"]), int(r["other_items"])])

    items_by_j: dict[str, list] = {}
    for r in articles:  # articles.csv order = TOC order within an issue
        k = (r["journal_slug"], r["year"], r["volume"], r["issue"])
        items_by_j.setdefault(r["journal_slug"], []).append([
            issue_index[k], r["title"], r["doi"], r["pages"], TYPE_CODE[r["article_type"]],
            display_authors(r["authors"], r["authors_source"], stats),
            SRC_CODE[r["authors_source"]], r["publisher_url"],
        ])

    jindex = []
    shard_sizes = {}
    names = {j["journal_slug"]: j["display_name"] for j in journals}
    for j in sorted(journals, key=lambda x: x["display_name"].lower()):
        slug = j["journal_slug"]
        items = items_by_j.get(slug, [])
        # Keep issue grouping stable even if articles.csv interleaves issues.
        items.sort(key=lambda it: it[0])
        shard = {"slug": slug, "name": names[slug],
                 "fields": {"issues": ["year", "volume", "issue", "toc_url", "items", "research", "other"],
                            "items": ["issue_idx", "title", "doi", "pages", "type", "authors", "authors_source",
                                      "publisher_url"]},
                 "codes": {"type": {"a": "article", "o": "other", "p": "proceedings"},
                           "authors_source": {"s": "spine (as printed in TOC)",
                                              "o": "openalex_via_registry (name only)",
                                              "d": "openalex by DOI (name only)",
                                              "c": "crossref by DOI (name only)",
                                              "q": "official article page (Quantitative Economics)", "": "none"}},
                 "issues": issues_by_j[slug], "items": items}
        out = SITE / "data" / "journals" / f"{slug}.json"
        out.write_text(json.dumps(shard, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        shard_sizes[slug] = out.stat().st_size
        cov = [c for c in coverage if c["journal_slug"] == slug]
        jindex.append({
            "slug": slug, "name": names[slug], "issn_l": j["issn_l"], "publisher": j["publisher_family"],
            "year_start": int(j["year_start"]), "year_end": int(j["year_end"]),
            "years": len(cov), "issues": int(j["issues"]), "items": int(j["items"]),
            "research": int(j["research_articles"]), "other": int(j["other_items"]),
        })
        assert len(items) == int(j["items"]), slug

    meta = {k: summary[k] for k in ("window", "journals", "journal_years", "issues", "items",
                                    "research_articles", "other_items", "items_with_doi",
                                    "items_with_authors", "research_with_authors", "authors_source_counts")}
    meta["built"] = summary["created_at"]
    (SITE / "data" / "journals.json").write_text(
        json.dumps({"meta": meta, "journals": jindex}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")

    # ---- Downloads (journal-level tables only) ---------------------------
    for name in ("journals.csv", "issues.csv", "coverage.csv", "authors_missing_by_journal_year.csv", "summary.json", "README.md"):
        shutil.copy2(FREEZE / name, SITE / "downloads" / name)
    dl_rows = "\n".join(f'      <li><a href="{n}">{n}</a></li>' for n in
                        ("journals.csv", "issues.csv", "coverage.csv", "authors_missing_by_journal_year.csv", "summary.json", "README.md"))
    (SITE / "downloads" / "index.html").write_text(
        page("Downloads — Journal Articles", "Journal-level tables from the TOC freeze.", "",
             f"""    <h1 class="page-title">Downloads</h1>
    <section class="prose">
    <p>Journal-, issue-, and year-level tables from the <code>articles_toc_2012_2025</code> freeze.
    The article-level data is in the per-journal files under <a href="../data/journals/">data/journals/</a>
    used by the <a href="../catalog.html">catalog</a>.</p>
    <ul>
{dl_rows}
    </ul>
    <p><a href="../">Back to the hub</a></p>
    </section>""").replace('href="style.css"', 'href="../style.css"').replace('href="./"', 'href="../"')
        .replace('href="catalog.html"', 'href="../catalog.html"').replace('href="index.html#', 'href="../index.html#'),
        encoding="utf-8")

    # ---- Static assets ----------------------------------------------------
    shutil.copy2(SRC / "style.css", SITE / "style.css")
    shutil.copy2(SRC / "catalog.js", SITE / "catalog.js")
    (SITE / ".nojekyll").write_text("", encoding="utf-8")

    built = summary["created_at"][:10]
    about = ABOUT_HTML.format(window=summary["window"].replace("-", "–"),
                              built=built, repo=ARTICLE_REPO)

    # ---- Hub --------------------------------------------------------------
    s = summary
    src = s["authors_source_counts"]
    rows = []
    for j in jindex:
        yrs = f'{j["year_start"]}–{j["year_end"]}'
        rows.append(
            f'          <tr><td><a class="jname" href="catalog.html?journal={esc(j["slug"])}">{esc(j["name"])}</a></td>'
            f'<td>{esc(PUBLISHER_LABEL.get(j["publisher"], j["publisher"]))}</td>'
            f'<td class="num">{yrs}</td><td class="num">{fmt(j["years"])}</td><td class="num">{fmt(j["issues"])}</td>'
            f'<td class="num">{fmt(j["items"])}</td><td class="num">{fmt(j["research"])}</td>'
            f'<td class="num">{fmt(j["other"])}</td></tr>')
    hub_body = f"""    <h1 class="sr-only">Journal Articles — 49 core economics journals, 2012–2025</h1>
    <p class="intro">
      The publisher tables of contents for 49 core economics journals,
      2012–2025. You can browse by journal, then by year and issue. Each item has its title, DOI, item type, and author names with their source.
      AER: Insights starts in 2019, so 2012–2018 have 48 journals.
      This release has no person registry: names come from the TOC, the journal’s article pages, OpenAlex, or Crossref (names only).
    </p>

    <section class="stats" aria-label="Release totals">
      <div class="stat"><div class="n">{fmt(s["items"])}</div><div class="l">TOC items</div>
        <div class="sub">{fmt(s["issues"])} issues · {fmt(s["journal_years"])} journal-years</div></div>
      <div class="stat"><div class="n">{fmt(s["research_articles"])}</div><div class="l">Research articles</div>
        <div class="sub">{fmt(s["other_items"])} other and proceedings items</div></div>
      <div class="stat"><div class="n">{fmt(s["items_with_doi"])}</div><div class="l">Items with a DOI</div>
        <div class="sub">{fmt(s["items"] - s["items_with_doi"])} TOC records without one</div></div>
      <div class="stat"><div class="n">{fmt(s["research_with_authors"])}</div><div class="l">Research articles with names</div>
        <div class="sub">{fmt(s["items_with_authors"])} items with names: {fmt(src.get("spine", 0) + src.get("toc_official_qe", 0))} from the publisher, {fmt(src.get("openalex_via_registry", 0) + src.get("openalex", 0))} from OpenAlex, {fmt(src.get("crossref", 0))} from Crossref</div></div>
    </section>

    <h2 class="section-title">Explore</h2>
    <div class="explore">
      <a href="catalog.html"><span class="label">Catalog</span>
        <span class="sub">Choose a journal, then a year and an issue. You can search titles and names within the journal.</span></a>
      <a href="#journals"><span class="label">Journals</span>
        <span class="sub">All {s["journals"]} journals with years, issues, and research and other counts.</span></a>
    </div>

    <h2 class="section-title" id="journals">Journals</h2>
    <div class="tbl-wrap">
      <table>
        <caption>{s["journals"]} journals. Counts are TOC items in the {s["window"].replace("-", "–")} freeze. A journal name opens its catalog.</caption>
        <thead><tr><th scope="col">Journal</th><th scope="col">Publisher</th><th scope="col" class="num">Years</th>
          <th scope="col" class="num">Journal-years</th><th scope="col" class="num">Issues</th><th scope="col" class="num">Items</th>
          <th scope="col" class="num">Research</th><th scope="col" class="num">Other</th></tr></thead>
        <tbody>
{chr(10).join(rows)}
        </tbody>
      </table>
    </div>

{about}"""
    (SITE / "index.html").write_text(
        page("Journal Articles — 49 core economics journals, 2012–2025",
             "TOC-first article catalog for the core 49 economics journals, 2012–2025: titles, DOIs, item types, and author names by source.",
             "home", hub_body), encoding="utf-8")

    # ---- Catalog ----------------------------------------------------------
    cat_body = """    <nav class="crumbs" id="crumbs" aria-label="Breadcrumb"></nav>
    <h1 class="page-title" id="results-title">Catalog</h1>
    <form class="controls" role="search" aria-label="Browse the catalog" onsubmit="return false">
      <div class="row">
        <div class="field"><label class="lbl" for="f-journal">Journal</label>
          <select id="f-journal"><option value="">Loading…</option></select></div>
        <div class="field"><label class="lbl" for="f-year">Year</label>
          <select id="f-year" disabled><option value="">All years</option></select></div>
        <div class="field"><label class="lbl" for="f-issue">Issue</label>
          <select id="f-issue" disabled><option value="">All issues</option></select></div>
        <div class="field grow"><label class="lbl" for="f-q">Search titles and names in this journal</label>
          <input type="search" id="f-q" autocomplete="off" placeholder="e.g. minimum wage, Duflo"></div>
      </div>
      <div class="row">
        <fieldset class="chips" id="f-type">
          <legend class="lbl">Item type</legend>
          <button type="button" class="chip" data-type="research" aria-pressed="true">Research articles<span class="c"></span></button>
          <button type="button" class="chip" data-type="other" aria-pressed="false">Other and proceedings<span class="c"></span></button>
          <button type="button" class="chip" data-type="all" aria-pressed="false">All items<span class="c"></span></button>
        </fieldset>
        <button type="button" class="btn" id="f-reset">Reset filters</button>
      </div>
      <p class="hint">Names are labelled by source. <em>As printed in the TOC</em> means the publisher’s TOC. <em>OpenAlex</em>, <em>OpenAlex by DOI</em>, and <em>Crossref by DOI</em> mean names from those databases, used when the TOC had none. <em>Official article page</em> means the journal’s own article page.
        Items without names show none. Only the selected journal is downloaded.</p>
    </form>
    <p class="count" id="count" role="status" aria-live="polite"></p>
    <div id="results"></div>
"""
    (SITE / "catalog.html").write_text(
        page("Catalog — Journal Articles",
             "Browse the core 49 TOC by journal, year, and issue.", "catalog", cat_body,
             canonical_path="catalog.html", scripts='  <script src="catalog.js"></script>'),
        encoding="utf-8")

    # ---- 404 (inline CSS so it styles at any depth) -----------------------
    css = (SRC / "style.css").read_text(encoding="utf-8")
    body404 = """    <h1 class="page-title">Page not found</h1>
    <section class="prose">
      <p>This address is not part of the Journal Articles catalog.</p>
      <p><a id="home-link" href="./">Go to the hub</a> or <a id="cat-link" href="catalog.html">open the catalog</a>.</p>
    </section>"""
    fix = """  <script>
    /* GitHub Pages serves 404.html at any depth; point links at the project base. */
    (function () {
      var m = location.pathname.match(/^\\/econ-journal-authors\\//);
      var base = m ? m[0] : "./";
      document.querySelectorAll('a[href="./"], a[href="catalog.html"], a[href^="index.html"]').forEach(function (a) {
        a.setAttribute("href", base + a.getAttribute("href").replace(/^\\.\\//, ""));
      });
    })();
  </script>"""
    (SITE / "404.html").write_text(
        page("Not found — Journal Articles", "Page not found.", "", body404,
             extra_head="<style>\n" + css + "\n  </style>", scripts=fix), encoding="utf-8")

    # ---- Safety scan --------------------------------------------------------
    leaks = []
    for p in SITE.rglob("*"):
        if p.is_file():
            low_name = p.name.lower()
            if any(f in low_name for f in FORBIDDEN):
                leaks.append(str(p))
            if p.suffix in (".json", ".csv"):
                head = p.read_text(encoding="utf-8")
                if "person_id" in head and p.name != "summary.json":
                    leaks.append(f"{p}: person_id")
    csv_cols = set()
    for n in ("journals.csv", "issues.csv", "coverage.csv", "authors_missing_by_journal_year.csv"):
        with open(SITE / "downloads" / n, newline="", encoding="utf-8") as f:
            csv_cols |= set(next(csv.reader(f)))
    leaks += [c for c in csv_cols if any(f in c.lower() for f in FORBIDDEN)]
    if leaks:
        print("Forbidden content in site/:", leaks, file=sys.stderr)
        return 1

    total = sum(shard_sizes.values())
    big = max(shard_sizes, key=shard_sizes.get)
    print(f"Built {SITE}")
    print(f"  {len(jindex)} journals, {len(issues)} issues, {len(articles)} items")
    print(f"  shards: {total/1e6:.1f} MB total; largest {big} {shard_sizes[big]/1e6:.2f} MB")
    print(f"  authors display: {dict(stats)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
