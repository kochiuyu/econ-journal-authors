"""Inline SVG charts for the journal pages, computed only from the freeze.

Name counts use the author string the catalog displays. Pieces separated by
'; ' are names. A spine row whose display string is the printed byline
("A, B, and C") has no '; ' in that byline; the names are the individual
segments stored after the byline, and each of those segments appears in it.
Empty strings count as no names and are left out of averages and shares.
The count is names on the article, not distinct people.

Page length is last page minus first page plus one, and only for a numeric
range. Abbreviated ranges such as 116-48 are read as 116-148 when the ending
digits are greater than the start's tail. The same letter prefix on both
sides (S3-S14) is a range. Article numbers, blanks, and ambiguous strings
are left out.
"""
from __future__ import annotations

import html
import math
import re
from collections import Counter, defaultdict
from decimal import Decimal, ROUND_HALF_UP

PAGE_RE = re.compile(r"(\d+)\s*[-–—]\s*(\d+)")
LETTER_RE = re.compile(r"([A-Za-z]+)(\d+)\s*[-–—]\s*([A-Za-z]+)(\d+)")
ARTICLE_NO_RE = re.compile(r"(?:Article\s+\d+|\d{5,}|[A-Za-z]+\d+)", re.IGNORECASE)

OREOPOULOS = "The Short- and Long-Term Career Effects of Graduating in a Recession"
DUFLO = "The Miracle of Microfinance? Evidence from a Randomized Evaluation"
BERGEMANN_DOI = "10.1257/aer.20161079"

VB_W = 360
PLOT_H = 120
LEFT = 68
RIGHT = 8
TOP = 8
FONT = "Source Sans 3, Segoe UI, Helvetica, Arial, sans-serif"


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def fmt(n) -> str:
    return f"{int(n):,}"


def spine_byline_names(raw: str):
    """Return (printed byline, individual names) or None.

    The test matches display_authors: the first segment contains " and ",
    and every later segment appears verbatim in that byline.
    """
    if not raw:
        return None
    segs = [s.strip() for s in raw.split(";")]
    if len(segs) >= 3 and " and " in segs[0] and all(s and s in segs[0] for s in segs[1:]):
        return segs[0], segs[1:]
    return None


def author_name_count(raw: str, source: str) -> int:
    if not raw:
        return 0
    if source == "spine":
        hit = spine_byline_names(raw)
        if hit is not None:
            return len(hit[1])
    return len([p for p in raw.split("; ") if p.strip()])


def page_length(pages: str):
    """Inclusive length of a numeric page range, or None."""
    s = (pages or "").strip()
    if not s:
        return None
    m = PAGE_RE.fullmatch(s)
    if m:
        a_s, b_s = m.group(1), m.group(2)
        a, b = int(a_s), int(b_s)
        if len(b_s) < len(a_s):
            if int(b_s) <= int(a_s[-len(b_s):]):
                return None
            end = int(a_s[:-len(b_s)] + b_s)
            if end < a:
                return None
            return end - a + 1
        if b < a:
            return None
        return b - a + 1
    m = LETTER_RE.fullmatch(s)
    if m and m.group(1).lower() == m.group(3).lower():
        a, b = int(m.group(2)), int(m.group(4))
        if b < a:
            return None
        return b - a + 1
    return None


def page_skip_kind(pages: str) -> str:
    s = (pages or "").strip()
    if not s:
        return "blank"
    if ARTICLE_NO_RE.fullmatch(s):
        return "article_number"
    return "not_range"


def page_length_self_check() -> list:
    expect = {
        "116-48": 33,
        "1127-1265": 139,
        "S183-S300": 118,
        "S3-S14": 12,
        "e1-e16": 16,
        "F4-F30": 27,
        "100-104": 5,
        "231-231": 1,
        "105-27": 23,
    }
    absent = ["104457", "Article 105074", "231-31", "4614-000", "", "i-vi", "591", "p. 635", "1010"]
    bad = []
    for raw, n in expect.items():
        got = page_length(raw)
        if got != n:
            bad.append(f"page_length({raw!r})={got}, expected {n}")
    for raw in absent:
        got = page_length(raw)
        if got is not None:
            bad.append(f"page_length({raw!r})={got}, expected None")
    if author_name_count("", "spine") != 0:
        bad.append("empty name count")
    if author_name_count("Ada Lovelace", "openalex") != 1:
        bad.append("single name count")
    if author_name_count("Ada Lovelace; Alan Turing", "openalex") != 2:
        bad.append("semicolon name count")
    sample = "A, B, and C; A; B; C"
    if author_name_count(sample, "spine") != 3:
        bad.append("byline name count")
    if author_name_count(sample, "openalex") != 4:
        bad.append("non-spine byline string was shortened")
    return bad


def round_half_up(num, den, places=2) -> str:
    if not den:
        return ""
    quant = Decimal("1") if places == 0 else Decimal("0." + "0" * (places - 1) + "1")
    q = (Decimal(int(num)) / Decimal(int(den))).quantize(quant, rounding=ROUND_HALF_UP)
    return f"{q:.{places}f}"


def _new_year(year: int) -> dict:
    return {
        "year": year,
        "research": 0,
        "other": 0,
        "named": 0,
        "unnamed": 0,
        "name_sum": 0,
        "b1": 0,
        "b2": 0,
        "b3": 0,
        "b4": 0,
        "page_n": 0,
        "page_sum": 0,
        "skip_blank": 0,
        "skip_article_number": 0,
        "skip_not_range": 0,
    }


def build_chart_series(articles, journals, coverage, missing, summary):
    """Per-journal and all-journal year series. problems is empty when the
    series match journals.csv, coverage.csv, and authors_missing_by_journal_year.csv.
    """
    problems = page_length_self_check() + _low_high_self_check()
    by = {}
    for c in coverage:
        by.setdefault(c["journal_slug"], {})[int(c["year"])] = _new_year(int(c["year"]))
    known = {"oreopoulos": 0, "duflo": 0, "bergemann": 0}
    sources = defaultdict(Counter)
    for r in articles:
        slug = r["journal_slug"]
        try:
            year = int(r["year"])
        except ValueError:
            problems.append(f"bad year {r.get('year')!r}")
            continue
        slot = by.get(slug, {}).get(year)
        if slot is None:
            problems.append(f"article outside coverage {slug} {year}")
            continue
        if r["is_research"] == "1":
            slot["research"] += 1
            n = author_name_count(r["authors"], r["authors_source"])
            if n <= 0:
                slot["unnamed"] += 1
            else:
                slot["named"] += 1
                slot["name_sum"] += n
                if n == 1:
                    slot["b1"] += 1
                elif n == 2:
                    slot["b2"] += 1
                elif n == 3:
                    slot["b3"] += 1
                else:
                    slot["b4"] += 1
                sources[slug][r["authors_source"]] += 1
            span = page_length(r["pages"])
            if span is None:
                slot["skip_" + page_skip_kind(r["pages"])] += 1
            elif span > 2000:
                problems.append(f"implausible page length {span} {slug} {year} {r['pages']!r}")
            else:
                slot["page_n"] += 1
                slot["page_sum"] += span
            if r["title"] == OREOPOULOS:
                known["oreopoulos"] += 1
                if n != 3:
                    problems.append(f"Oreopoulos name count {n}")
            elif r["title"] == DUFLO:
                known["duflo"] += 1
                if n != 4:
                    problems.append(f"Duflo name count {n}")
            if (r.get("doi") or "").strip().lower() == BERGEMANN_DOI:
                known["bergemann"] += 1
                if n != 3:
                    problems.append(f"Bergemann name count {n}")
        else:
            slot["other"] += 1
    if known["oreopoulos"] != 1 or known["duflo"] != 1 or known["bergemann"] != 1:
        problems.append(f"known name-count rows {known}")

    miss = {(m["journal_slug"], int(m["year"])): m for m in missing}
    journal_rows = {j["journal_slug"]: j for j in journals}
    series = {}
    all_acc = {}
    for slug, years in by.items():
        jrow = journal_rows.get(slug)
        if jrow is None:
            problems.append(f"coverage slug missing from journals.csv {slug}")
            continue
        ordered = [years[y] for y in sorted(years)]
        pub = oa = cr = 0
        for y in ordered:
            m = miss.get((slug, y["year"]))
            if m is None:
                problems.append(f"missing author-year row {slug} {y['year']}")
                continue
            if y["research"] != int(m["research"]) or y["named"] != int(m["with_authors"]) or y["unnamed"] != int(m["missing"]):
                problems.append(f"name totals {slug} {y['year']}")
            if y["b1"] + y["b2"] + y["b3"] + y["b4"] != y["named"]:
                problems.append(f"name buckets {slug} {y['year']}")
            if y["named"] + y["unnamed"] != y["research"]:
                problems.append(f"named split {slug} {y['year']}")
            skips = y["skip_blank"] + y["skip_article_number"] + y["skip_not_range"]
            if y["page_n"] + skips != y["research"]:
                problems.append(f"page split {slug} {y['year']}")
            bucket = all_acc.setdefault(y["year"], _new_year(y["year"]))
            bucket["journals"] = bucket.get("journals", 0) + 1
            for key in ("research", "other", "named", "unnamed", "name_sum", "b1", "b2", "b3", "b4",
                        "page_n", "page_sum", "skip_blank", "skip_article_number", "skip_not_range"):
                bucket[key] += y[key]
        cov_years = {}
        # filled below from the coverage pass
        src = sources[slug]
        pub = src["spine"] + src["toc_official_qe"] + src["publisher_page"]
        oa = src["openalex"] + src["openalex_via_registry"]
        cr = src["crossref"]
        extra = sum(v for k, v in src.items() if k not in {
            "spine", "toc_official_qe", "publisher_page", "openalex", "openalex_via_registry", "crossref"})
        if extra:
            problems.append(f"unexpected name source {slug} {extra}")
        if pub + oa + cr != sum(y["named"] for y in ordered):
            problems.append(f"source sum {slug}")
        series[slug] = {
            "years": ordered,
            "sources": {"publisher": pub, "openalex": oa, "crossref": cr},
            "_cov": cov_years,
        }

    for c in coverage:
        slug = c["journal_slug"]
        year = int(c["year"])
        slot = by.get(slug, {}).get(year)
        if slot is None or slug not in series:
            problems.append(f"coverage year missing {slug} {year}")
            continue
        if slot["research"] != int(c["research_articles"]) or slot["other"] != int(c["other_items"]):
            problems.append(f"coverage counts {slug} {year}")
        if slot["research"] + slot["other"] != int(c["items"]):
            problems.append(f"coverage items {slug} {year}")
        m = miss[(slug, year)]
        series[slug]["_cov"][year] = {
            "spine": int(m["source_spine"]),
            "qe": int(m["source_toc_official_qe"]),
            "other": int(m["source_other"]),
            "oa_reg": int(m["source_openalex_via_registry"]),
            "oa": int(m["source_openalex"]),
            "cr": int(m["source_crossref"]),
        }

    for slug, pack in series.items():
        bits = pack.pop("_cov")
        jrow = journal_rows[slug]
        research = sum(y["research"] for y in pack["years"])
        other = sum(y["other"] for y in pack["years"])
        if research != int(jrow["research_articles"]) or other != int(jrow["other_items"]):
            problems.append(f"journals.csv totals {slug}")
        pub = sum(v["spine"] + v["qe"] + v["other"] for v in bits.values())
        oa = sum(v["oa_reg"] + v["oa"] for v in bits.values())
        cr = sum(v["cr"] for v in bits.values())
        got = pack["sources"]
        if (got["publisher"], got["openalex"], got["crossref"]) != (pub, oa, cr):
            problems.append(f"source grouping {slug}: articles {got} author-year {(pub, oa, cr)}")
        if pub + oa + cr != sum(y["named"] for y in pack["years"]):
            problems.append(f"author-year source sum {slug}")

    if sum(sum(y["research"] for y in p["years"]) for p in series.values()) != summary["research_articles"]:
        problems.append("chart research total != summary")
    if sum(sum(y["other"] for y in p["years"]) for p in series.values()) != summary["other_items"]:
        problems.append("chart other total != summary")
    if sum(sum(y["named"] for y in p["years"]) for p in series.values()) != summary["research_with_authors"]:
        problems.append("chart named total != summary")
    if set(series) != set(journal_rows):
        problems.append("chart journals != journals.csv")

    all_years = []
    for year in sorted(all_acc):
        row = all_acc[year]
        row["journals"] = row.get("journals", 0)
        all_years.append(row)
    if sum(r["research"] for r in all_years) != summary["research_articles"]:
        problems.append("all-journals research total")
    if sum(r["journals"] for r in all_years) != summary["journal_years"]:
        problems.append("all-journals journal-year total")
    return series, all_years, problems


def axis_top(value, *, integer=False):
    value = float(value)
    if value <= 0:
        return (1, 1, 1) if integer else (1.0, 1.0, 1)
    best = None
    for steps in (4, 5, 3, 6, 2):
        raw = value / steps
        exp = 0 if raw <= 0 else math.floor(math.log10(raw))
        base = 10 ** exp
        for mult in (1, 2, 5, 10):
            step = mult * base
            if integer:
                step = max(1, int(round(step)))
            else:
                step = round(step, 10)
            top = step * steps
            if top + 1e-9 < value:
                continue
            waste = top / value if value else top
            cand = (round(waste, 6), steps, top, step)
            if best is None or cand < best:
                best = cand
    return best[2], best[3], best[1]


def _px(n) -> str:
    return f"{float(n):.1f}"


def _tick_text(v, step, integer) -> str:
    if integer or abs(v - round(v)) < 1e-6:
        return fmt(int(round(v)))
    return f"{v:.1f}"


def _geom(n, rotate):
    bottom = 56 if rotate else 40
    height = TOP + PLOT_H + bottom
    return {
        "n": n,
        "rotate": rotate,
        "left": LEFT,
        "right": RIGHT,
        "top": TOP,
        "bottom": bottom,
        "plot_w": VB_W - LEFT - RIGHT,
        "plot_h": PLOT_H,
        "height": height,
        "base": TOP + PLOT_H,
    }


def _year_x(geom, i):
    slot = geom["plot_w"] / geom["n"]
    return geom["left"] + (i + 0.5) * slot, slot


def _svg_open(chart_id, title, desc, height):
    return (
        f'<svg role="img" aria-labelledby="{chart_id}-svg-title {chart_id}-svg-desc" '
        f'viewBox="0 0 {VB_W} {height}">'
        f'<title id="{chart_id}-svg-title">{esc(title)}</title>'
        f'<desc id="{chart_id}-svg-desc">{esc(desc)}</desc>'
    )


def _axis(geom, ticks, labels, y_title, integer, step):
    parts = []
    base = geom["base"]
    top_v = ticks[-1] if ticks else 1
    for v, label in zip(ticks, labels):
        y = base - (v / top_v) * geom["plot_h"] if top_v else base
        parts.append(
            f'<line x1="{_px(geom["left"])}" y1="{_px(y)}" x2="{_px(geom["left"] + geom["plot_w"])}" '
            f'y2="{_px(y)}" stroke="var(--chart-line)" stroke-width="1"/>'
        )
        parts.append(
            f'<text fill="var(--chart-muted)" font-family="{FONT}" font-size="11" '
            f'text-anchor="end" x="{_px(geom["left"] - 6)}" y="{_px(y + 4)}">{esc(label)}</text>'
        )
    parts.append(
        f'<text fill="var(--chart-ink)" font-family="{FONT}" font-size="11" text-anchor="middle" '
        f'transform="translate(11,{_px(geom["top"] + geom["plot_h"] / 2)}) rotate(-90)">{esc(y_title)}</text>'
    )
    year_y = base + (46 if geom["rotate"] else 32)
    mid = geom["left"] + geom["plot_w"] / 2
    parts.append(
        f'<text fill="var(--chart-ink)" font-family="{FONT}" font-size="11" text-anchor="middle" '
        f'x="{_px(mid)}" y="{_px(year_y)}">Year</text>'
    )
    return parts


def _year_labels(geom, years):
    parts = []
    base = geom["base"]
    for i, year in enumerate(years):
        cx, _slot = _year_x(geom, i)
        if geom["rotate"]:
            parts.append(
                f'<text fill="var(--chart-muted)" font-family="{FONT}" font-size="11" text-anchor="end" '
                f'transform="translate({_px(cx)},{_px(base + 4)}) rotate(-90)">{year}</text>'
            )
        else:
            parts.append(
                f'<text fill="var(--chart-muted)" font-family="{FONT}" font-size="11" text-anchor="middle" '
                f'x="{_px(cx)}" y="{_px(base + 16)}">{year}</text>'
            )
    return parts


def _bar_width(slot):
    return min(22.0, slot * 0.62)


def sr_table(chart, caption, headers, rows) -> str:
    th = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body = "\n".join(
        "<tr>" + "".join(f"<td>{esc(c)}</td>" for c in row) + "</tr>" for row in rows
    )
    return (
        f'<div class="sr-only"><table data-chart="{esc(chart)}"><caption>{esc(caption)}</caption>'
        f"<thead><tr>{th}</tr></thead><tbody>\n{body}\n</tbody></table></div>"
    )


def legend(items) -> str:
    lis = []
    for cls, label in items:
        lis.append(f'<li><span class="swatch {cls}"></span>{esc(label)}</li>')
    return '<ul class="legend">' + "".join(lis) + "</ul>"


def figure(chart_id, heading, note, svg, legend_html, summary, table) -> str:
    return (
        f'<figure class="chart" aria-labelledby="{chart_id}-title">'
        f'<figcaption><span class="chart-title" id="{chart_id}-title">{esc(heading)}</span>'
        f'<span class="chart-note">{esc(note)}</span></figcaption>'
        f"{svg}{legend_html}"
        f'<p class="chart-summary">{esc(summary)}</p>'
        f"{table}</figure>"
    )


def _year_phrase(years) -> str:
    if len(years) == 1:
        return years[0]
    if len(years) <= 4:
        return ", ".join(years)
    return f"{len(years)} years, including {years[0]}"


def _low_high(rows, num_key, den_key):
    usable = [r for r in rows if r[den_key]]
    if not usable:
        return ""
    # Compare the displayed two-decimal values as numbers. A text sort would
    # put "10.12" before "9.49".
    scored = []
    for r in usable:
        shown = round_half_up(r[num_key], r[den_key], 2)
        scored.append((Decimal(shown), shown, str(r["year"])))
    lo = min(scored)[1]
    hi = max(scored)[1]
    lo_years = [year for value, shown, year in scored if shown == lo]
    hi_years = [year for value, shown, year in scored if shown == hi]
    if lo == hi:
        return f"The displayed average is {lo} in every plotted year."
    return (f"The displayed average is as low as {lo} in {_year_phrase(lo_years)} "
            f"and as high as {hi} in {_year_phrase(hi_years)}.")


def _low_high_self_check() -> list:
    rows = [
        {"year": 2010, "page_sum": 949, "page_n": 100},
        {"year": 2011, "page_sum": 1012, "page_n": 100},
    ]
    text = _low_high(rows, "page_sum", "page_n")
    if text != ("The displayed average is as low as 9.49 in 2010 "
                "and as high as 10.12 in 2011."):
        return [f"low/high sentence {text!r}"]
    return []


def _count_ticks(max_value):
    top, step, nsteps = axis_top(max_value, integer=True)
    ticks = [i * step for i in range(nsteps + 1)]
    labels = [_tick_text(v, step, True) for v in ticks]
    return top, step, ticks, labels


def _avg_ticks(max_value):
    top, step, nsteps = axis_top(max_value, integer=False)
    ticks = [i * step for i in range(nsteps + 1)]
    labels = [_tick_text(v, step, False) for v in ticks]
    return top, step, ticks, labels


def _frame(chart_id, title, desc, years, y_title, ticks, labels, integer, step):
    rotate = len(years) > 7
    geom = _geom(len(years), rotate)
    parts = [_svg_open(chart_id, title, desc, geom["height"])]
    parts.extend(_axis(geom, ticks, labels, y_title, integer, step))
    parts.extend(_year_labels(geom, [str(y) for y in years]))
    return geom, parts


def _close(parts) -> str:
    parts.append("</svg>")
    return "".join(parts)


def items_chart(chart_id, years, journal_name) -> str:
    max_total = max((y["research"] + y["other"]) for y in years) if years else 0
    top, step, ticks, labels = _count_ticks(max_total)
    research = sum(y["research"] for y in years)
    other = sum(y["other"] for y in years)
    note = ("Research articles and other items in each year. Other items are TOC rows that are not "
            "research articles, including proceedings. The bars sum to this journal’s totals.")
    fullest = max(years, key=lambda y: (y["research"] + y["other"], y["year"]))
    tie = [str(y["year"]) for y in years if y["research"] + y["other"] == fullest["research"] + fullest["other"]]
    summary = (f"Together: {fmt(research)} research articles and {fmt(other)} other items. "
               f"The fullest year is {_year_phrase(tie)}, with {fmt(fullest['research'])} research articles "
               f"and {fmt(fullest['other'])} other items.")
    desc = f"{journal_name}. {summary}"
    geom, parts = _frame(chart_id, f"Research articles and other items per year, {journal_name}",
                         desc, [y["year"] for y in years], "Items", ticks, labels, True, step)
    for i, y in enumerate(years):
        cx, slot = _year_x(geom, i)
        bw = _bar_width(slot)
        x = cx - bw / 2
        cursor = geom["base"]
        parts.append("<g>")
        for value, color, label in (
            (y["research"], "var(--bar-1)", "research articles"),
            (y["other"], "var(--bar-3)", "other items"),
        ):
            if value <= 0 or top <= 0:
                continue
            h = value / top * geom["plot_h"]
            cursor -= h
            parts.append(
                f'<rect x="{_px(x)}" y="{_px(cursor)}" width="{_px(bw)}" height="{_px(h)}" fill="{color}">'
                f"<title>{esc(y['year'])}: {fmt(value)} {label}</title></rect>"
            )
        parts.append("</g>")
    svg = _close(parts)
    rows = [[str(y["year"]), str(y["research"]), str(y["other"])] for y in years]
    table = sr_table("items", f"Research articles and other items per year, {journal_name}",
                     ["Year", "Research articles", "Other items"], rows)
    return figure(chart_id, "Research articles and other items per year", note, svg,
                  legend([("s1", "Research articles"), ("s3", "Other items")]), summary, table)


def names_chart(chart_id, years, journal_name) -> str:
    ratios = [y["name_sum"] / y["named"] for y in years if y["named"]]
    max_v = max(ratios) if ratios else 1
    top, step, ticks, labels = _avg_ticks(max_v)
    named = sum(y["named"] for y in years)
    unnamed = sum(y["unnamed"] for y in years)
    research = named + unnamed
    note = ("Average names on a research article. Names are counted in the author string shown in the "
            "catalog, split on “; ”. When that string is a printed byline (“A, B, and C”), each name in "
            "the byline is counted. This is names on the article, not unique people. Research articles "
            "with no names are left out of the average.")
    if unnamed == 0:
        exclude = f"Every research article has names, so none are left out ({fmt(research)} articles)."
    else:
        exclude = (f"{fmt(unnamed)} of {fmt(research)} research articles have no names and are left out. "
                   f"The average uses {fmt(named)} articles.")
    summary = exclude + " " + _low_high(years, "name_sum", "named")
    desc = f"{journal_name}. {note} {summary}"
    geom, parts = _frame(chart_id, f"Average names per research article, {journal_name}",
                         desc, [y["year"] for y in years], "Names", ticks, labels, False, step)
    points = []
    for i, y in enumerate(years):
        cx, _slot = _year_x(geom, i)
        if not y["named"] or top <= 0:
            points.append(None)
            continue
        avg = y["name_sum"] / y["named"]
        cy = geom["base"] - (avg / top) * geom["plot_h"]
        points.append((cx, cy, y))
    _polyline(parts, points, "var(--bar-1)")
    for p in points:
        if p is None:
            continue
        cx, cy, y = p
        shown = round_half_up(y["name_sum"], y["named"], 2)
        tip = (f"{y['year']}: {shown} names per article "
               f"({fmt(y['named'])} research articles with names; {fmt(y['name_sum'])} names)")
        parts.append(
            f'<g><title>{esc(tip)}</title>'
            f'<circle cx="{_px(cx)}" cy="{_px(cy)}" r="8" fill="transparent"/>'
            f'<circle cx="{_px(cx)}" cy="{_px(cy)}" r="3.5" fill="var(--bar-1)" '
            f'stroke="var(--panel)" stroke-width="1.5"/></g>'
        )
    svg = _close(parts)
    rows = []
    for y in years:
        rows.append([
            str(y["year"]), str(y["named"]), str(y["unnamed"]), str(y["name_sum"]),
            round_half_up(y["name_sum"], y["named"], 2),
        ])
    table = sr_table("names", f"Average names per research article, {journal_name}",
                     ["Year", "Articles with names", "Articles without names", "Names counted", "Average"],
                     rows)
    return figure(chart_id, "Average names per research article", note, svg,
                  legend([("s1", "Names per article")]), summary, table)


def _polyline(parts, points, color):
    chunk = []
    def flush():
        if len(chunk) >= 2:
            pts = " ".join(f"{_px(x)},{_px(y)}" for x, y, _row in chunk)
            parts.append(
                f'<polyline fill="none" stroke="{color}" stroke-width="2" '
                f'stroke-linejoin="round" stroke-linecap="round" points="{pts}"/>'
            )
        chunk.clear()
    for p in points:
        if p is None:
            flush()
        else:
            chunk.append(p)
    flush()


def share_chart(chart_id, years, journal_name) -> str:
    unnamed = sum(y["unnamed"] for y in years)
    named = sum(y["named"] for y in years)
    note = ("Share of research articles with 1, 2, 3, or 4 or more names on the article. "
            "The name count is the same one used in the average above. Articles with no names "
            "are left out, and each bar is 100% of the articles that have names.")
    if unnamed == 0:
        exclude = f"Every research article has names, so the bars cover all {fmt(named)}."
    else:
        exclude = f"{fmt(unnamed)} research articles have no names and are left out. The bars cover {fmt(named)}."
    summary = exclude
    desc = f"{journal_name}. {note} {summary}"
    ticks = [0, 25, 50, 75, 100]
    labels = ["0%", "25%", "50%", "75%", "100%"]
    geom, parts = _frame(chart_id, f"Share of research articles by name count, {journal_name}",
                         desc, [y["year"] for y in years], "Share", ticks, labels, True, 25)
    bands = (("b1", "var(--bar-1)", "1 name"), ("b2", "var(--bar-2)", "2 names"),
             ("b3", "var(--bar-3)", "3 names"), ("b4", "var(--bar-4)", "4 or more names"))
    for i, y in enumerate(years):
        cx, slot = _year_x(geom, i)
        bw = _bar_width(slot)
        x = cx - bw / 2
        parts.append("<g>")
        if y["named"] <= 0:
            parts.append(f"<title>{esc(str(y['year']))}: no research articles with names</title>")
        else:
            cursor = geom["base"]
            for key, color, label in bands:
                value = y[key]
                if value <= 0:
                    continue
                h = value / y["named"] * geom["plot_h"]
                cursor -= h
                pct = round_half_up(value, y["named"], 1)
                tip = f"{y['year']}: {fmt(value)} with {label} ({pct}% of {fmt(y['named'])} with names)"
                parts.append(
                    f'<rect x="{_px(x)}" y="{_px(cursor)}" width="{_px(bw)}" height="{_px(h)}" fill="{color}">'
                    f"<title>{esc(tip)}</title></rect>"
                )
        parts.append("</g>")
    svg = _close(parts)
    rows = [[str(y["year"]), str(y["b1"]), str(y["b2"]), str(y["b3"]), str(y["b4"])] for y in years]
    table = sr_table("share", f"Research articles by name count, {journal_name}",
                     ["Year", "1 name", "2 names", "3 names", "4 or more"], rows)
    return figure(chart_id, "Research articles by number of names", note, svg,
                  legend([("s1", "1 name"), ("s2", "2 names"), ("s3", "3 names"), ("s4", "4 or more")]),
                  summary, table)


def _left_out_phrase(years) -> str:
    blank = sum(y["skip_blank"] for y in years)
    art = sum(y["skip_article_number"] for y in years)
    other = sum(y["skip_not_range"] for y in years)
    bits = []
    if blank:
        bits.append(f"{fmt(blank)} with blank pages")
    if art:
        bits.append(f"{fmt(art)} with an article number rather than a page range")
    if other:
        bits.append(f"{fmt(other)} with a page string that is not a numeric range")
    if not bits:
        return "Nothing was left out."
    return "Left out: " + "; ".join(bits) + "."


def pages_block(chart_id, years, journal_name) -> str:
    research = sum(y["research"] for y in years)
    usable = sum(y["page_n"] for y in years)
    definition = ("Average pages per research article that has a numeric page range, counted as the last "
                  "page minus the first page plus one. A range such as 116-48 is read as 116–148 when the "
                  "ending digits are unambiguous. A letter prefix that matches on both sides, such as S3-S14, "
                  "is included. Article numbers are not. Research articles without a usable range are left "
                  "out of the average.")
    left = _left_out_phrase(years)
    included = f"{fmt(usable)} of {fmt(research)} research articles are included."
    if usable <= 0:
        summary = f"Average page length is not charted. {included} {left}"
        return f'<p class="chart-note">{esc(summary)} {esc(definition)}</p>'
    ratios = [y["page_sum"] / y["page_n"] for y in years if y["page_n"]]
    top, step, ticks, labels = _avg_ticks(max(ratios) if ratios else 1)
    gap = any(y["page_n"] == 0 for y in years)
    gap_s = " A year with no point has no usable page range." if gap else ""
    summary = f"{included} {left} {_low_high(years, 'page_sum', 'page_n')}{gap_s}"
    note = definition
    desc = f"{journal_name}. {note} {summary}"
    geom, parts = _frame(chart_id, f"Average page length per research article, {journal_name}",
                         desc, [y["year"] for y in years], "Pages", ticks, labels, False, step)
    points = []
    for i, y in enumerate(years):
        cx, _slot = _year_x(geom, i)
        if not y["page_n"] or top <= 0:
            points.append(None)
            continue
        avg = y["page_sum"] / y["page_n"]
        cy = geom["base"] - (avg / top) * geom["plot_h"]
        points.append((cx, cy, y))
    _polyline(parts, points, "var(--bar-2)")
    for p in points:
        if p is None:
            continue
        cx, cy, y = p
        shown = round_half_up(y["page_sum"], y["page_n"], 2)
        tip = (f"{y['year']}: {shown} pages on average "
               f"({fmt(y['page_n'])} of {fmt(y['research'])} research articles had a numeric page range; "
               f"{fmt(y['page_sum'])} pages in total)")
        parts.append(
            f'<g><title>{esc(tip)}</title>'
            f'<circle cx="{_px(cx)}" cy="{_px(cy)}" r="8" fill="transparent"/>'
            f'<circle cx="{_px(cx)}" cy="{_px(cy)}" r="3.5" fill="var(--bar-2)" '
            f'stroke="var(--panel)" stroke-width="1.5"/></g>'
        )
    svg = _close(parts)
    rows = []
    for y in years:
        rows.append([
            str(y["year"]), str(y["research"]), str(y["page_n"]), str(y["page_sum"]),
            round_half_up(y["page_sum"], y["page_n"], 2),
        ])
    table = sr_table("pages", f"Average page length, {journal_name}",
                     ["Year", "Research articles", "Usable ranges", "Pages summed", "Average"], rows)
    return figure(chart_id, "Average page length per research article", note, svg,
                  legend([("s2", "Pages per article, numeric ranges only")]), summary, table)


def sources_chart(chart_id, sources, journal_name) -> str:
    rows_spec = (
        ("Publisher", sources["publisher"], "var(--bar-1)"),
        ("OpenAlex", sources["openalex"], "var(--bar-2)"),
        ("Crossref", sources["crossref"], "var(--bar-4)"),
    )
    total = sum(n for _label, n, _color in rows_spec)
    note = ("Where the names on research articles came from. Publisher is the TOC plus the journal’s "
            "article page. OpenAlex combines OpenAlex names and OpenAlex by DOI. Crossref is Crossref by DOI. "
            "These are research articles with names, not unique people.")
    summary = (f"{fmt(sources['publisher'])} from the publisher, {fmt(sources['openalex'])} from OpenAlex, "
               f"{fmt(sources['crossref'])} from Crossref. The three sum to {fmt(total)}.")
    desc = f"{journal_name}. {summary}"
    height = 118
    parts = [_svg_open(chart_id, f"Where research-article names came from, {journal_name}", desc, height)]
    max_n = max(n for _l, n, _c in rows_spec)
    bar_left = 96
    bar_right = 278
    span = bar_right - bar_left
    for i, (label, n, color) in enumerate(rows_spec):
        y = 18 + i * 34
        parts.append(
            f'<text fill="var(--chart-ink)" font-family="{FONT}" font-size="12" '
            f'x="4" y="{y + 14}">{esc(label)}</text>'
        )
        noun = "research article" if n == 1 else "research articles"
        tip = f"<title>{esc(label)}: {fmt(n)} {noun}</title>"
        if n > 0 and max_n > 0:
            w = max(span * n / max_n, 1.5)
            parts.append(
                f'<rect x="{bar_left}" y="{y}" width="{_px(w)}" height="18" fill="{color}">{tip}</rect>'
            )
        parts.append(
            f'<text fill="var(--chart-ink)" font-family="{FONT}" font-size="12" text-anchor="end" '
            f'x="352" y="{y + 14}">{tip}{esc(fmt(n))}</text>'
        )
    svg = _close(parts)
    table = sr_table("sources", f"Where research-article names came from, {journal_name}",
                     ["Source", "Research articles"],
                     [[label, str(n)] for label, n, _color in rows_spec])
    return figure(chart_id, "Where research-article names came from", note, svg, "", summary, table)


def journal_charts_html(slug, name, pack) -> str:
    years = pack["years"]
    chart = slug
    parts = [
        items_chart(f"{chart}-items", years, name),
        names_chart(f"{chart}-names", years, name),
        share_chart(f"{chart}-share", years, name),
        pages_block(f"{chart}-pages", years, name),
        sources_chart(f"{chart}-sources", pack["sources"], name),
    ]
    return '<div class="charts">\n' + "\n".join(parts) + "\n</div>"


def _journal_span_sentence(all_years) -> str:
    groups = []
    for row in all_years:
        n = row["journals"]
        y = row["year"]
        if not groups or groups[-1][0] != n:
            groups.append([n, y, y])
        else:
            groups[-1][2] = y
    bits = []
    for n, a, b in groups:
        span = str(a) if a == b else f"{a}–{b}"
        noun = "journal" if n == 1 else "journals"
        bits.append(f"{span}: {n} {noun}")
    return ". ".join(bits) + "."


def across_charts_html(all_years) -> str:
    span = _journal_span_sentence(all_years)
    research = sum(y["research"] for y in all_years)
    named = sum(y["named"] for y in all_years)
    unnamed = sum(y["unnamed"] for y in all_years)
    intro = (f"Counted from the freeze, for every journal that has issues in that year. {span} "
             "Names are names on the article, not unique people. Research articles with no names "
             "are left out of the average.")
    # Research bars. Reuse the items chart machinery with other forced to 0 would
    # draw an empty series, so draw a one-series chart here.
    max_total = max(y["research"] for y in all_years)
    top, step, ticks, labels = _count_ticks(max_total)
    note = ("Research articles per year, summed across the journals in the freeze for that year. " + span)
    fullest = max(all_years, key=lambda y: (y["research"], y["year"]))
    tie = [str(y["year"]) for y in all_years if y["research"] == fullest["research"]]
    summary = (f"The bars sum to {fmt(research)} research articles. "
               f"The fullest year is {_year_phrase(tie)}, with {fmt(fullest['research'])}.")
    desc = summary + " " + span
    chart_id = "all-research"
    geom, parts = _frame(chart_id, "Research articles per year, all journals",
                         desc, [y["year"] for y in all_years], "Articles", ticks, labels, True, step)
    for i, y in enumerate(all_years):
        cx, slot = _year_x(geom, i)
        bw = _bar_width(slot)
        x = cx - bw / 2
        if y["research"] > 0 and top > 0:
            h = y["research"] / top * geom["plot_h"]
            y0 = geom["base"] - h
            tip = f"{y['year']}: {fmt(y['research'])} research articles in {y['journals']} journals"
            parts.append(
                f'<rect x="{_px(x)}" y="{_px(y0)}" width="{_px(bw)}" height="{_px(h)}" fill="var(--bar-1)">'
                f"<title>{esc(tip)}</title></rect>"
            )
    svg = _close(parts)
    rows = [[str(y["year"]), str(y["journals"]), str(y["research"])] for y in all_years]
    table = sr_table("research", "Research articles per year across journals",
                     ["Year", "Journals", "Research articles"], rows)
    research_fig = figure(chart_id, "Research articles per year", note, svg,
                          legend([("s1", "Research articles")]), summary, table)
    names = names_chart("all-names", all_years, "all journals")
    # names_chart's table uses data-chart="names", which is what the checker expects.
    if unnamed == 0:
        names_line = f"The average uses all {fmt(named)} research articles."
    else:
        names_line = f"The average leaves out {fmt(unnamed)} research articles with no names."
    # The names figure already states the exclusion. intro covers the journal span.
    return (
        '<h2 class="section-title" id="across">Across all journals</h2>\n'
        f'<p class="hint">{esc(intro)} {esc(names_line)}</p>\n'
        '<div class="charts">\n' + research_fig + "\n" + names + "\n</div>\n"
    )


def _parse_tables(text):
    tables = {}
    for m in re.finditer(r'<table data-chart="([^"]+)">(.*?)</table>', text, re.S):
        body = re.search(r"<tbody>(.*)</tbody>", m.group(2), re.S)
        rows = []
        for tr in re.findall(r"<tr>(.*?)</tr>", body.group(1), re.S):
            cells = [html.unescape(c) for c in re.findall(r"<td>(.*?)</td>", tr, re.S)]
            rows.append(cells)
        tables[m.group(1)] = rows
    return tables


def _svg_blocks(text):
    return re.findall(r"<svg\b.*?</svg>", text, re.S)


def _check_year_rows(problems, where, rows, years, pairs):
    """pairs: list of (column index, key) for integer columns after the year."""
    if len(rows) != len(years):
        problems.append(f"{where} row count {len(rows)} != {len(years)}")
        return
    for row, y in zip(rows, years):
        if row[0] != str(y["year"]):
            problems.append(f"{where} year {row[0]} != {y['year']}")
            return
        for idx, key in pairs:
            if int(row[idx]) != y[key]:
                problems.append(f"{where} {y['year']} {key} html {row[idx]} != {y[key]}")
                return


def check_rendered_charts(site, jindex, series_by_slug, all_years, summary) -> list:
    problems = []
    jdir = site / "journals"
    index_html = (jdir / "index.html").read_text(encoding="utf-8")
    hub = (site / "index.html").read_text(encoding="utf-8")
    gap = summary["items"] - summary["items_with_doi"]
    if gap == 1:
        if "1 TOC record without one" not in hub or "1 TOC records without one" in hub:
            problems.append("hub singular DOI wording")
    elif gap == 0:
        if "Every item has a DOI" not in hub:
            problems.append("hub missing every-item DOI line")
    else:
        phrase = f"{fmt(gap)} TOC records without one"
        if phrase not in hub:
            problems.append("hub DOI gap wording")

    itables = _parse_tables(index_html)
    if set(itables) != {"research", "names"}:
        problems.append(f"index charts {sorted(itables)}")
    else:
        _check_year_rows(problems, "index research", itables["research"], all_years,
                         [(1, "journals"), (2, "research")])
        _check_year_rows(problems, "index names", itables["names"], all_years,
                         [(1, "named"), (2, "unnamed"), (3, "name_sum")])
        for row, y in zip(itables["names"], all_years):
            if row[4] != round_half_up(y["name_sum"], y["named"], 2):
                problems.append(f"index names average {y['year']}")
                break
        if sum(int(r[2]) for r in itables["research"]) != summary["research_articles"]:
            problems.append("index research sum")
        if sum(int(r[1]) for r in itables["names"]) != summary["research_with_authors"]:
            problems.append("index named sum")
    for svg in _svg_blocks(index_html):
        if "<title" not in svg or "<desc" not in svg:
            problems.append("index svg missing title or desc")
            break
    if 'id="across"' not in index_html or index_html.find('id="journal-table"') > index_html.find('id="across"'):
        problems.append("across charts are not below the journal table")

    forbidden_name = "Philip Oreopoulos"
    for j in jindex:
        slug = j["slug"]
        text = (jdir / f"{slug}.html").read_text(encoding="utf-8")
        if forbidden_name in text:
            problems.append(f"{slug} contains an author name")
        pack = series_by_slug[slug]
        years = pack["years"]
        tables = _parse_tables(text)
        expect = {"items", "names", "share", "sources"}
        if sum(y["page_n"] for y in years):
            expect.add("pages")
        if set(tables) != expect:
            problems.append(f"{slug} charts {sorted(tables)} != {sorted(expect)}")
            continue
        _check_year_rows(problems, f"{slug} items", tables["items"], years, [(1, "research"), (2, "other")])
        _check_year_rows(problems, f"{slug} names", tables["names"], years,
                         [(1, "named"), (2, "unnamed"), (3, "name_sum")])
        _check_year_rows(problems, f"{slug} share", tables["share"], years,
                         [(1, "b1"), (2, "b2"), (3, "b3"), (4, "b4")])
        for row, y in zip(tables["names"], years):
            if row[4] != round_half_up(y["name_sum"], y["named"], 2):
                problems.append(f"{slug} names average {y['year']}")
                break
            if int(row[1]) + int(row[2]) != y["research"]:
                problems.append(f"{slug} names split {y['year']}")
                break
        for row, y in zip(tables["share"], years):
            if int(row[1]) + int(row[2]) + int(row[3]) + int(row[4]) != y["named"]:
                problems.append(f"{slug} share sum {y['year']}")
                break
        if "pages" in tables:
            _check_year_rows(problems, f"{slug} pages", tables["pages"], years,
                             [(1, "research"), (2, "page_n"), (3, "page_sum")])
            for row, y in zip(tables["pages"], years):
                if row[4] != round_half_up(y["page_sum"], y["page_n"], 2):
                    problems.append(f"{slug} pages average {y['year']}")
                    break
                if int(row[2]) > int(row[1]):
                    problems.append(f"{slug} pages usable exceeds research {y['year']}")
                    break
        src_rows = tables["sources"]
        expect_src = [("Publisher", pack["sources"]["publisher"]),
                      ("OpenAlex", pack["sources"]["openalex"]),
                      ("Crossref", pack["sources"]["crossref"])]
        if [(r[0], int(r[1])) for r in src_rows] != expect_src:
            problems.append(f"{slug} sources {src_rows}")
        elif sum(n for _l, n in expect_src) != sum(y["named"] for y in years):
            problems.append(f"{slug} sources do not sum to named")
        if sum(int(r[1]) for r in tables["items"]) != j["research"]:
            problems.append(f"{slug} chart research != journals.csv")
        if sum(int(r[2]) for r in tables["items"]) != j["other"]:
            problems.append(f"{slug} chart other != journals.csv")
        svgs = _svg_blocks(text)
        if len(svgs) != (5 if "pages" in expect else 4):
            problems.append(f"{slug} svg count {len(svgs)}")
        elif any("<title" not in s or "<desc" not in s for s in svgs):
            problems.append(f"{slug} svg missing title or desc")
        m = re.search(r'<h2 class="section-title">Issues</h2>[\s\S]*?<h3><a [^>]*>\s*(\d{4})\s*</a>', text)
        if not m or int(m.group(1)) != max(y["year"] for y in years):
            problems.append(f"{slug} issues are not newest-year first")
        stats_at = text.find('class="stats compact"')
        issues_at = text.find(">Issues</h2>")
        details_at = text.find("<details")
        if not (0 <= issues_at < stats_at < details_at):
            problems.append(f"{slug} section order")
    return problems
