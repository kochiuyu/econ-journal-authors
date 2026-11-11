# econ-journal-authors — Journal Articles (Geographic Dispersion)

Public static site and future GitHub repo for the **Geographic Dispersion article catalog**:
the publisher tables of contents (TOC) for the core 49 economics journals, 2012–2025.

- Planned repo: <https://github.com/kochiuyu/econ-journal-authors> (not created yet)
- Planned site (GitHub Pages, project base `/econ-journal-authors/`): <https://kochiuyu.github.io/econ-journal-authors/>
- Sibling site, editorial boards: <https://kochiuyu.github.io/econ-journal-dispersion/>
  (repo <https://github.com/kochiuyu/econ-journal-dispersion>). No editor data is copied here.

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
src/style.css           site stylesheet (sibling of the editor directory)
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

## Publishing (later)

Create an empty public repo `kochiuyu/econ-journal-authors`. Push this directory and serve
GitHub Pages from `site/` (Actions) or publish `site/` to the `gh-pages` branch.

Licence: not yet chosen (the sibling editor project uses CC-BY-4.0). Titles and bylines remain the publishers’.
