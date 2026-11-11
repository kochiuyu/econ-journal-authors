# Articles TOC catalog, 2012–2025

Public freeze of the core-49 publisher table-of-contents spine for 49 economics journals.

- Window: 2012–2025 (AER Insights starts in 2019).
- The TOC is the article list. `is_research=1` marks research articles (`article_type=article`); other items are kept and flagged.
- Author names, in order of preference (`authors_source`): the publisher TOC (`spine`); OpenAlex names recorded by the collector (`openalex_via_registry`); a journal-side OpenAlex work harvest by DOI (`openalex`); Crossref metadata by DOI (`crossref`); and, for Quantitative Economics items with no publisher DOI, the official Econometric Society article page (`toc_official_qe`, names as shown on the page). This release does **not** include internal `person_id` values, conflict files, or QS handoffs.
- Built 2026-11-11 23:59 (Asia/Taipei).
- This supersedes the 2026-11-11 23:54 freeze (`releases/articles_toc_2012_2025_20261111T2354/`). 116 listing items that had been typed as research are now typed non-research (`is_research=0`): JEL classification lists (56), doctoral dissertation lists (14), auditor's reports (12), book-review sections (12), notes and notes-and-errata (9), AJAE award-thesis abstract listings (7), correspondence (2), volume indexes (2), one special introduction, and one society officers list. Research 55,556 → 55,440; items unchanged (62,936); research-with-authors unchanged (55,439). One research row is still without names (a 2025 Journal of Financial Econometrics article whose DOI is not yet registered); it is listed in `authors_missing_by_journal_year.csv`.

Files: `articles.csv`, `issues.csv`, `journals.csv`, `coverage.csv`, `authors_missing_by_journal_year.csv`, `summary.json`.
