#!/usr/bin/env python3
"""Build the Journal Articles static site from the public TOC freeze.

Only input: releases/articles_toc_2012_2025/ (articles.csv, issues.csv,
journals.csv, coverage.csv, summary.json, README.md).
Output: site/ (static GitHub Pages site, relative asset paths only).

No person_ids, conflict files, or QS handoffs are read or written.
Also writes site/data/search/{research,other}.json, a title-and-author
index for site-wide search. It uses the same display names as the shards.
Also writes site/data/search/doi.json, a compact DOI-to-issue map.
DOIs are lowercased. The file has no titles, names, or person ids.
"""
from __future__ import annotations

import csv
import gzip
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


def public_readme(text: str) -> str:
    """Drop editor-site wording from the public copy of the freeze README."""
    kept = []
    for line in text.splitlines(keepends=True):
        if "econ-journal-dispersion" in line or "Geographic Dispersion" in line:
            continue
        kept.append(line)
    return "".join(kept)


def write_search_partition(path: Path, jindex, issues_by_j, rows):
    """Compact title/author index. rows are (slug, issue_idx, n, type, src, title, authors)."""
    slug_index = {j["slug"]: i for i, j in enumerate(jindex)}
    used = {}
    issues_out = []
    items_out = []
    for slug, issue_idx, n, typ, src, title, authors in rows:
        key = (slug, issue_idx)
        if key not in used:
            meta = issues_by_j[slug][issue_idx]
            used[key] = len(issues_out)
            issues_out.append([slug_index[slug], meta[0], meta[1], meta[2]])
        items_out.append([used[key], n, typ, src, title, authors])
    obj = {
        "fields": {
            "issues": ["journal", "year", "volume", "issue"],
            "items": ["issue", "n", "type", "authors_source", "title", "authors"],
        },
        "codes": {
            "type": {"a": "article", "o": "other", "p": "proceedings"},
            "authors_source": {
                "s": "spine (as printed in TOC)",
                "o": "openalex_via_registry (name only)",
                "d": "openalex by DOI (name only)",
                "c": "crossref by DOI (name only)",
                "q": "official article page (Quantitative Economics)",
                "": "none",
            },
        },
        "journals": [j["slug"] for j in jindex],
        "issues": issues_out,
        "items": items_out,
    }
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw, obj


def check_search(research_obj, other_obj, summary):
    """Fail the build if the index drifts from the freeze or rewrites a known byline."""
    r_items = research_obj["items"]
    o_items = other_obj["items"]
    problems = []
    if len(r_items) != summary["research_articles"]:
        problems.append(f"research items {len(r_items)} != {summary['research_articles']}")
    if len(o_items) != summary["other_items"]:
        problems.append(f"other items {len(o_items)} != {summary['other_items']}")
    if any(it[2] != "a" for it in r_items):
        problems.append("research index contains a non-research row")
    if any(it[2] == "a" for it in o_items):
        problems.append("other index contains a research row")
    title = "The Short- and Long-Term Career Effects of Graduating in a Recession"
    hits = [it for it in r_items if it[4] == title]
    if len(hits) != 1:
        problems.append(f"known title hits {len(hits)}")
    else:
        iss = research_obj["issues"][hits[0][0]]
        slug = research_obj["journals"][iss[0]]
        if (slug, iss[1], iss[2], iss[3], hits[0][1]) != ("aej-applied-economics", "2012", "4", "1", 1):
            problems.append(f"known title location {(slug, iss[1], iss[2], iss[3], hits[0][1])}")
        if ";" in hits[0][5] or "Philip Oreopoulos" not in hits[0][5]:
            problems.append("TOC byline prefix was not applied to the known title")
    micro = "The Miracle of Microfinance? Evidence from a Randomized Evaluation"
    duflo = [it for it in r_items if it[4] == micro and "Duflo" in (it[5] or "")]
    if len(duflo) != 1:
        problems.append(f"Duflo microfinance hits {len(duflo)}")
    else:
        iss = research_obj["issues"][duflo[0][0]]
        slug = research_obj["journals"][iss[0]]
        if (slug, iss[1], iss[2], iss[3], duflo[0][1]) != ("aej-applied-economics", "2015", "7", "1", 2):
            problems.append(f"Duflo location {(slug, iss[1], iss[2], iss[3], duflo[0][1])}")
        if ";" in duflo[0][5]:
            problems.append("Duflo byline was not shortened to the printed byline")
    return problems


def write_doi_index(path: Path, jindex, issues_by_j, rows):
    """Compact DOI lookup. rows are (doi_lower, slug, issue_idx, n, type).

    Values are [journal index, year, volume, issue, n, type]. n is the
    0-based TOC position used by item= links. No titles or author names.
    """
    slug_index = {j["slug"]: i for i, j in enumerate(jindex)}
    items = {}
    dup = []
    for doi, slug, issue_idx, n, typ in rows:
        meta = issues_by_j[slug][issue_idx]
        key = doi.strip().lower()
        rec = [slug_index[slug], meta[0], meta[1], meta[2], n, typ]
        if key in items:
            dup.append(key)
        items[key] = rec
    obj = {
        "fields": ["journal", "year", "volume", "issue", "n", "type"],
        "journals": [j["slug"] for j in jindex],
        "items": items,
    }
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    return raw, obj, dup


def check_doi(doi_obj, summary):
    """Fail if the DOI map drifts from the freeze or misses a known item."""
    items = doi_obj["items"]
    journals = doi_obj["journals"]
    problems = []
    if len(items) != summary["items_with_doi"]:
        problems.append(f"doi items {len(items)} != {summary['items_with_doi']}")

    def locate(doi):
        rec = items.get(doi.strip().lower())
        if not rec:
            return None
        return (journals[rec[0]], rec[1], rec[2], rec[3], rec[4], rec[5])

    expected = {
        "10.1257/aer.20161079": ("aer", "2018", "108", "1", 1, "a"),
        "10.1257/AER.20161079": ("aer", "2018", "108", "1", 1, "a"),
        "10.1257/app.20130533": ("aej-applied-economics", "2015", "7", "1", 2, "a"),
        "10.1017/S0266466611000119": None,  # filled below if present; case must fold
    }
    aer = locate("10.1257/aer.20161079")
    if aer != expected["10.1257/aer.20161079"]:
        problems.append(f"Bergemann DOI {aer}")
    if locate("10.1257/AER.20161079") != expected["10.1257/aer.20161079"]:
        problems.append("mixed-case AER DOI did not fold")
    duflo = locate("10.1257/app.20130533")
    if duflo != expected["10.1257/app.20130533"]:
        problems.append(f"Duflo DOI {duflo}")
    folded = locate("10.1017/s0266466611000119")
    if folded is None:
        problems.append("known mixed-case DOI missing after folding")
    elif folded[0] != "econometric-theory":
        problems.append(f"mixed-case DOI journal {folded}")
    if any(not key.startswith("10.") or key != key.lower() for key in items):
        problems.append("DOI key was not a lowercased 10. prefix")
    return problems


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
  {extra_head or '<link rel="stylesheet" href="style.css?v=6">'}
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
        In an issue list, each name is a link labeled “Search for this name.” It searches the catalog for that
        name string. The same display name is not one person, and there is no author page.
      </p>
      <p>
        Not in this release: a person registry, author identifiers, affiliations, author pages, and any
        working files from the collection process. Affiliation panels and unique-author pages are planned
        for later releases. DOIs link to <code>doi.org</code>. When a TOC record has no DOI, the catalog says so.
        A DOI pasted into search opens the catalog item when that DOI is already in this release.
        A DOI that is not in the release is reported as missing. The site does not fetch or invent a record.
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
        Searching all journals uses <code>data/search/</code>, a title-and-author index built from the same freeze, not the raw article table.
        DOI lookup uses <code>data/search/doi.json</code>, a location map from the same freeze.
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
    search_rows = []
    doi_rows = []
    shard_sizes = {}
    names = {j["journal_slug"]: j["display_name"] for j in journals}
    for j in sorted(journals, key=lambda x: x["display_name"].lower()):
        slug = j["journal_slug"]
        items = items_by_j.get(slug, [])
        # Keep issue grouping stable even if articles.csv interleaves issues.
        items.sort(key=lambda it: it[0])
        seq = Counter()
        for it in items:
            n = seq[it[0]]
            seq[it[0]] += 1
            # Same strings the shard displays: title, authors, source, type, TOC position.
            search_rows.append((slug, it[0], n, it[4], it[6], it[1], it[5]))
            if it[2] and it[2].strip():
                doi_rows.append((it[2].strip().lower(), slug, it[0], n, it[4]))
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

    # ---- Site-wide search index (titles + display names only) -----------
    research_raw, research_obj = write_search_partition(
        SITE / "data" / "search" / "research.json", jindex, issues_by_j,
        [r for r in search_rows if r[3] == "a"])
    other_raw, other_obj = write_search_partition(
        SITE / "data" / "search" / "other.json", jindex, issues_by_j,
        [r for r in search_rows if r[3] != "a"])
    search_problems = check_search(research_obj, other_obj, summary)
    if search_problems:
        print("Search index check failed:", search_problems, file=sys.stderr)
        return 1
    doi_raw, doi_obj, doi_dups = write_doi_index(
        SITE / "data" / "search" / "doi.json", jindex, issues_by_j, doi_rows)
    if doi_dups:
        print("Duplicate DOIs in lookup:", doi_dups[:5], file=sys.stderr)
        return 1
    doi_problems = check_doi(doi_obj, summary)
    if doi_problems:
        print("DOI index check failed:", doi_problems, file=sys.stderr)
        return 1
    for blob, label in ((research_raw, "research"), (other_raw, "other"), (doi_raw, "doi")):
        if b"person_id" in blob or b"spine_id" in blob:
            print(f"Search index {label} contains a forbidden identifier", file=sys.stderr)
            return 1
    search_sizes = {
        "research": (len(research_raw), len(gzip.compress(research_raw, 9))),
        "other": (len(other_raw), len(gzip.compress(other_raw, 9))),
        "doi": (len(doi_raw), len(gzip.compress(doi_raw, 9))),
    }

    # ---- Downloads (journal-level tables only) ---------------------------
    for name in ("journals.csv", "issues.csv", "coverage.csv", "authors_missing_by_journal_year.csv", "summary.json", "README.md"):
        dest = SITE / "downloads" / name
        if name == "README.md":
            dest.write_text(public_readme((FREEZE / name).read_text(encoding="utf-8")), encoding="utf-8")
        else:
            shutil.copy2(FREEZE / name, dest)
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
    </section>""").replace('href="style.css?v=6"', 'href="../style.css?v=6"').replace('href="./"', 'href="../"')
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
            f'          <tr><td data-label="Journal"><a class="jname" href="catalog.html?journal={esc(j["slug"])}">{esc(j["name"])}</a></td>'
            f'<td class="num" data-label="Publisher">{esc(PUBLISHER_LABEL.get(j["publisher"], j["publisher"]))}</td>'
            f'<td class="num" data-label="Years">{yrs}</td><td class="num" data-label="Journal-years">{fmt(j["years"])}</td>'
            f'<td class="num" data-label="Issues">{fmt(j["issues"])}</td><td class="num" data-label="Items">{fmt(j["items"])}</td>'
            f'<td class="num" data-label="Research">{fmt(j["research"])}</td>'
            f'<td class="num" data-label="Other">{fmt(j["other"])}</td></tr>')
    hub_body = f"""    <h1 class="sr-only">Journal Articles — 49 core economics journals, 2012–2025</h1>
    <p class="intro">
      The publisher tables of contents for 49 core economics journals,
      2012–2025. Search titles and author names across every journal, or browse by journal, then by year and issue. Each item has its title, DOI, item type, and author names with their source.
      AER: Insights starts in 2019, so 2012–2018 have 48 journals.
      This release has no person registry: names come from the TOC, the journal’s article pages, OpenAlex, or Crossref (names only).
    </p>

    <h2 class="section-title" id="search">Search</h2>
    <form class="site-search" action="catalog.html" method="get" role="search">
      <label class="lbl" for="home-q">Search titles, author names, or a DOI — all {s["journals"]} journals</label>
      <div class="site-search-row">
        <input id="home-q" type="search" name="q" enterkeyhint="search" autocomplete="off" placeholder="e.g. minimum wage, Duflo, or a DOI">
        <button class="btn primary" type="submit">Search</button>
      </div>
      <p class="hint">Research articles are included by default. A result opens that issue. Paste a DOI (10.…, https://doi.org/…, or http://dx.doi.org/…) to open that item when it is in this catalog. In the catalog, choose “Other and proceedings” or “All items” to widen a title or name search.</p>
    </form>

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
        <span class="sub">Search all journals, or choose a journal, then a year and an issue.</span></a>
      <a href="#journals"><span class="label">Journals</span>
        <span class="sub">All {s["journals"]} journals with years, issues, and research and item counts.</span></a>
    </div>

    <h2 class="section-title" id="journals">Journals</h2>
    <div class="tbl-wrap">
      <table class="responsive">
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
             "Search and browse the core 49 economics journals, 2012–2025: titles, DOIs, item types, and author names by source.",
             "home", hub_body), encoding="utf-8")

    # ---- Catalog ----------------------------------------------------------
    cat_body = """    <nav class="crumbs" id="crumbs" aria-label="Breadcrumb"></nav>
    <h1 class="page-title" id="results-title">Catalog</h1>
    <form class="controls" role="search" aria-label="Search and browse the catalog" onsubmit="return false">
      <div class="row">
        <div class="field grow"><label class="lbl" id="f-q-label" for="f-q">Search titles, author names, or a DOI</label>
          <input type="search" id="f-q" autocomplete="off" enterkeyhint="search" placeholder="e.g. minimum wage, Duflo, or a DOI"></div>
      </div>
      <div class="row">
        <div class="field journal-field"><label class="lbl" for="f-journal">Journal</label>
          <div class="combo">
            <input type="search" id="f-journal" role="combobox" aria-autocomplete="list" aria-expanded="false" aria-controls="f-journal-list" autocomplete="off" autocapitalize="none" spellcheck="false" placeholder="Find a journal…">
            <ul id="f-journal-list" class="combo-list" role="listbox" hidden></ul>
          </div>
        </div>
      </div>
      <div class="row picks-row" id="year-row" hidden>
        <div class="field"><span class="lbl" id="year-lbl">Year</span>
          <div id="f-year" class="picks" role="group" aria-labelledby="year-lbl"></div></div>
      </div>
      <div class="row picks-row" id="issue-row" hidden>
        <div class="field"><span class="lbl" id="issue-lbl">Issue</span>
          <div id="f-issue" class="picks" role="group" aria-labelledby="issue-lbl"></div></div>
      </div>
      <div class="row">
        <fieldset class="chips" id="f-type">
          <legend class="lbl">Item type</legend>
          <button type="button" class="chip" data-type="research" aria-pressed="true">Research articles<span class="c"></span></button>
          <button type="button" class="chip" data-type="other" aria-pressed="false">Other and proceedings<span class="c"></span></button>
          <button type="button" class="chip" data-type="all" aria-pressed="false">All items<span class="c"></span></button>
        </fieldset>
        <button type="button" class="btn" id="f-reset">Reset filters</button>
        <button type="button" class="btn" id="f-all" hidden>Search all journals</button>
      </div>
      <p class="hint">Search all journals, or choose one to browse by year and issue. Research articles are the default. A result opens the issue and highlights the item. A DOI in this box opens that item when it is in this catalog, and says when it is not. A name in an issue list is labeled “Search for this name.” That searches the name string. It is not a page for one person. Previous and Next move between issues. Cite copies a citation and BibTeX.</p>
      <details class="hint">
        <summary>How author names are labelled</summary>
        <p><em>As printed in the TOC</em> means the publisher’s TOC. <em>OpenAlex</em>, <em>OpenAlex by DOI</em>, and <em>Crossref by DOI</em> mean names from those databases, used when the TOC had none. <em>Official article page</em> means the journal’s own article page. Items without names show none. Copy a DOI from the item. Cite uses the names, title, journal, year, volume, issue, pages, and DOI shown on that item. Choosing a name searches for that name string. The same display name is not one person.</p>
      </details>
    </form>
    <p class="count" id="count" role="status" aria-live="polite"></p>
    <div id="results"></div>
"""
    (SITE / "catalog.html").write_text(
        page("Catalog — Journal Articles",
             "Search titles and author names across 49 economics journals, or browse by journal, year, and issue.",
             "catalog", cat_body,
             canonical_path="catalog.html", scripts='  <script src="catalog.js?v=6"></script>'),
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
            if p.name == "articles.csv":
                leaks.append(f"{p}: articles.csv")
            rel = p.relative_to(SITE).as_posix()
            if p.suffix.lower() in (".html", ".js", ".css", ".md") and not rel.startswith("data/"):
                prose = p.read_text(encoding="utf-8")
                if "econ-journal-dispersion" in prose or "Geographic Dispersion" in prose:
                    leaks.append(f"{rel}: editor-site or Geographic Dispersion wording")
            if p.suffix in (".json", ".csv"):
                head = p.read_text(encoding="utf-8")
                if "person_id" in head and p.name != "summary.json":
                    leaks.append(f"{p}: person_id")
                if rel.startswith("data/search/") and "spine_id" in head:
                    leaks.append(f"{p}: spine_id")
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
    search_raw = search_sizes["research"][0] + search_sizes["other"][0]
    if search_raw >= total or search_sizes["research"][1] > 3_500_000 or search_sizes["doi"][0] > 6_000_000:
        print("Search index is not clearly smaller than the journal shards", search_sizes, total, file=sys.stderr)
        return 1
    print(f"Built {SITE}")
    print(f"  {len(jindex)} journals, {len(issues)} issues, {len(articles)} items")
    print(f"  shards: {total/1e6:.1f} MB total; largest {big} {shard_sizes[big]/1e6:.2f} MB")
    print(f"  search: research {search_sizes['research'][0]/1e6:.2f} MB (gzip {search_sizes['research'][1]/1e6:.2f} MB); "
          f"other {search_sizes['other'][0]/1e6:.2f} MB (gzip {search_sizes['other'][1]/1e6:.2f} MB); "
          f"doi {search_sizes['doi'][0]/1e6:.2f} MB (gzip {search_sizes['doi'][1]/1e6:.2f} MB)")
    print(f"  authors display: {dict(stats)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
