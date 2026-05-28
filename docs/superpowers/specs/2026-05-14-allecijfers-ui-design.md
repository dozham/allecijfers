# Allecijfers Neighborhood Statistics UI

**Date:** 2026-05-14  
**Stack:** FastAPI + HTMX + Jinja2 + SQLite  
**Status:** Approved

## What we're building

A local web UI for exploring neighborhood statistics scraped from allecijfers.nl. Users can search across all areas (wijken and buurten) in Amsterdam, Haarlem, and Utrecht, then drill into any area to see its full 472-row statistics table.

## Project structure

```
ui/
  main.py                      # FastAPI app, all routes
  db.py                        # SQLite connection and query functions
  templates/
    base.html                  # Shell: HTMX CDN, nav, CSS link
    index.html                 # Search/home page (extends base)
    area.html                  # Area detail page (extends base)
    partials/
      search_results.html      # HTMX partial — search results list
      stats_body.html          # HTMX partial — stats table body
  static/
    style.css
```

Lives at the project root alongside `allecijfers/` and `scrape_hierarchy.py`. Run with `uv run fastapi dev ui/main.py`.

## Routes

| Method | Path | Response |
|--------|------|----------|
| `GET` | `/` | Full search page |
| `GET` | `/search?q=&municipality=&type=` | **Partial** — results list (HTMX swap) |
| `GET` | `/area/{slug}` | Full area detail page |
| `GET` | `/area/{slug}/stats?q=` | **Partial** — stats body (HTMX swap) |
| `POST` | `/set-lang` | Sets `lang` cookie, redirects back (via `Referer`) |

Partial routes return HTML fragments with no `<html>` wrapper.

## Data layer (`db.py`)

Three query functions, each returning plain dicts/lists:

### `search_areas(q, municipality, area_type) → list`

```sql
SELECT DISTINCT area_slug, area_name, area_type, municipality
FROM stats
WHERE area_name LIKE '%q%'
  AND municipality = :municipality   -- omitted when "all"
  AND area_type = :area_type         -- omitted when "all"
ORDER BY municipality, area_name
LIMIT 50
```

### `get_area_stats(slug, q="") → dict[category, list[row]]`

```sql
SELECT category, topic, value, unit, year
FROM stats
WHERE area_slug = :slug
  AND (topic LIKE '%q%' OR category LIKE '%q%')  -- omitted when q is empty
ORDER BY category, topic
```

Returns rows grouped by category. When `q` is empty all 472 rows come back. When `q` is set, matching rows come back flat (template renders them differently).

### `get_area_hierarchy(slug, area_type) → dict`

Queries `area_hierarchy` table:
- **buurt**: returns `{wijk_slug, wijk_name, siblings: [buurt_slug, buurt_name, ...]}`
- **wijk**: returns `{buurten: [buurt_slug, buurt_name, ...]}`

## Search page (`/`)

- Large search input: `hx-get="/search"` on `keyup`, 200ms debounce, targets `#results`
- Filter chips for municipality (All / Amsterdam / Haarlem / Utrecht) and type (All / wijk / buurt): implemented as hidden inputs inside the same `<form>`, clicking a chip updates the value and re-triggers the search
- Results list: each row is `<a href="/area/{slug}">` with area name, type badge, and municipality — full page navigation on click

## Area detail page (`/area/{slug}`)

Layout top to bottom:

1. **Header** — area name, area_type badge (wijk / buurt), municipality
2. **Summary cards** — 4 hardcoded topics rendered server-side on page load:
   - `Inwoners` (category: Bevolking)
   - `Gemiddeld inkomen per inwoner` (category: Inkomen)
   - `% Huurwoningen` (category: Woningen)
   - `Misdrijven` (category: Misdrijven)
   
   Topics missing for an area are silently omitted.

3. **Stats search input** — `hx-get="/area/{slug}/stats"` on `keyup`, 200ms debounce, targets `#stats-body`

4. **Stats body** (`#stats-body`) — two modes, both served by `/area/{slug}/stats`:
   - **Browse mode** (`q` empty): 15 `<details>` elements, one per category, each containing a `<table>` with topic / value / unit / year. Browser handles open/close natively.
   - **Search mode** (`q` non-empty): single flat `<table>` with category / topic / value / unit / year columns showing only matching rows.

5. **Hierarchy panel** — rendered server-side:
   - buurt page: link to parent wijk + list of sibling buurten
   - wijk page: list of child buurten

## HTMX wiring summary

| Trigger | Event | Target | Result |
|---------|-------|--------|--------|
| Search input on `/` | `keyup` 200ms | `#results` | Swaps in `search_results.html` partial |
| Filter chip click on `/` | `change` | `#results` | Same partial with updated filters |
| Stats search input on `/area/{slug}` | `keyup` 200ms | `#stats-body` | Swaps in `stats_body.html` partial |

No custom JavaScript. HTMX served from CDN. `<details>` handles category collapse natively.

## Internationalisation (NL / EN)

The UI supports Dutch (default) and English via a toggle in the nav bar. Language preference is stored in a browser cookie (`lang=nl` or `lang=en`).

**Translation loading:** `db.py` reads `allecijfers/data/translations.csv` at startup into a `dict[str, str]` keyed on Dutch term. The file covers all 472 topics, 15 categories, and area-type terms (`buurt`, `wijk`, `gemeente`) in a simple two-column `dutch,english` format — reusable for any Dutch neighbourhood stats dataset. 89 topics are covered; untranslated topics fall back to Dutch in both modes.

**Category name mapping:** hardcoded dict in `db.py` mapping the 15 Dutch DB categories to English equivalents:

```python
CATEGORY_TRANSLATIONS = {
    "Bevolking": "Demographics",
    "Bedrijven": "Businesses",
    "Energieverbruik": "Energy use",
    "Gezondheid-gedrag": "Health behaviour",
    "Gezondheid-overig": "Health other",
    "Gezondheid-ziekte": "Health illness",
    "Huishoudens": "Households",
    "Inkomen": "Income",
    "Migratie": "Migration",
    "Misdrijven": "Crime",
    "Nabijheid voorzieningen": "Proximity to amenities",
    "Omgeving": "Environment",
    "Verkeersongevallen": "Traffic accidents",
    "Vervoer": "Transport",
    "Woningen": "Housing",
}
```

**Template integration:** a Jinja2 `translate_topic` filter and `translate_category` filter are registered at app startup. Templates call `{{ topic | translate_topic }}` and `{{ category | translate_category }}`. When `lang=nl`, both filters are identity functions (no translation applied).

**HTMX:** partial requests carry the cookie automatically — no extra query params needed.

**Toggle:** a NL / EN button in `base.html` POSTs to `/set-lang` which sets the cookie and redirects back.

## Dependencies to add

```toml
# pyproject.toml
fastapi[standard]
jinja2
```

SQLite is stdlib. The existing `allecijfers/data/allecijfers.db` is used read-only by the UI.
