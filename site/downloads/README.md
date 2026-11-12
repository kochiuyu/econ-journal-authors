# Articles TOC catalog, 2012–2025

Public freeze of the core-49 publisher table-of-contents spine for 49 economics journals.

- Window: 2012–2025 (AER Insights starts in 2019).
- The TOC is the article list. `is_research=1` marks research articles (`article_type=article`); other items are kept and flagged.
- Author names, in order of preference (`authors_source`): the publisher TOC (`spine`); OpenAlex names recorded by the collector (`openalex_via_registry`); a journal-side OpenAlex work harvest by DOI (`openalex`); Crossref metadata by DOI (`crossref`); and, for Quantitative Economics items whose names were taken from the official Econometric Society article page, that page (`toc_official_qe`, names as shown on the page). This release does **not** include internal `person_id` values, conflict files, or QS handoffs.
- Built 2026-11-12 13:37 (Asia/Taipei).
- This supersedes the 2026-11-11 23:59 freeze (`releases/articles_toc_2012_2025_20261111T2359/`). 53 Quantitative Economics research articles from 2012–2015 (2012: 14, 2013: 16, 2014: 16, 2015: 7) that had no DOI now carry their publisher DOI (`10.3982/QE…`), matched in Crossref by title, year, volume, and issue. Every item now has a DOI (62,883 → 62,936). Their author names, pages, and types are unchanged; because `spine_id` includes the DOI, those 53 rows have new `spine_id` values. Items (62,936), research (55,440), and research-with-authors (55,439) are unchanged. One research row is still without names (a 2025 Journal of Financial Econometrics article, 10.1093/jjfinec/nbaf010, with no published byline confirmed); it is listed in `authors_missing_by_journal_year.csv`.

Files: `articles.csv`, `issues.csv`, `journals.csv`, `coverage.csv`, `authors_missing_by_journal_year.csv`, `summary.json`.
