# Articles TOC catalog, 2012–2025

Public freeze of the core-49 publisher table-of-contents spine for 49 economics journals.

- Window: 2012–2025 (AER Insights starts in 2019).
- The TOC is the article list. `is_research=1` marks research articles (`article_type=article`); other items are kept and flagged.
- Author names, in order of preference (`authors_source`): the publisher TOC (`spine`); OpenAlex names recorded by the collector (`openalex_via_registry`); a journal-side OpenAlex work harvest by DOI (`openalex`); Crossref metadata by DOI (`crossref`); and, for Quantitative Economics items with no publisher DOI, the official Econometric Society article page (`toc_official_qe`, names as shown on the page). This release does **not** include internal `person_id` values, conflict files, or QS handoffs.
- Built 2026-11-11 23:54 (Asia/Taipei).
- This supersedes the 2026-11-11 23:35 freeze (`releases/articles_toc_2012_2025_20261111T2335/`). It adds two new name sources for research articles still blank after OpenAlex: Crossref by DOI (122 articles) and official Quantitative Economics article pages for 24 items without a publisher DOI. Research-with-authors 55,293 → 55,439. Research and item counts are unchanged (55,556 research; 62,936 items). The 117 research rows still without names are listed per journal-year in `authors_missing_by_journal_year.csv`; most are listings (classification lists, dissertation lists, auditor's reports, book-review sections) that carry no authors.

Files: `articles.csv`, `issues.csv`, `journals.csv`, `coverage.csv`, `authors_missing_by_journal_year.csv`, `summary.json`.
