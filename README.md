# econ-journal-authors — Journal Articles

Public static site and GitHub repo for the **article catalog**:
the publisher tables of contents (TOC) for 49 core economics journals, 2010–2025.

- Repo: <https://github.com/kochiuyu/econ-journal-authors>
- Site (GitHub Pages, project base `/econ-journal-authors/`): <https://kochiuyu.github.io/econ-journal-authors/>

## What the first release publishes

You can search titles and author names across all 49 journals, or browse by journal, then year, then issue. Each TOC item shows:

- title, pages, volume/issue, and a link to the issue TOC (and the publisher page when the freeze has one);
- DOI linked to `https://doi.org/{doi}` (189 items from 2010–2011 have no DOI in the TOC, and the catalog says so);
- type: **Research article** (`article_type=article`, `is_research=1`), **Other**, or **Proceedings** (`is_research=0`).
  The catalog and site-wide search show research articles first. A filter chip includes other and proceedings items, or all items.
- author names exactly as recorded, always labelled by source:
  - `authors_source=spine` → “as printed in the TOC”
  - `authors_source=openalex_via_registry` → “OpenAlex (name only)”
  - `authors_source=openalex` → “OpenAlex by DOI (name only)”
  - `authors_source=crossref` → “Crossref by DOI (name only)”
  - `authors_source=toc_official_qe` → “official article page”
  - `authors_source=publisher_page` → “official article page”
  - empty → no names shown; nothing is filled in from elsewhere.

Spine rows stored as a printed byline followed by the individual names
(`A, B, and C; A; B; C`) display the printed byline only. All other strings display verbatim.

On an issue, **Previous** and **Next** open the adjacent issue of that journal in catalog order
(year, then volume, then issue, so numeric issues such as 1, 2, … 10 come before labels such as S1;
Elsevier continuous volumes stay issue “C”). The step crosses a year or volume when that is the next
catalog issue. The first and last issue in the 2010–2025 window has the empty direction disabled.
The move updates `year`, `volume`, and `issue` only. A highlighted `item` does not carry over.

Each TOC item has **Cite**. It copies a plain-text journal citation and a BibTeX `@article` record
from the displayed author names (the same string as on the page, including the byline-prefix rule),
title, journal, year, volume, issue, pages, and DOI. Empty fields are omitted. Names are not rewritten.

Freeze totals (from `summary.json`): 49 journals, 775 journal-years, 4,835 issues, 70,058 items,
61,316 research articles, 8,742 other items, 70,057 with a DOI, 63,424 with author names
(20,395 from the publisher, 42,907 from OpenAlex, 122 from Crossref), 61,316 research articles with names.
AER: Insights starts in 2019.

## What is not published

Person IDs or any person registry, conflict files, QS handoffs, collector caches, affiliations,
unique-author pages, `spine_id`, and the raw 25 MB `articles.csv`. Affiliation panels and
author pages are planned for later releases.

## Source

The only input is the frozen release `releases/articles_toc_2010_2025/`
(`articles.csv`, `issues.csv`, `journals.csv`, `coverage.csv`, `summary.json`, `README.md`),
built 2026-11-14 14:13 (Asia/Hong_Kong). It adds 2010–2011 and supersedes the 2012–2025 freeze of 2026-11-12 13:55; every 2012–2025 row is unchanged. Nothing is read from the collector workspace.

## Layout

```
scripts/build_site.py   reads the freeze, verifies it against summary.json, writes site/
src/style.css           site stylesheet
src/catalog.js          browse UI and site-wide search
src/journals.js         sort the journals index
site/                   generated; this is what GitHub Pages serves
  index.html            hub: search, counts, 49-journal table, About
  catalog.html          search and browse (?journal=&year=&volume=&issue=&type=&q=&item=)
  journals/index.html   all 49 journals, sortable
  journals/<slug>.html  one page per journal: counts, coverage, issues
  data/journals.json    small index (meta + per-journal coverage)
  data/journals/<slug>.json   one lean shard per journal, loaded on demand
  data/search/research.json   titles and display names for research articles
  data/search/other.json      other and proceedings items, loaded when that filter is used
  data/search/doi.json        DOI to issue and item position, loaded only for a DOI query
  downloads/            journal/issue/year tables + summary from the freeze
  404.html, .nojekyll
```

Catalog URLs:

- The homepage search box submits to `catalog.html?q=…`. The same box is on the catalog page, and the query stays in the URL.
- `catalog.html?q=Duflo` searches titles and author names in all 49 journals (research articles unless `type=other` or `type=all`). No journal has to be selected first.
- `journals/index.html` lists all 49 journals and sorts by name, publisher, years, journal-years, issues, items, research, other, items with a DOI, items with names, and research articles with names. Those counts come from `journals.csv`, `coverage.csv`, and `authors_missing_by_journal_year.csv`.
- `journals/<slug>.html` is one journal: display name, publisher, ISSN, years covered (AER: Insights starts in 2019; the others run 2010–2025), issue and item counts, items with a DOI, items and research articles with names, a year-by-year coverage table, and the issues in the freeze. A year or issue opens `catalog.html?journal=&year=&volume=&issue=`.
- A journal name on the homepage, the journals index, and the catalog list opens that journal page. Browse in the catalog, and the year and issue links on the journal page, still open the catalog viewer.
- `catalog.html?journal=aer`, `catalog.html?journal=aer&year=2018`, `catalog.html?journal=aer&year=2018&volume=108&issue=1` browse as before.
- `catalog.html?journal=aer&q=wage` still searches only inside the loaded journal.
- `catalog.html?journal=aej-applied-economics&year=2015&volume=7&issue=1&item=2` opens that issue and highlights the item. `item` is the 0-based position in the issue’s TOC order, not a public identifier.
- Previous and Next on that issue go to the neighboring issues in the same order the year page lists them. No extra query parameter is added.
- On an issue, each displayed author name is a link labeled “Search for this name.” It opens a site-wide search for that name string only. The same display name is not one person, and there is no author page.
- A DOI in either search box — `10.…`, `https://doi.org/…`, or `http://dx.doi.org/…`, with case and surrounding whitespace ignored — opens that issue and highlights the item when the DOI is in this catalog. If it is not, the catalog says the DOI is not in the 2010–2025 release and does not add a record.

The search index is built from the freeze only. It stores the same display names as the catalog, including the TOC byline-prefix rule, and it does not include `articles.csv`. The first site-wide search shows a loading state while `research.json` downloads; other and proceedings items download if you include them. DOI lookup uses `data/search/doi.json` (lowercased DOI, journal, year, volume, issue, and TOC position only) and loads that file only when the query is a DOI. GitHub Pages gzips those files.

## Build and preview

```
python3 scripts/build_site.py
python3 -m http.server 8000 -d site     # then open http://localhost:8000/
```

The build fails if the freeze totals disagree with `summary.json`, if the search index does not match those totals, or if a person_id, conflict, or QS
file or column would appear in `site/`. All asset paths are relative, so the same files work at the
project-pages URL and on localhost. Data is fetched with `fetch()`, so open the site over HTTP, not `file://`.
On a narrow screen the catalog keeps the search box, journal finder, and year and issue chips in reach. Previous and Next are full-width tap targets, each item keeps Copy DOI beside Cite, and each author name is at least 44px tall. The journals index sorts from a control that stays on screen at about 390px wide, and the journal tables stack instead of scrolling the page sideways.

## Publishing

GitHub Pages is served from the `gh-pages` branch, which is a subtree of `site/`. After a site rebuild:

```
git add -A && git commit -m "…" && git push origin main
git branch -D gh-pages
git subtree split --prefix site -b gh-pages
git push origin gh-pages
```

## License / citation

The compiled catalog, site code, and documentation are **CC-BY-4.0**. See `LICENSE` and `CITATION.cff`.

Article titles, author bylines, and publisher tables of contents remain the publishers’. OpenAlex names follow OpenAlex’s terms.
