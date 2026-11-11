# Articles TOC catalog, 2012–2025

Public freeze of the core-49 publisher table-of-contents spine for 49 economics journals.

- Window: 2012–2025 (AER Insights starts in 2019).
- The TOC is the article list. `is_research=1` marks research articles (`article_type=article`); other items are kept and flagged.
- Author names come from the TOC when present, otherwise from OpenAlex names recorded by the collector, or from a journal-side OpenAlex work harvest by DOI. This release does **not** include internal `person_id` values, conflict files, or QS handoffs.
- Built 2026-11-11 23:35 (Asia/Taipei).
- This supersedes the 2026-11-11 22:28 freeze (`releases/articles_toc_2012_2025_20261111T2228/`). It fills author names for research articles that had empty TOC and registry names, using a journal-side OpenAlex harvest by DOI (7,595 research articles newly named; research-with-authors 47,698 → 55,293). Research and item counts are unchanged (55,556 research; 62,936 items).

Files: `articles.csv`, `issues.csv`, `journals.csv`, `coverage.csv`, `authors_missing_by_journal_year.csv`, `summary.json`.
