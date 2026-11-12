# Articles TOC catalog, 2012–2025

Public freeze of the core-49 publisher table-of-contents spine for 49 economics journals.

- Window: 2012–2025 (AER Insights starts in 2019).
- The TOC is the article list. `is_research=1` marks research articles (`article_type=article`); other items are kept and flagged.
- Author names, in order of preference (`authors_source`): the publisher TOC (`spine`); OpenAlex names recorded by the collector (`openalex_via_registry`); a journal-side OpenAlex work harvest by DOI (`openalex`); Crossref metadata by DOI (`crossref`); for Quantitative Economics items whose names were taken from the official Econometric Society article page, that page (`toc_official_qe`, names as shown on the page); and, for one item whose names were read from the printed byline on the official publisher article page, that page (`publisher_page`, names as printed). This release does **not** include internal `person_id` values, conflict files, or QS handoffs.
- Built 2026-11-12 13:55 (Asia/Taipei).
- This supersedes the 2026-11-12 13:37 freeze (`releases/articles_toc_2012_2025_20261112T1337/`). The one research row that had no names, a 2025 Journal of Financial Econometrics article (23(2), nbaf010, DOI 10.1093/jjfinec/nbaf010, "Assessing Tail Risk via a Generalized Conditional Autoregressive Expectile Model"), now carries the byline printed on the official Oxford University Press article page (published 26 March 2025): Zongwu Cai; Ying Fang; Dingshi Tian (`authors_source=publisher_page`). Crossref and OpenAlex did not yet return this DOI. Only the printed names were taken; no affiliations or identifiers. Its `publisher_url` is now the public article page, https://academic.oup.com/jfec/article/23/2/nbaf010/8096628. Its title, pages, type, and DOI are unchanged. This was the last research row without names: research with authors is now 55,440 of 55,440 (items with authors 56,824 → 56,825). In `authors_missing_by_journal_year.csv` this row is counted under `source_other`.
- The 2026-11-12 13:37 freeze gave 53 Quantitative Economics research articles from 2012–2015 (2012: 14, 2013: 16, 2014: 16, 2015: 7) their publisher DOI (`10.3982/QE…`), matched in Crossref by title, year, volume, and issue, so every item has a DOI (62,936). Their names, pages, and types are unchanged in this freeze.
- Items (62,936), research (55,440), issues (4,283), and journals (49) are unchanged.

Files: `articles.csv`, `issues.csv`, `journals.csv`, `coverage.csv`, `authors_missing_by_journal_year.csv`, `summary.json`.
