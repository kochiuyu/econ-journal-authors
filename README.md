# econ-journal-authors — Journal Articles

Public static site and GitHub repo for the **article catalog**:
the publisher tables of contents (TOC) for 49 core economics journals, 2012–2025.

- Repo: <https://github.com/kochiuyu/econ-journal-authors>
- Site (GitHub Pages, project base `/econ-journal-authors/`): <https://kochiuyu.github.io/econ-journal-authors/>

## What the first release publishes

You can browse by journal, then year, then issue. Each TOC item shows:

- title, pages, volume/issue, and a link to the issue TOC (and the publisher page when the freeze has one);
- DOI linked to `https://doi.org/{doi}`, or “No DOI in the TOC record” (53 items);
- type: **Research article** (`article_type=article`, `is_research=1`), **Other**, or **Proceedings** (`is_research=0`).
  The catalog shows research articles first. A filter chip shows other/proceedings items or all items;
- author names exactly as recorded, always labelled by source:
  - `authors_source=spine` → “as printed in the TOC”
  - `authors_source=openalex_via_registry` → “OpenAlex (name only)”
  - empty → no names shown; nothing is filled in from elsewhere.

Spine rows stored as a printed byline followed by the individual names
(`A, B, and C; A; B; C`) display the printed byline only. All other strings display verbatim.

Freeze totals (from `summary.json`): 49 journals, 679 journal-years, 4,283 issues, 62,936 items,
55,534 research articles, 7,402 other items, 62,883 with a DOI, 49,107 with author names
(15,440 TOC, 33,667 OpenAlex), 47,674 research articles with names. AER: Insights starts in 2019.

## What is not published

Person IDs or any person registry, conflict files, QS handoffs, collector caches, affiliations,
unique-author pages, `spine_id`, and the raw 25 MB `articles.csv`. Affiliation panels and
author pages are planned for later releases.

## Source

The only input is the frozen release `releases/articles_toc_2012_2025/`
(`articles.csv`, `issues.csv`, `journals.csv`, `coverage.csv`, `summary.json`, `README.md`),
built 2026-11-11 (Asia/Taipei). Nothing is read from the collector workspace.

## Layout

```
scripts/build_site.py   reads the freeze, verifies it against summary.json, writes site/
src/style.css           site stylesheet
src/catalog.js          browse UI
site/                   generated; this is what GitHub Pages serves
  index.html            hub: counts, 49-journal table, About
  catalog.html          browse UI (?journal=&year=&volume=&issue=&type=&q=)
  data/journals.json    small index (meta + per-journal coverage)
  data/journals/<slug>.json   one lean shard per journal, loaded on demand
  downloads/            journal/issue/year tables + summary from the freeze
  404.html, .nojekyll
```

Catalog URLs: `catalog.html?journal=aer`, `catalog.html?journal=aer&year=2018`,
`catalog.html?journal=aer&year=2018&volume=108&issue=1`; optional `type=all|other` and `q=` (title/name search
within the loaded journal).

## Build and preview

```
python3 scripts/build_site.py
python3 -m http.server 8000 -d site     # then open http://localhost:8000/
```

The build fails if the freeze totals disagree with `summary.json` or if a person_id, conflict, or QS
file or column would appear in `site/`. All asset paths are relative, so the same files work at the
project-pages URL and on localhost. Data is fetched with `fetch()`, so open the site over HTTP, not `file://`.

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
