# Articles TOC catalog, 2010–2025

Public freeze of the core-49 publisher table-of-contents spine for 49 economics journals.

- Window: 2010–2025 (AER Insights starts in 2019, so 2010–2018 have 48 journals). 775 journal-years, 4,835 issues.
- Built 2026-11-14 14:47 (Asia/Hong_Kong).
- The TOC is the article list. `is_research=1` marks research articles (`article_type=article`); other items are kept and flagged. All typing decisions current in the spine on the build date are included.
- Same files and columns as the 2012–2025 freeze: `articles.csv`, `issues.csv`, `journals.csv`, `coverage.csv`, `authors_missing_by_journal_year.csv`, `summary.json`; plus `DIFF_vs_articles_toc_2012_2025.md`.
- This release does **not** include internal `person_id` values, conflict files, QS handoffs, abstracts, keywords, or JEL codes.
- This supersedes `releases/articles_toc_2010_2025_20261114T1413/`.

## Author sources (`authors_source`)
In order of preference: the publisher TOC (`spine`); OpenAlex names recorded by the collector (`openalex_via_registry`); a journal-side OpenAlex work harvest by DOI (`openalex`, names only); Crossref metadata by DOI (`crossref`); the official Econometric Society article page for some Quantitative Economics items (`toc_official_qe`); and, for one item, the printed byline on the official publisher article page (`publisher_page`).

The freeze prefers spine names once `authors_raw` is present. Further 2010–2011 Quantitative Economics bylines, DOIs, and pages were written onto the spine from official Econometric Society article pages and official PDFs (Crossref-checked). Review of Economics and Statistics 2010–2011 research items received Crossref DOIs (unambiguous title plus first-page matches).

## Totals
| Window | Items | Research | Research with authors | Items with DOI |
|---|---:|---:|---:|---:|
| 2010–2011 | 7,122 | 5,876 | 5,876 | 7,121 |
| 2012–2025 | 62,936 | 55,440 | 55,440 | 62,936 |
| 2010–2025 | 70,058 | 61,316 | 61,316 | 70,057 |

2010–2011 research author sources: `spine` 4,339; `openalex` 1,537. No research item in the 2010–2025 window is missing names.

## Missing rates, 2010–2011
- 1 item has no DOI: a non-research Journal of Money, Credit and Banking 2011 43-S2 discussion. It is kept. Every research item in the 2010–2025 window now has a DOI.
- 0 research items have no author names. See `authors_missing_by_journal_year.csv`.

## Changes vs the previous freeze
Supersedes `releases/articles_toc_2010_2025_20261114T1413/` (built 2026-11-14 14:13, Asia/Hong_Kong). Versus that freeze, `articles.csv` changes only on 202 rows in 2010–2011: Quantitative Economics byline, DOI, and page fills; 179 Review of Economics and Statistics DOIs; and six retypes. Every 2012–2025 row in `articles.csv`, `issues.csv`, `coverage.csv`, and `authors_missing_by_journal_year.csv` is identical to `releases/articles_toc_2012_2025/` (built 2026-11-12 13:55, UTC+8) and to the 14:13 freeze. See `DIFF_vs_articles_toc_2012_2025.md`.
