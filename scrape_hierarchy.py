"""Scrape wijk→buurt relationships from gemeente-overzicht pages
and write them to the area_hierarchy table in the SQLite database.
"""

import re
import sqlite3
import urllib.request

DB_PATH = "data/allecijfers.db"
MUNICIPALITIES = ["amsterdam", "haarlem", "utrecht"]
BASE_URL = "https://allecijfers.nl/gemeente-overzicht/{municipality}/"
HEADERS = {"User-Agent": "Mozilla/5.0"}

ROW_RE = re.compile(
    r'href="/(wijk|buurt)/([^"]+)"[^>]+target="_blank">([^<]+)</a></td><td>(Wijk|Buurt)</td>'
)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        return resp.read().decode("utf-8")


def parse_hierarchy(html: str, municipality: str) -> list[tuple]:
    rows = []
    current_wijk_slug = None
    current_wijk_name = None

    for area_type, slug, name, label in ROW_RE.findall(html):
        if label == "Wijk":
            current_wijk_slug = slug
            current_wijk_name = name.strip()
        elif label == "Buurt" and current_wijk_slug:
            rows.append((municipality, current_wijk_slug, current_wijk_name, slug, name.strip()))

    return rows


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS area_hierarchy (
            municipality TEXT NOT NULL,
            wijk_slug    TEXT NOT NULL,
            wijk_name    TEXT NOT NULL,
            buurt_slug   TEXT NOT NULL,
            buurt_name   TEXT NOT NULL,
            PRIMARY KEY (municipality, buurt_slug)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_hier_wijk ON area_hierarchy(municipality, wijk_slug)")
    conn.commit()

    for municipality in MUNICIPALITIES:
        url = BASE_URL.format(municipality=municipality)
        print(f"Fetching {url} ...", end=" ", flush=True)
        html = fetch(url)
        rows = parse_hierarchy(html, municipality)
        conn.executemany(
            "INSERT OR REPLACE INTO area_hierarchy VALUES (?,?,?,?,?)",
            rows,
        )
        conn.commit()
        print(f"{len(rows)} buurt→wijk mappings written")

    conn.close()


if __name__ == "__main__":
    main()
