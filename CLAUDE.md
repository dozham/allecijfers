# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Scrapes neighborhood statistics from [allecijfers.nl](https://allecijfers.nl) — a Dutch government statistics aggregator — and stores them in a local SQLite database for analysis and visualization. Each neighborhood page contains 15 per-category tables with ~472 rows of statistics (population, income, housing, crime, health, etc.).

Currently scraped: **Amsterdam** (624 areas), **Haarlem** (132), **Utrecht** (121) → ~415k rows total.

## Running the scraper

All commands run from the project root. The `.venv` is managed by `uv`; use it directly since `uv run scrapy` panics on this machine.

```bash
# Scrape a municipality (default: amsterdam)
cd allecijfers
../.venv/bin/scrapy crawl neighborhood -a municipality=amsterdam
../.venv/bin/scrapy crawl neighborhood -a municipality=utrecht
../.venv/bin/scrapy crawl neighborhood -a municipality=haarlem

# Scrape wijk→buurt hierarchy (run from project root, after stats scrape)
.venv/bin/python scrape_hierarchy.py
```

Output goes to `data/allecijfers.db`. Re-running is safe — inserts use `INSERT OR REPLACE` keyed on `(url, topic)`.

## Project structure

```
allecijfers/               # Scrapy project root (scrapy.cfg lives here)
  allecijfers/
    spiders/amsterdam.py   # NeighborhoodSpider — one spider handles all municipalities
    pipelines.py           # SQLitePipeline — batched writes (500/flush) to SQLite
    items.py               # StatsItem definition
    settings.py            # TELNETCONSOLE_ENABLED=False required (sandbox restriction)
scrape_hierarchy.py        # Standalone script — scrapes wijk→buurt parent relationships
data/allecijfers.db        # SQLite output
data/topic_translations.csv # Dutch→English topic name mappings
```

## Database schema

**`stats`** — one row per statistic per neighborhood page:
```
municipality, area_type (wijk|buurt), area_slug, area_name, url,
category, topic, value (TEXT — preserves "<1", "n.v.t.", "50%"),
unit, year, scraped_at
UNIQUE(url, topic)
```

**`area_hierarchy`** — wijk→buurt parent relationships:
```
municipality, wijk_slug, wijk_name, buurt_slug, buurt_name
PRIMARY KEY(municipality, buurt_slug)
```

## Key scraping details

- Stats tables are **static HTML** — no JS rendering needed
- Each neighborhood page has **15 separate `<table>` elements**, one per category. The category name is the first `<th>` of each table; the column pattern is `Category | Waarde | Eenheid | Jaar`
- Area name comes from `<span itemprop='name'>` (prefixed with "wijk " or "buurt " — stripped by the spider)
- Wijk→buurt hierarchy is scraped from `/gemeente-overzicht/<municipality>/` where rows appear in wijk-then-buurten order

## Extending to new municipalities

Add the municipality slug (as it appears in allecijfers.nl URLs) to `MUNICIPALITIES` in `scrape_hierarchy.py`, then run both the spider and the hierarchy script. The spider and pipeline are fully generic.

## Values quirk

Dutch number formatting: `"2.080"` = 2080 (period = thousands separator, comma = decimal). Cast for numeric queries:
```sql
CAST(REPLACE(REPLACE(value, '.', ''), ',', '.') AS REAL)
```
