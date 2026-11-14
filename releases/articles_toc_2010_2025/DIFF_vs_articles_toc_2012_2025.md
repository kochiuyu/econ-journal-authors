# Diff: articles_toc_2010_2025_20261114T1447 vs articles_toc_2012_2025 (2026-11-12 13:55 UTC+8)

| File | Previous rows | New rows, 2012–2025 | New rows, 2010–2011 | 2012–2025 rows identical |
|---|---:|---:|---:|---|
| articles.csv | 62,936 | 62,936 | 7,122 | yes (all fields, same spine_ids) |
| issues.csv | 4,283 | 4,283 | 552 | yes |
| coverage.csv | 679 | 679 | 96 | yes |
| authors_missing_by_journal_year.csv | 679 | 679 | 96 | yes |
| journals.csv | 49 | 49 | — | metadata columns unchanged; years/issues/items/research counts widened to 2010–2025 |

- Columns: unchanged in every file.
- 2012–2025: 0 rows added, 0 removed, 0 changed. The 62,936 article rows are also identical to the 14:13 freeze.
- 2010–2011 added relative to the 2012–2025 catalog: 7,122 items; 5,876 research; 5,876 research with authors (spine 4,339, openalex 1,537); 7,121 with DOI.

## Versus `articles_toc_2010_2025_20261114T1413` (2026-11-14 14:13 Asia/Hong_Kong)

`articles.csv` has the same 70,058 rows and the same columns. Exactly 202 rows in 2010–2011 changed (matched by journal, year, volume, issue, and title); every other article row is identical.

### Quantitative Economics 2010–2011 bylines, DOIs, and pages

Seventeen research rows changed. Nine previously missing `10.3982/QE` DOIs were filled, and 17 previously blank page ranges were filled, from official Econometric Society article pages and official PDFs (Crossref-checked). Pages are stored with a hyphen, matching the spine convention. The nine new DOIs also change those rows' `spine_id` values, because the builder uses the DOI in the id once one is present. Ten bylines on the spine were completed or corrected:

- 2010 1-1 `10.3982/QE16` “Effects of school reform on education and labor market performance: Evidence from Chile’s universal voucher system” — David Bravo; Sankar Mukhopadhyay; Petra E. Todd (pages `47-95`; official PDF is more complete than the previous OpenAlex name Petra Todd; `authors_source` openalex → spine).
- 2010 1-1 `10.3982/QE7` “Aggregate labor market outcomes: The roles of choice and chance” — Per Krusell; Toshihiko Mukoyama; Richard Rogerson; Ayşegül Şahin (pages `97-127`).
- 2010 1-2 `10.3982/QE1` “Set identification and sensitivity analysis with Tobin regressors” — Victor Chernozhukov; Roberto Rigobon; Thomas M. Stoker (pages `255-277`).
- 2010 1-2 `10.3982/QE43` “Semiparametric efficiency in nonlinear LATE models” — Han Hong; Denis Nekipelov (pages `279-304`).
- 2011 2-1 `10.3982/QE2` “Childhood determinants of risk aversion: The long shadow of compulsory education” — Dmytro Hryshko; María José Luengo-Prado; Bent E. Sørensen (pages `37-72`).
- 2011 2-1 `10.3982/QE19` “The cyclical behavior of equity turnover” — David N. DeJong; Emilio Espino (pages `99-133`).
- 2011 2-1 `10.3982/QE40` “Costly financial intermediation in neoclassical growth theory” — authors already complete; DOI and pages `1-36` filled.
- 2011 2-2 `10.3982/QE14` “Numerically stable and accurate stochastic simulation approaches for solving dynamic economic models” — Kenneth L. Judd; Lilia Maliar; Serguei Maliar (pages `173-210`).
- 2011 2-2 `10.3982/QE59` “Is distance dying at last? Falling home bias in fixed-effects models of patent citations” — Rachel Griffith; Sokbae Lee; John Van Reenen (pages `211-249`).
- 2011 2-3 `10.3982/QE69` “A nonparametric analysis of black–white differences in intergenerational income mobility in the United States” — Debopam Bhattacharya; Bhashkar Mazumder (pages `335-379`).
- 2011 2-3 `10.3982/QE82` “Dating the timeline of financial bubbles during the subprime crisis” — authors already complete; DOI and pages `455-491` filled.
- 2011 2-3 `10.3982/QE83` “Does affirmative action lead to mismatch? A new test and evidence” — Peter Arcidiacono; Esteban M. Aucejo; Hanming Fang; Kenneth I. Spenner (pages `303-333`).

Five further 2010–2011 Quantitative Economics research rows received official page ranges only (authors left on OpenAlex, which already matched or was more complete than the official byline): `10.3982/QE8` pages `1-46`; `10.3982/QE9` pages `129-162`; `10.3982/QE6` pages `163-186`; `10.3982/QE5` pages `187-202`; `10.3982/QE36` pages `73-98`. The seven Quantitative Economics byline/DOI/page fills already in the 14:13 freeze are unchanged.

### Review of Economics and Statistics 2010–2011 DOIs

All 179 research items in 2010 (78) and 2011 (101) received a Crossref DOI. Matches were unambiguous on normalized title plus first page (volume and issue also agreed). Titles, types, and pages were not changed. DOI forms are those registered in Crossref (`10.1162/rest.2009…` or `10.1162/rest.2010…` for 33 items; `10.1162/rest_a_…` for 146).

### Six retypes

- The Journal of Economic History 2010 70-1 `10.1017/S0022050710000112` “The Decline in Infant Death Rates, 1878–1913: The Role of Early Sickness Insurance Programs” — `article_type` other → article, `is_research` 0 → 1 (research note).
- Quarterly Journal of Economics 2011 126-4 `10.1093/qje/qjr042` “Saving Babies? Revisiting the effect of very low birth weight classification” — article → other, `is_research` 1 → 0 (comment; a Reply follows in the same issue).
- Journal of Economic Behavior and Organization 2011 78-1-2 `10.1016/j.jebo.2011.01.002` “Professor Zak's empirical studies on trust and oxytocin” — article → other, `is_research` 1 → 0 (comment/critique).
- Journal of Financial Econometrics 2010 8-2 `10.1093/jjfinec/nbq008` “Separation in Cointegrated Systems”; `10.1093/jjfinec/nbq007` “Clive Granger and HEGY”; and `10.1093/jjfinec/nbq004` “Further Developments in the Study of Cointegrated Variables” — article → other, `is_research` 1 → 0 (tribute/reminiscence).

Consequential count updates only, in the affected journal-years and issues: research 61,320 → 61,316; research with authors 61,320 → 61,316; items with DOI 69,869 → 70,057; other items 8,738 → 8,742. `issues.csv` (16 issues), `coverage.csv` (8 journal-years), `authors_missing_by_journal_year.csv` (5 journal-years), and `journals.csv` (JEBO research 4,650 → 4,649; JFEC 443 → 440; QJE 701 → 700; JEH 496 → 497) change only as a result of those 202 article rows.

- summary.json: window 2010-2025; timezone label Asia/Hong_Kong; research_with_authors equals research_articles (0 nameless research). Every research item now has a DOI. The one remaining no-DOI item is the non-research JMCB 2011 43-S2 discussion.
