# Diff: articles_toc_2010_2025_20261114T1413 vs articles_toc_2012_2025 (2026-11-12 13:55 UTC+8)

| File | Previous rows | New rows, 2012–2025 | New rows, 2010–2011 | 2012–2025 rows identical |
|---|---:|---:|---:|---|
| articles.csv | 62,936 | 62,936 | 7,122 | yes (all fields, same spine_ids) |
| issues.csv | 4,283 | 4,283 | 552 | yes |
| coverage.csv | 679 | 679 | 96 | yes |
| authors_missing_by_journal_year.csv | 679 | 679 | 96 | yes |
| journals.csv | 49 | 49 | — | metadata columns unchanged; years/issues/items/research counts widened to 2010–2025 |

- Columns: unchanged in every file.
- 2012–2025: 0 rows added, 0 removed, 0 changed.
- 2010–2011 added: 7,122 items; 5,880 research; 5,880 research with authors (spine 4,338, openalex 1,542); 6,933 with DOI.

## Versus `articles_toc_2010_2025_20261114T1240` (2026-11-14 12:39 Asia/Hong_Kong)

`articles.csv` has the same 70,058 rows and the same columns. Exactly nine 2010–2011 rows changed (matched by journal, year, volume, issue, and title); every other article row is identical.

Eight byline fills (authors written to the spine; `authors_source=spine`):

- European Economic Review 2011 55-1 `10.1016/j.euroecorev.2010.11.006` “Deficit reduction: Short-term pain for long-term gain” — authors Kevin Clinton; Michael Kumhof; Douglas Laxton; Susanna Mursula (Crossref). Pages were already `118-139` (hyphen) and were left unchanged.
- Quantitative Economics 2010 1-2 “Partial identification of spread parameters” — Jörg Stoye; DOI `10.3982/QE24`; pages `323-357`.
- Quantitative Economics 2010 1-2 “Identification in matching games” — Jeremy T. Fox; DOI `10.3982/QE3`; pages `203-254`.
- Quantitative Economics 2010 1-2 “Continuity and differentiability of expected value functions in dynamic discrete choice models” — Andriy Norets; DOI `10.3982/QE41`; pages `305-322`.
- Quantitative Economics 2011 2-2 “Sources of macroeconomic fluctuations: A regime-switching DSGE approach” — Zheng Liu; Daniel F. Waggoner; Tao Zha; DOI `10.3982/QE71`; pages `251-301`.
- Quantitative Economics 2011 2-2 “Nonparametric probability bounds for Nash equilibrium actions in a simultaneous discrete game” — Andres Aradillas-Lopez; DOI `10.3982/QE74`; pages `135-171`.
- Quantitative Economics 2011 2-3 “A simple estimator for the distribution of random coefficients” — Jeremy T. Fox; Kyoo il Kim; Stephen P. Ryan; Patrick Bajari; DOI `10.3982/QE49`; pages `381-418`.
- Quantitative Economics 2011 2-3 “Are the responses of the U.S. economy asymmetric in energy price increases and decreases?” — Lutz Kilian; Robert J. Vigfusson; DOI `10.3982/QE99`; pages `419-453`.

The seven Quantitative Economics `spine_id` values changed because the builder uses the DOI in the id once one is present. Pages for those seven were previously blank; they are stored with a hyphen (`323-357`), matching the spine convention (official pages used an en-dash).

One retype (widget t238u; this item only; authors left blank):

- American Journal of Agricultural Economics 2010 92-2 `10.1093/ajae/aaq002` “The History of AAEA Research Awards” — `article_type` article → other, `is_research` 1 → 0.

Consequential count updates only, in the affected journal-years and issues: research 61,321 → 61,320; research with authors 61,312 → 61,320; items with DOI 69,862 → 69,869; other items 8,737 → 8,738. `issues.csv` (5 issues), `coverage.csv` (4 journal-years), `authors_missing_by_journal_year.csv` (4 journal-years), and `journals.csv` (AJAE research 1,294 → 1,293) change only as a result of those nine article rows.

- summary.json: window 2010-2025; timezone label Asia/Hong_Kong; research_with_authors equals research_articles (0 nameless research).
