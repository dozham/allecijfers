import csv
import sqlite3
from pathlib import Path

_ROOT = Path(__file__).parent.parent
DB_PATH = _ROOT / "allecijfers" / "data" / "allecijfers.db"
_TRANSLATIONS_PATH = _ROOT / "allecijfers" / "data" / "translations.csv"

_translations: dict[str, str] | None = None


def load_translations() -> dict[str, str]:
    global _translations
    if _translations is None:
        _translations = {}
        with open(_TRANSLATIONS_PATH, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                _translations[row["dutch"]] = row["english"]
    return _translations


def translate(term: str, lang: str) -> str:
    if lang != "en":
        return term
    return load_translations().get(term, term)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_municipalities() -> list[str]:
    sql = "SELECT DISTINCT municipality FROM stats ORDER BY municipality"
    with get_connection() as conn:
        return [r[0] for r in conn.execute(sql).fetchall()]


_PER_PAGE = 20


def _search_where(q: str, municipality: str, area_type: str) -> tuple[str, list]:
    params: list[str] = [f"%{q}%"]
    where = "area_name LIKE ?"
    if municipality:
        where += " AND municipality = ?"
        params.append(municipality)
    if area_type:
        where += " AND area_type = ?"
        params.append(area_type)
    return where, params


def count_areas(q: str, municipality: str = "", area_type: str = "") -> int:
    where, params = _search_where(q, municipality, area_type)
    sql = f"SELECT COUNT(DISTINCT area_slug) FROM stats WHERE {where}"
    with get_connection() as conn:
        return conn.execute(sql, params).fetchone()[0]


def search_areas(
    q: str, municipality: str = "", area_type: str = "", page: int = 1
) -> list[dict]:
    where, params = _search_where(q, municipality, area_type)
    offset = (page - 1) * _PER_PAGE
    sql = (
        f"SELECT DISTINCT area_slug, area_name, area_type, municipality "
        f"FROM stats WHERE {where} "
        f"ORDER BY municipality, area_name LIMIT {_PER_PAGE} OFFSET {offset}"
    )
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


def get_area_meta(slug: str) -> dict | None:
    sql = (
        "SELECT DISTINCT area_slug, area_name, area_type, municipality, url "
        "FROM stats WHERE area_slug = ? LIMIT 1"
    )
    with get_connection() as conn:
        row = conn.execute(sql, [slug]).fetchone()
    return dict(row) if row else None


def get_area_stats(slug: str, q: str = "") -> dict[str, list[dict]]:
    params: list[str] = [slug]
    sql = "SELECT category, topic, value, unit, year FROM stats WHERE area_slug = ?"
    if q:
        sql += " AND (topic LIKE ? OR category LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%"])
    sql += " ORDER BY category, topic"
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        cat = row["category"]
        if cat not in grouped:
            grouped[cat] = []
        grouped[cat].append(dict(row))
    return grouped


def get_areas_meta(slugs: list[str]) -> dict[str, dict]:
    if not slugs:
        return {}
    ph = ",".join("?" * len(slugs))
    sql = (
        f"SELECT area_slug, area_name, area_type, municipality, url "
        f"FROM stats WHERE area_slug IN ({ph}) GROUP BY area_slug"
    )
    with get_connection() as conn:
        rows = conn.execute(sql, slugs).fetchall()
    return {r["area_slug"]: dict(r) for r in rows}


def get_comparison_data(slugs: list[str], topics: set[str]) -> dict[str, dict[str, dict]]:
    """Returns {topic: {slug: {value, unit, year}}}"""
    if not slugs or not topics:
        return {}
    ph_s = ",".join("?" * len(slugs))
    ph_t = ",".join("?" * len(topics))
    sql = (
        f"SELECT area_slug, topic, value, unit, year FROM stats "
        f"WHERE area_slug IN ({ph_s}) AND topic IN ({ph_t})"
    )
    with get_connection() as conn:
        rows = conn.execute(sql, list(slugs) + list(topics)).fetchall()
    result: dict[str, dict[str, dict]] = {t: {} for t in topics}
    for row in rows:
        result[row["topic"]][row["area_slug"]] = {
            "value": row["value"], "unit": row["unit"], "year": row["year"],
        }
    return result


def get_area_hierarchy(slug: str, area_type: str) -> dict:
    with get_connection() as conn:
        try:
            conn.execute("SELECT 1 FROM area_hierarchy LIMIT 1")
        except Exception:
            return {}
        if area_type == "buurt":
            row = conn.execute(
                "SELECT wijk_slug, wijk_name FROM area_hierarchy WHERE buurt_slug = ?",
                [slug],
            ).fetchone()
            if not row:
                return {}
            siblings = conn.execute(
                "SELECT buurt_slug, buurt_name FROM area_hierarchy "
                "WHERE wijk_slug = ? AND buurt_slug != ? ORDER BY buurt_name",
                [row["wijk_slug"], slug],
            ).fetchall()
            return {
                "parent_wijk": dict(row),
                "siblings": [dict(r) for r in siblings],
            }
        if area_type == "wijk":
            buurten = conn.execute(
                "SELECT buurt_slug, buurt_name FROM area_hierarchy "
                "WHERE wijk_slug = ? ORDER BY buurt_name",
                [slug],
            ).fetchall()
            return {"buurten": [dict(r) for r in buurten]}
    return {}
