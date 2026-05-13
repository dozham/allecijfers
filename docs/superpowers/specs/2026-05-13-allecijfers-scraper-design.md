# allecijfers.nl Neighborhood Statistics Scraper — Design Spec

**Date:** 2026-05-13  
**Status:** Approved

---

## Context

[allecijfers.nl](https://allecijfers.nl) publishes CBS/government statistics for every neighborhood (wijk and buurt) in the Netherlands. Each neighborhood page (e.g. `/wijk/elzenhagen-amsterdam/`) contains a static HTML table with 250+ rows of statistics covering topics like population, income, housing, crime, energy, and health.

The goal is to scrape all neighborhood statistics for **Amsterdam** (630 areas: mix of `/wijk/` and `/buurt/` URLs) and store them in a local SQLite database for analysis. The design should make it straightforward to later extend to all ~320 municipalities in the Netherlands.

---

## Architecture

A single **Scrapy project** with one spider that runs in two logical phases within a single `scrapy crawl` invocation:

1. **Index phase** — spider starts at `/gemeente-overzicht/amsterdam/`, extracts all `/wijk/` and `/buurt/` links (~630 URLs)
2. **Extraction phase** — for each neighborhood URL, fetches the page and parses the 250-row statistics table

### Project Layout

```
allcharts-scraper/
├── allecijfers/
│   ├── scrapy.cfg
│   └── allecijfers/
│       ├── __init__.py
│       ├── settings.py
│       ├── items.py
│       ├── pipelines.py
│       └── spiders/
│           └── amsterdam.py
├── data/
│   └── allecijfers.db       # output SQLite database
└── docs/
    └── superpowers/specs/
        └── this file
```

### Spider: `AmsterdamSpider`

- **`name`**: `amsterdam`
- **`start_urls`**: `["https://allecijfers.nl/gemeente-overzicht/amsterdam/"]`
- **`parse`** (index): CSS-selects all `a[href*="/wijk/"], a[href*="/buurt/"]` links → yields one `Request` per neighborhood with callback `parse_neighborhood`
- **`parse_neighborhood`**: extracts area name from page heading, walks the 250-row table tracking category headers (rows with `<th>` spanning all columns or styled as section headers), yields one `StatsItem` per data row

### Item: `StatsItem`

```python
municipality: str   # "amsterdam"
area_type:    str   # "wijk" | "buurt"
area_slug:    str   # "elzenhagen-amsterdam"
area_name:    str   # display name from page <h1>
url:          str   # full page URL
category:     str   # "Bevolking", "Inkomen", etc.
topic:        str   # "Inwoners"
value:        str   # raw string (preserves "<1", "n.v.t.", "%")
unit:         str   # "Aantal", "%", "Euro"
year:         str   # "2025"
scraped_at:   str   # ISO-8601 timestamp
```

---

## Data Model

Single flat SQLite table — simplifies cross-neighborhood queries.

```sql
CREATE TABLE IF NOT EXISTS stats (
    id           INTEGER PRIMARY KEY,
    municipality TEXT    NOT NULL,
    area_type    TEXT    NOT NULL,
    area_slug    TEXT    NOT NULL,
    area_name    TEXT,
    url          TEXT    NOT NULL,
    category     TEXT,
    topic        TEXT    NOT NULL,
    value        TEXT,
    unit         TEXT,
    year         TEXT,
    scraped_at   TEXT    NOT NULL,
    UNIQUE (url, topic)
);

CREATE INDEX IF NOT EXISTS idx_slug  ON stats(area_slug);
CREATE INDEX IF NOT EXISTS idx_topic ON stats(topic);
```

`value` is stored as TEXT to preserve non-numeric values (`<1`, `n.v.t.`, etc.).

---

## Settings

```python
# settings.py
DOWNLOAD_DELAY = 0         # no artificial delay (user preference)
CONCURRENT_REQUESTS = 16   # Scrapy default
RETRY_TIMES = 3
ROBOTSTXT_OBEY = True
ITEM_PIPELINES = {"allecijfers.pipelines.SQLitePipeline": 300}
SQLITE_DATABASE = "data/allecijfers.db"
```

---

## Pipeline: `SQLitePipeline`

- Opens `data/allecijfers.db` on spider open, creates schema if not exists
- Batches inserts using `executemany` every 500 items for performance
- Flushes remaining batch on spider close
- Uses `INSERT OR REPLACE` to allow safe reruns without duplicates (keyed on `url + topic`)

---

## Error Handling

- Scrapy's `RetryMiddleware` handles transient HTTP errors (500, 503, timeouts) with 3 retries
- If a neighborhood page returns 404 or the stats table is absent, log a `WARNING` with the URL and skip — the crawl continues
- Missing neighborhoods are detectable post-hoc: compare scraped URLs against expected count

---

## Running the Scraper

```bash
cd allcharts-scraper/allecijfers
pip install scrapy
scrapy crawl amsterdam
```

Output: `data/allecijfers.db`

**Sample query:**
```sql
SELECT area_name, value, unit, year
FROM stats
WHERE topic = 'Inwoners'
ORDER BY CAST(value AS REAL) DESC;
```

---

## Future Extensibility

To scrape all ~320 Dutch municipalities:
1. Add a `NetherlandsSpider` with `start_urls = ["https://allecijfers.nl/gebieden/"]`
2. Parse all `/gemeente-overzicht/[name]/` links → collect neighborhood links per municipality
3. Reuse the same `parse_neighborhood` callback and `StatsItem` — only `municipality` changes
4. Consider adding `DOWNLOAD_DELAY = 0.5` for the larger run

---

## Verification

1. `scrapy crawl amsterdam` completes without unhandled exceptions
2. `SELECT COUNT(DISTINCT area_slug) FROM stats;` returns ~630
3. `SELECT COUNT(*) FROM stats WHERE area_slug = 'elzenhagen-amsterdam';` returns ~250
4. Spot-check: `SELECT * FROM stats WHERE area_slug = 'elzenhagen-amsterdam' AND topic = 'Inwoners';` matches value on live page
5. No area_slug has 0 rows without a corresponding WARNING in logs
