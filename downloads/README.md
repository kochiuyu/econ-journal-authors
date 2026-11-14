# Articles TOC catalog, 2010–2025

Public freeze of the core-49 publisher table-of-contents spine for 49 economics journals.

- Window: 2010–2025 (AER Insights starts in 2019, so 2010–2018 have 48 journals). 775 journal-years, 4,835 issues.
- Built 2026-11-14 14:13 (Asia/Hong_Kong).
- The TOC is the article list. `is_research=1` marks research articles (`article_type=article`); other items are kept and flagged. All typing decisions current in the spine on the build date are included, including the 2026-11-14 user-confirmed retype of American Journal of Agricultural Economics 10.1093/ajae/aaq002 “The History of AAEA Research Awards” to non-research (widget t238u; this item only).
- Same files and columns as the 2012–2025 freeze: `articles.csv`, `issues.csv`, `journals.csv`, `coverage.csv`, `authors_missing_by_journal_year.csv`, `summary.json`; plus `DIFF_vs_articles_toc_2012_2025.md`.
- This release does **not** include internal `person_id` values, conflict files, QS handoffs, abstracts, keywords, or JEL codes.
- This supersedes `releases/articles_toc_2010_2025_20261114T1240/`.

## Author sources (`authors_source`)
In order of preference: the publisher TOC (`spine`); OpenAlex names recorded by the collector (`openalex_via_registry`); a journal-side OpenAlex work harvest by DOI (`openalex`, names only); Crossref metadata by DOI (`crossref`); the official Econometric Society article page for some Quantitative Economics items (`toc_official_qe`); and, for one item, the printed byline on the official publisher article page (`publisher_page`).

Eight previously nameless 2010–2011 research items were filled from verified bylines written onto the spine (`authors_source=spine`): seven Quantitative Economics articles from the official Econometric Society article pages and official PDFs (DOIs and pages also filled; those later-assigned 10.3982/QE DOIs had been absent from the publisher TOC), and one European Economic Review article from Crossref. The freeze prefers spine names once `authors_raw` is present.

## Totals
| Window | Items | Research | Research with authors | Items with DOI |
|---|---:|---:|---:|---:|
| 2010–2011 | 7,122 | 5,880 | 5,880 | 6,933 |
| 2012–2025 | 62,936 | 55,440 | 55,440 | 62,936 |
| 2010–2025 | 70,058 | 61,320 | 61,320 | 69,869 |

2010–2011 research author sources: `spine` 4,338; `openalex` 1,542. No research item in the 2010–2025 window is missing names.

## Missing rates, 2010–2011
- 189 items have no DOI (188 research: Review of Economics and Statistics 2010 78, 2011 101; Quantitative Economics 2010 2, 2011 7; plus 1 non-research JMCB item). They are kept. All of these research items now have author names.
- 0 research items have no author names. See `authors_missing_by_journal_year.csv`.

## Changes vs the previous freeze
Supersedes `releases/articles_toc_2010_2025_20261114T1240/` (built 2026-11-14 12:39, Asia/Hong_Kong). Versus that freeze, `articles.csv` changes only on nine 2010–2011 rows: eight verified byline/DOI/page fills, and the AJAE aaq002 retype. Every 2012–2025 row in `articles.csv`, `issues.csv`, `coverage.csv`, and `authors_missing_by_journal_year.csv` is identical to `releases/articles_toc_2012_2025/` (built 2026-11-12 13:55, Asia/Taipei = UTC+8). See `DIFF_vs_articles_toc_2012_2025.md`.
