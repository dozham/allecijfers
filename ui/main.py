from pathlib import Path

from fastapi import Cookie, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import ui.db as db

_HERE = Path(__file__).parent

app = FastAPI()
app.mount("/static", StaticFiles(directory=_HERE / "static"), name="static")
templates = Jinja2Templates(directory=_HERE / "templates")
templates.env.globals["translate"] = db.translate

_SUMMARY_TOPICS = [
    "Inwoners",
    "Gemiddeld inkomen per inwoner",
    "% Huurwoningen",
    "Misdrijven",
    "% Herkomst buiten Europa",
]

_SUMMARY_LABELS: dict[str, tuple[str, str]] = {
    "Inwoners":                      ("Inwoners",        "Residents"),
    "Gemiddeld inkomen per inwoner": ("Gem. inkomen",    "Avg. income"),
    "% Huurwoningen":                ("Huurwoningen",    "Rental homes"),
    "Misdrijven":                    ("Misdrijven",      "Crimes"),
    "% Herkomst buiten Europa":      ("Buiten Europa",   "Non-European"),
}

_SKIP_UNITS = {"Aantal", "Code", "Naam", "Categorisch type", "Percentage", ""}


def _parse_starred(cookie: str) -> set[str]:
    return set(filter(None, cookie.split("|")))


def _parse_compare(cookie: str) -> list[str]:
    return list(filter(None, cookie.split("|")))


def _parse_numeric(val: str) -> float | None:
    try:
        return float(val.replace("%", "").replace(",", ".").strip())
    except (ValueError, AttributeError):
        return None


def _stats_with_pinned(stats: dict, starred: set[str]) -> dict:
    if not starred:
        return stats
    pinned = [row for rows in stats.values() for row in rows if row["topic"] in starred]
    return {"_starred": pinned, **stats} if pinned else stats


@app.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    lang: str = Cookie(default="nl"),
    theme: str = Cookie(default="dark"),
    compare: str = Cookie(default=""),
):
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "lang": lang,
            "theme": theme,
            "municipalities": db.get_municipalities(),
            "compare_slugs": _parse_compare(compare),
        },
    )


@app.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    q: str = "",
    municipality: str = "",
    type: str = "",
    page: int = 1,
    lang: str = Cookie(default="nl"),
):
    results = db.search_areas(q, municipality, type, page)
    total = db.count_areas(q, municipality, type)
    return templates.TemplateResponse(
        request,
        "partials/search_results.html",
        {
            "results": results,
            "lang": lang,
            "q": q,
            "municipality": municipality,
            "type": type,
            "page": page,
            "total": total,
            "per_page": db._PER_PAGE,
        },
    )


@app.get("/area/{slug}", response_class=HTMLResponse)
async def area(
    request: Request,
    slug: str,
    lang: str = Cookie(default="nl"),
    theme: str = Cookie(default="dark"),
    starred: str = Cookie(default=""),
    compare: str = Cookie(default=""),
):
    meta = db.get_area_meta(slug)
    if not meta:
        return HTMLResponse("Not found", status_code=404)
    all_stats = db.get_area_stats(slug)
    starred_set = _parse_starred(starred)
    compare_slugs = _parse_compare(compare)
    summary: dict[str, dict] = {}
    for rows in all_stats.values():
        for row in rows:
            if row["topic"] in _SUMMARY_TOPICS:
                summary[row["topic"]] = row
    hierarchy = db.get_area_hierarchy(slug, meta["area_type"])
    return templates.TemplateResponse(
        request,
        "area.html",
        {
            "meta": meta,
            "summary": summary,
            "summary_topics": _SUMMARY_TOPICS,
            "summary_labels": _SUMMARY_LABELS,
            "skip_units": _SKIP_UNITS,
            "stats": _stats_with_pinned(all_stats, starred_set),
            "hierarchy": hierarchy,
            "lang": lang,
            "theme": theme,
            "starred": starred_set,
            "slug": slug,
            "compare_slugs": compare_slugs,
            "in_compare": slug in compare_slugs,
        },
    )


@app.get("/area/{slug}/stats", response_class=HTMLResponse)
async def area_stats(
    request: Request,
    slug: str,
    q: str = "",
    lang: str = Cookie(default="nl"),
    starred: str = Cookie(default=""),
):
    starred_set = _parse_starred(starred)
    stats = db.get_area_stats(slug, q)
    return templates.TemplateResponse(
        request,
        "partials/stats_body.html",
        {
            "stats": _stats_with_pinned(stats, starred_set),
            "q": q,
            "lang": lang,
            "skip_units": _SKIP_UNITS,
            "starred": starred_set,
            "slug": slug,
        },
    )


@app.post("/area/{slug}/star", response_class=HTMLResponse)
async def star_topic(
    request: Request,
    slug: str,
    lang: str = Cookie(default="nl"),
    starred: str = Cookie(default=""),
):
    form = await request.form()
    topic = str(form.get("topic", ""))
    q = str(form.get("q", ""))
    starred_set = _parse_starred(starred)
    if topic in starred_set:
        starred_set.discard(topic)
    else:
        starred_set.add(topic)
    stats = db.get_area_stats(slug, q)
    resp = templates.TemplateResponse(
        request,
        "partials/stats_body.html",
        {
            "stats": _stats_with_pinned(stats, starred_set),
            "q": q,
            "lang": lang,
            "skip_units": _SKIP_UNITS,
            "starred": starred_set,
            "slug": slug,
        },
    )
    resp.set_cookie("starred", "|".join(starred_set), max_age=60 * 60 * 24 * 365)
    return resp


@app.post("/compare/add")
async def compare_add(request: Request, compare: str = Cookie(default="")):
    form = await request.form()
    slug = str(form.get("slug", ""))
    slugs = _parse_compare(compare)
    if slug and slug not in slugs:
        slugs.append(slug)
    referer = request.headers.get("referer", "/")
    resp = RedirectResponse(url=referer, status_code=303)
    resp.set_cookie("compare", "|".join(slugs), max_age=60 * 60 * 24 * 365)
    return resp


@app.post("/compare/remove")
async def compare_remove(request: Request, compare: str = Cookie(default="")):
    form = await request.form()
    slug = str(form.get("slug", ""))
    slugs = [s for s in _parse_compare(compare) if s != slug]
    referer = request.headers.get("referer", "/")
    resp = RedirectResponse(url=referer, status_code=303)
    resp.set_cookie("compare", "|".join(slugs), max_age=60 * 60 * 24 * 365)
    return resp


@app.post("/compare/clear")
async def compare_clear(request: Request):
    referer = request.headers.get("referer", "/")
    resp = RedirectResponse(url=referer, status_code=303)
    resp.set_cookie("compare", "", max_age=60 * 60 * 24 * 365)
    return resp


@app.get("/compare", response_class=HTMLResponse)
async def compare_page(
    request: Request,
    lang: str = Cookie(default="nl"),
    theme: str = Cookie(default="dark"),
    starred: str = Cookie(default=""),
    compare: str = Cookie(default=""),
):
    compare_slugs = _parse_compare(compare)
    starred_set = _parse_starred(starred)
    areas_meta = db.get_areas_meta(compare_slugs)
    comparison = db.get_comparison_data(compare_slugs, starred_set)
    scores: dict[str, dict[str, float]] = {}
    for topic, area_vals in comparison.items():
        nums = {s: _parse_numeric(d["value"]) for s, d in area_vals.items()}
        valid = {s: v for s, v in nums.items() if v is not None}
        if len(valid) >= 2:
            mn, mx = min(valid.values()), max(valid.values())
            if mx != mn:
                scores[topic] = {s: (v - mn) / (mx - mn) for s, v in valid.items()}
    return templates.TemplateResponse(
        request,
        "compare.html",
        {
            "lang": lang,
            "theme": theme,
            "compare_slugs": compare_slugs,
            "areas_meta": areas_meta,
            "starred": starred_set,
            "comparison": comparison,
            "scores": scores,
            "skip_units": _SKIP_UNITS,
        },
    )


@app.post("/set-lang")
async def set_lang(request: Request):
    form = await request.form()
    lang = form.get("lang", "nl")
    if lang not in ("nl", "en"):
        lang = "nl"
    referer = request.headers.get("referer", "/")
    resp = RedirectResponse(url=referer, status_code=303)
    resp.set_cookie("lang", lang, max_age=60 * 60 * 24 * 365)
    return resp


@app.post("/set-theme")
async def set_theme(request: Request):
    form = await request.form()
    theme = form.get("theme", "dark")
    if theme not in ("light", "dark"):
        theme = "dark"
    referer = request.headers.get("referer", "/")
    resp = RedirectResponse(url=referer, status_code=303)
    resp.set_cookie("theme", theme, max_age=60 * 60 * 24 * 365)
    return resp
