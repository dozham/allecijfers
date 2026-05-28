# Allecijfers UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a FastAPI + HTMX web UI for searching and exploring Dutch neighbourhood statistics stored in a local SQLite database.

**Architecture:** A single FastAPI app with Jinja2 server-side rendering. HTMX handles two partial swaps (search results, stats body) — no custom JS. Language (NL/EN) is stored in a cookie; a `translate()` helper applied in templates handles all term lookups from `allecijfers/data/translations.csv`.

**Tech Stack:** FastAPI, Jinja2, HTMX (CDN), SQLite (stdlib), pytest + httpx

---

## File map

| File | Responsibility |
|------|----------------|
| `ui/__init__.py` | Empty package marker |
| `ui/db.py` | SQLite queries + translation loading |
| `ui/main.py` | FastAPI app, all routes, Jinja2 setup |
| `ui/templates/base.html` | Shell: HTMX CDN, nav, lang toggle, CSS |
| `ui/templates/index.html` | Search/home page |
| `ui/templates/area.html` | Area detail page |
| `ui/templates/partials/search_results.html` | HTMX partial — results list |
| `ui/templates/partials/stats_body.html` | HTMX partial — stats table |
| `ui/static/style.css` | All styles |
| `tests/ui/conftest.py` | Fixture DB + TestClient |
| `tests/ui/test_db.py` | Unit tests for db.py functions |
| `tests/ui/test_routes.py` | Integration tests for all routes |

---

## Task 1: Dependencies + project scaffold

**Files:**
- Modify: `pyproject.toml`
- Create: `ui/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/ui/__init__.py`

- [ ] **Step 1: Add dependencies**

Edit `pyproject.toml` — replace the `dependencies` list:

```toml
dependencies = [
    "scrapy>=2.15.2",
    "fastapi[standard]>=0.115",
    "jinja2>=3.1",
    "httpx>=0.27",
    "pytest>=8",
]
```

- [ ] **Step 2: Install**

```bash
uv sync
```

Expected: resolves and installs without errors.

- [ ] **Step 3: Create package markers and directory structure**

```bash
mkdir -p ui/templates/partials ui/static tests/ui
touch ui/__init__.py tests/__init__.py tests/ui/__init__.py
```

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml uv.lock ui/__init__.py tests/__init__.py tests/ui/__init__.py
git commit -m "chore: add fastapi, jinja2, httpx, pytest dependencies"
```

---

## Task 2: db.py — translations + connection

**Files:**
- Create: `ui/db.py`
- Create: `tests/ui/test_db.py`

- [ ] **Step 1: Write the failing test**

Create `tests/ui/test_db.py`:

```python
from ui.db import load_translations, translate

def test_load_translations_returns_dict():
    t = load_translations()
    assert isinstance(t, dict)
    assert len(t) > 400

def test_known_translation():
    assert translate("Inwoners", "en") == "Residents"

def test_dutch_passthrough():
    assert translate("Inwoners", "nl") == "Inwoners"

def test_missing_term_fallback():
    assert translate("__onbekend__", "en") == "__onbekend__"

def test_category_translation():
    assert translate("Bevolking", "en") == "Demographics"

def test_area_type_translation():
    assert translate("buurt", "en") == "neighbourhood"
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/ui/test_db.py -v
```

Expected: `ModuleNotFoundError: No module named 'ui.db'`

- [ ] **Step 3: Implement db.py**

Create `ui/db.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify passing**

```bash
uv run pytest tests/ui/test_db.py -v
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ui/db.py tests/ui/test_db.py
git commit -m "feat: add db.py translation loading"
```

---

## Task 3: db.py — search_areas

**Files:**
- Modify: `ui/db.py`
- Modify: `tests/ui/test_db.py`
- Create: `tests/ui/conftest.py`

- [ ] **Step 1: Create fixture DB**

Create `tests/ui/conftest.py`:

```python
import sqlite3
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def patch_db(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE stats (
            id INTEGER PRIMARY KEY,
            municipality TEXT NOT NULL,
            area_type TEXT NOT NULL,
            area_slug TEXT NOT NULL,
            area_name TEXT,
            url TEXT NOT NULL,
            category TEXT,
            topic TEXT NOT NULL,
            value TEXT,
            unit TEXT,
            year TEXT,
            scraped_at TEXT NOT NULL,
            UNIQUE (area_slug, topic)
        );
        CREATE TABLE area_hierarchy (
            municipality TEXT,
            wijk_slug TEXT,
            wijk_name TEXT,
            buurt_slug TEXT,
            buurt_name TEXT,
            PRIMARY KEY(municipality, buurt_slug)
        );
        INSERT INTO stats VALUES
            (1,'amsterdam','wijk','oud-west-amsterdam','Oud-West',
             'https://allecijfers.nl/wijk/oud-west-amsterdam/',
             'Bevolking','Inwoners','25000','Aantal','2023','2024-01-01'),
            (2,'amsterdam','wijk','oud-west-amsterdam','Oud-West',
             'https://allecijfers.nl/wijk/oud-west-amsterdam/',
             'Inkomen','Gemiddeld inkomen per inwoner','35000','€','2022','2024-01-01'),
            (3,'amsterdam','wijk','oud-west-amsterdam','Oud-West',
             'https://allecijfers.nl/wijk/oud-west-amsterdam/',
             'Woningen','% Huurwoningen','65','%','2023','2024-01-01'),
            (4,'amsterdam','wijk','oud-west-amsterdam','Oud-West',
             'https://allecijfers.nl/wijk/oud-west-amsterdam/',
             'Misdrijven','Misdrijven','500','Aantal','2023','2024-01-01'),
            (5,'amsterdam','buurt','de-pijp-amsterdam','De Pijp',
             'https://allecijfers.nl/buurt/de-pijp-amsterdam/',
             'Bevolking','Inwoners','15000','Aantal','2023','2024-01-01'),
            (6,'haarlem','buurt','centrum-haarlem','Centrum',
             'https://allecijfers.nl/buurt/centrum-haarlem/',
             'Bevolking','Inwoners','8000','Aantal','2023','2024-01-01');
        INSERT INTO area_hierarchy VALUES
            ('amsterdam','oud-west-amsterdam','Oud-West','de-pijp-amsterdam','De Pijp');
    """)
    conn.commit()
    conn.close()
    monkeypatch.setattr("ui.db.DB_PATH", db_path)
    monkeypatch.setattr("ui.db._translations", None)


@pytest.fixture
def client():
    from ui.main import app
    return TestClient(app, follow_redirects=True)
```

- [ ] **Step 2: Write the failing tests**

Append to `tests/ui/test_db.py`:

```python
from ui.db import search_areas


def test_search_returns_matching_areas():
    results = search_areas("pijp")
    assert len(results) == 1
    assert results[0]["area_slug"] == "de-pijp-amsterdam"


def test_search_empty_query_returns_all():
    results = search_areas("")
    assert len(results) == 3  # oud-west, de-pijp, centrum


def test_search_filter_by_municipality():
    results = search_areas("", municipality="haarlem")
    assert all(r["municipality"] == "haarlem" for r in results)
    assert len(results) == 1


def test_search_filter_by_type():
    results = search_areas("", area_type="wijk")
    assert all(r["area_type"] == "wijk" for r in results)
    assert len(results) == 1


def test_search_result_keys():
    results = search_areas("oud")
    assert set(results[0].keys()) >= {"area_slug", "area_name", "area_type", "municipality"}
```

- [ ] **Step 3: Run to verify failure**

```bash
uv run pytest tests/ui/test_db.py::test_search_returns_matching_areas -v
```

Expected: `ImportError` or `AttributeError: module 'ui.db' has no attribute 'search_areas'`

- [ ] **Step 4: Implement search_areas**

Append to `ui/db.py`:

```python
def search_areas(q: str, municipality: str = "", area_type: str = "") -> list[dict]:
    params: list[str] = [f"%{q}%"]
    sql = (
        "SELECT DISTINCT area_slug, area_name, area_type, municipality "
        "FROM stats WHERE area_name LIKE ?"
    )
    if municipality:
        sql += " AND municipality = ?"
        params.append(municipality)
    if area_type:
        sql += " AND area_type = ?"
        params.append(area_type)
    sql += " ORDER BY municipality, area_name LIMIT 50"
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
```

- [ ] **Step 5: Run tests**

```bash
uv run pytest tests/ui/test_db.py -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add ui/db.py tests/ui/test_db.py tests/ui/conftest.py
git commit -m "feat: add search_areas query"
```

---

## Task 4: db.py — get_area_meta + get_area_stats

**Files:**
- Modify: `ui/db.py`
- Modify: `tests/ui/test_db.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/ui/test_db.py`:

```python
from ui.db import get_area_meta, get_area_stats


def test_get_area_meta_returns_dict():
    meta = get_area_meta("oud-west-amsterdam")
    assert meta is not None
    assert meta["area_name"] == "Oud-West"
    assert meta["area_type"] == "wijk"
    assert meta["municipality"] == "amsterdam"


def test_get_area_meta_missing_slug_returns_none():
    assert get_area_meta("does-not-exist") is None


def test_get_area_stats_returns_grouped():
    stats = get_area_stats("oud-west-amsterdam")
    assert "Bevolking" in stats
    assert stats["Bevolking"][0]["topic"] == "Inwoners"
    assert stats["Bevolking"][0]["value"] == "25000"


def test_get_area_stats_with_query_filters():
    stats = get_area_stats("oud-west-amsterdam", q="inkomen")
    assert "Bevolking" not in stats
    assert "Inkomen" in stats


def test_get_area_stats_empty_query_returns_all():
    stats = get_area_stats("oud-west-amsterdam")
    total = sum(len(rows) for rows in stats.values())
    assert total == 4
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/ui/test_db.py::test_get_area_meta_returns_dict -v
```

Expected: `ImportError` — `get_area_meta` not defined.

- [ ] **Step 3: Implement get_area_meta and get_area_stats**

Append to `ui/db.py`:

```python
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
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/ui/test_db.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ui/db.py tests/ui/test_db.py
git commit -m "feat: add get_area_meta and get_area_stats queries"
```

---

## Task 5: db.py — get_area_hierarchy

**Files:**
- Modify: `ui/db.py`
- Modify: `tests/ui/test_db.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/ui/test_db.py`:

```python
from ui.db import get_area_hierarchy


def test_hierarchy_for_buurt_returns_parent_wijk():
    h = get_area_hierarchy("de-pijp-amsterdam", "buurt")
    assert h["parent_wijk"]["wijk_slug"] == "oud-west-amsterdam"
    assert h["parent_wijk"]["wijk_name"] == "Oud-West"


def test_hierarchy_for_buurt_with_no_siblings():
    h = get_area_hierarchy("de-pijp-amsterdam", "buurt")
    assert h["siblings"] == []


def test_hierarchy_for_wijk_returns_buurten():
    h = get_area_hierarchy("oud-west-amsterdam", "wijk")
    assert len(h["buurten"]) == 1
    assert h["buurten"][0]["buurt_slug"] == "de-pijp-amsterdam"


def test_hierarchy_for_unknown_buurt_returns_empty():
    h = get_area_hierarchy("does-not-exist", "buurt")
    assert h == {}
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/ui/test_db.py::test_hierarchy_for_buurt_returns_parent_wijk -v
```

Expected: `ImportError` — `get_area_hierarchy` not defined.

- [ ] **Step 3: Implement get_area_hierarchy**

Append to `ui/db.py`:

```python
def get_area_hierarchy(slug: str, area_type: str) -> dict:
    with get_connection() as conn:
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
```

- [ ] **Step 4: Run tests**

```bash
uv run pytest tests/ui/test_db.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add ui/db.py tests/ui/test_db.py
git commit -m "feat: add get_area_hierarchy query"
```

---

## Task 6: FastAPI app skeleton + base template + /set-lang

**Files:**
- Create: `ui/main.py`
- Create: `ui/templates/base.html`
- Create: `ui/static/style.css` (stub)
- Modify: `tests/ui/test_routes.py` (create)

- [ ] **Step 1: Write the failing route test**

Create `tests/ui/test_routes.py`:

```python
def test_homepage_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "allecijfers" in resp.text.lower()


def test_set_lang_sets_cookie(client):
    resp = client.post("/set-lang", data={"lang": "en"})
    assert resp.status_code == 200
    assert client.cookies.get("lang") == "en"


def test_set_lang_rejects_invalid(client):
    client.post("/set-lang", data={"lang": "de"})
    assert client.cookies.get("lang") == "nl"
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/ui/test_routes.py -v
```

Expected: `ModuleNotFoundError: No module named 'ui.main'`

- [ ] **Step 3: Create ui/main.py**

```python
from pathlib import Path

from fastapi import Cookie, FastAPI, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import ui.db as db

_HERE = Path(__file__).parent

app = FastAPI()
app.mount("/static", StaticFiles(directory=_HERE / "static"), name="static")
templates = Jinja2Templates(directory=_HERE / "templates")
templates.env.globals["translate"] = db.translate


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, lang: str = Cookie(default="nl")):
    return templates.TemplateResponse(
        "index.html", {"request": request, "lang": lang}
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
```

- [ ] **Step 4: Create ui/static/style.css (stub)**

```css
/* styles added in Task 10 */
```

- [ ] **Step 5: Create ui/templates/base.html**

```html
<!DOCTYPE html>
<html lang="{{ lang }}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Allecijfers Explorer</title>
  <script src="https://unpkg.com/htmx.org@1.9.12" defer></script>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <nav class="nav">
    <a href="/" class="nav-brand">Allecijfers</a>
    <form method="post" action="/set-lang" class="lang-toggle">
      <button type="submit" name="lang" value="nl"
              class="lang-btn {% if lang == 'nl' %}active{% endif %}">NL</button>
      <button type="submit" name="lang" value="en"
              class="lang-btn {% if lang == 'en' %}active{% endif %}">EN</button>
    </form>
  </nav>
  <main class="container">
    {% block content %}{% endblock %}
  </main>
</body>
</html>
```

- [ ] **Step 6: Create ui/templates/index.html (stub)**

```html
{% extends "base.html" %}
{% block content %}
<h1>Allecijfers Explorer</h1>
{% endblock %}
```

- [ ] **Step 7: Run tests**

```bash
uv run pytest tests/ui/test_routes.py -v
```

Expected: all 3 tests PASS.

- [ ] **Step 8: Commit**

```bash
git add ui/main.py ui/templates/base.html ui/templates/index.html ui/static/style.css tests/ui/test_routes.py
git commit -m "feat: add fastapi app skeleton, base template, /set-lang route"
```

---

## Task 7: Search page (GET / + GET /search)

**Files:**
- Modify: `ui/main.py`
- Modify: `ui/templates/index.html`
- Create: `ui/templates/partials/search_results.html`
- Modify: `tests/ui/test_routes.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/ui/test_routes.py`:

```python
def test_search_returns_partial_html(client):
    resp = client.get("/search?q=pijp")
    assert resp.status_code == 200
    assert "de-pijp-amsterdam" in resp.text
    assert "<!DOCTYPE" not in resp.text  # must be a fragment, not full page


def test_search_empty_shows_all(client):
    resp = client.get("/search?q=")
    assert resp.status_code == 200
    assert "Oud-West" in resp.text
    assert "De Pijp" in resp.text


def test_search_filter_municipality(client):
    resp = client.get("/search?q=&municipality=haarlem")
    assert resp.status_code == 200
    assert "Centrum" in resp.text
    assert "Oud-West" not in resp.text


def test_search_result_links_to_area(client):
    resp = client.get("/search?q=pijp")
    assert "/area/de-pijp-amsterdam" in resp.text


def test_search_shows_type_badge(client):
    resp = client.get("/search?q=pijp")
    assert "buurt" in resp.text
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/ui/test_routes.py::test_search_returns_partial_html -v
```

Expected: 404 — `/search` route not defined.

- [ ] **Step 3: Add /search route to ui/main.py**

Append to `ui/main.py` (after the `/` route):

```python
@app.get("/search", response_class=HTMLResponse)
async def search(
    request: Request,
    q: str = "",
    municipality: str = "",
    type: str = "",
    lang: str = Cookie(default="nl"),
):
    results = db.search_areas(q, municipality, type)
    return templates.TemplateResponse(
        "partials/search_results.html",
        {"request": request, "results": results, "lang": lang},
    )
```

- [ ] **Step 4: Create ui/templates/partials/search_results.html**

```html
{% if results %}
<ul class="results-list">
  {% for r in results %}
  <li>
    <a href="/area/{{ r.area_slug }}" class="result-item">
      <span class="result-name">{{ r.area_name }}</span>
      <span class="result-badges">
        <span class="badge badge-type">{{ translate(r.area_type, lang) }}</span>
        <span class="badge badge-city">{{ r.municipality }}</span>
      </span>
    </a>
  </li>
  {% endfor %}
</ul>
{% else %}
<p class="no-results">
  {{ "No results found." if lang == "en" else "Geen resultaten gevonden." }}
</p>
{% endif %}
```

- [ ] **Step 5: Update ui/templates/index.html with full search UI**

```html
{% extends "base.html" %}
{% block content %}
<div class="search-page">
  <h1>{{ "Search a neighbourhood or district" if lang == "en" else "Zoek een buurt of wijk" }}</h1>
  <p class="subtitle">624 Amsterdam · 132 Haarlem · 121 Utrecht</p>

  <form id="search-form"
        hx-get="/search"
        hx-trigger="input changed delay:200ms from:#q, change from:.filter-chip"
        hx-target="#results"
        hx-include="#search-form">

    <input id="q" name="q" type="search" autocomplete="off"
           placeholder="{{ 'Search areas…' if lang == 'en' else 'Zoek gebieden…' }}"
           class="search-input">

    <div class="chips">
      <span class="chip-label">
        {{ "Municipality" if lang == "en" else "Gemeente" }}:
      </span>
      {% for val, label in [("", "Alle" if lang == "nl" else "All"),
                            ("amsterdam", "Amsterdam"),
                            ("haarlem", "Haarlem"),
                            ("utrecht", "Utrecht")] %}
      <label class="chip">
        <input class="filter-chip" type="radio" name="municipality"
               value="{{ val }}" {% if loop.first %}checked{% endif %}>
        {{ label }}
      </label>
      {% endfor %}
    </div>

    <div class="chips">
      <span class="chip-label">{{ "Type" }}:</span>
      {% for val, label_nl, label_en in [("", "Alle", "All"),
                                         ("wijk", "Wijk", "District"),
                                         ("buurt", "Buurt", "Neighbourhood")] %}
      <label class="chip">
        <input class="filter-chip" type="radio" name="type"
               value="{{ val }}" {% if loop.first %}checked{% endif %}>
        {{ label_en if lang == "en" else label_nl }}
      </label>
      {% endfor %}
    </div>
  </form>

  <div id="results"></div>
</div>
{% endblock %}
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/ui/test_routes.py -v
```

Expected: all tests PASS.

- [ ] **Step 7: Commit**

```bash
git add ui/main.py ui/templates/index.html ui/templates/partials/search_results.html tests/ui/test_routes.py
git commit -m "feat: add search page and /search HTMX route"
```

---

## Task 8: Area detail page (GET /area/{slug})

**Files:**
- Modify: `ui/main.py`
- Create: `ui/templates/area.html`
- Modify: `tests/ui/test_routes.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/ui/test_routes.py`:

```python
def test_area_page_returns_200(client):
    resp = client.get("/area/oud-west-amsterdam")
    assert resp.status_code == 200
    assert "Oud-West" in resp.text


def test_area_page_shows_summary_cards(client):
    resp = client.get("/area/oud-west-amsterdam")
    assert "25000" in resp.text   # Inwoners value
    assert "35000" in resp.text   # inkomen value


def test_area_page_shows_type_badge(client):
    resp = client.get("/area/oud-west-amsterdam")
    assert "wijk" in resp.text


def test_area_page_shows_hierarchy_for_wijk(client):
    resp = client.get("/area/oud-west-amsterdam")
    assert "de-pijp-amsterdam" in resp.text


def test_area_page_shows_hierarchy_for_buurt(client):
    resp = client.get("/area/de-pijp-amsterdam")
    assert "oud-west-amsterdam" in resp.text  # link to parent wijk


def test_area_page_404_for_missing_slug(client):
    resp = client.get("/area/does-not-exist")
    assert resp.status_code == 404


def test_area_page_english(client):
    client.post("/set-lang", data={"lang": "en"})
    resp = client.get("/area/de-pijp-amsterdam")
    assert "Residents" in resp.text  # translated summary card label
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/ui/test_routes.py::test_area_page_returns_200 -v
```

Expected: 404 — `/area/{slug}` route not defined.

- [ ] **Step 3: Add /area/{slug} route to ui/main.py**

Append to `ui/main.py`:

```python
_SUMMARY_TOPICS = [
    "Inwoners",
    "Gemiddeld inkomen per inwoner",
    "% Huurwoningen",
    "Misdrijven",
]

_SUMMARY_LABELS = {
    "Inwoners":                      ("Inwoners",      "Residents"),
    "Gemiddeld inkomen per inwoner": ("Gem. inkomen",  "Avg. income"),
    "% Huurwoningen":                ("Huurwoningen",  "Rental homes"),
    "Misdrijven":                    ("Misdrijven",    "Crimes"),
}

_SKIP_UNITS = {"Aantal", "Code", "Naam", "Categorisch type", ""}


@app.get("/area/{slug}", response_class=HTMLResponse)
async def area(request: Request, slug: str, lang: str = Cookie(default="nl")):
    meta = db.get_area_meta(slug)
    if not meta:
        return HTMLResponse("Not found", status_code=404)
    all_stats = db.get_area_stats(slug)
    summary: dict[str, dict] = {}
    for rows in all_stats.values():
        for row in rows:
            if row["topic"] in _SUMMARY_TOPICS:
                summary[row["topic"]] = row
    hierarchy = db.get_area_hierarchy(slug, meta["area_type"])
    return templates.TemplateResponse(
        "area.html",
        {
            "request": request,
            "meta": meta,
            "summary": summary,
            "summary_topics": _SUMMARY_TOPICS,
            "summary_labels": _SUMMARY_LABELS,
            "skip_units": _SKIP_UNITS,
            "stats": all_stats,
            "hierarchy": hierarchy,
            "lang": lang,
        },
    )
```

- [ ] **Step 4: Create ui/templates/area.html**

```html
{% extends "base.html" %}
{% block content %}
<div class="area-page">

  <div class="area-header">
    <h1>{{ meta.area_name }}</h1>
    <div class="area-meta">
      <span class="badge badge-type">{{ translate(meta.area_type, lang) }}</span>
      <span class="badge badge-city">{{ meta.municipality }}</span>
      <a href="/" class="back-link">
        {{ "← Back to search" if lang == "en" else "← Terug naar zoeken" }}
      </a>
    </div>
  </div>

  <div class="summary-cards">
    {% for topic in summary_topics %}
      {% if topic in summary %}
      {% set row = summary[topic] %}
      {% set labels = summary_labels[topic] %}
      <div class="summary-card">
        <div class="card-value">{{ row.value }}</div>
        <div class="card-label">
          {{ labels[1] if lang == "en" else labels[0] }}
        </div>
        {% if row.unit and row.unit not in skip_units %}
        <div class="card-unit">{{ row.unit }}</div>
        {% endif %}
      </div>
      {% endif %}
    {% endfor %}
  </div>

  <input type="search" name="q"
         placeholder="{{ 'Search statistics…' if lang == 'en' else 'Zoek statistieken…' }}"
         class="stats-search"
         hx-get="/area/{{ meta.area_slug }}/stats"
         hx-trigger="input changed delay:200ms"
         hx-target="#stats-body"
         hx-include="[name='q']">

  <div id="stats-body">
    {% set q = "" %}
    {% include "partials/stats_body.html" %}
  </div>

  {% if hierarchy %}
  <div class="hierarchy">
    {% if hierarchy.parent_wijk is defined %}
    <div class="hierarchy-section">
      <h3>{{ "Parent district" if lang == "en" else "Bovenliggende wijk" }}</h3>
      <a href="/area/{{ hierarchy.parent_wijk.wijk_slug }}" class="hierarchy-link">
        {{ hierarchy.parent_wijk.wijk_name }}
      </a>
    </div>
    {% endif %}
    {% if hierarchy.siblings is defined and hierarchy.siblings %}
    <div class="hierarchy-section">
      <h3>
        {{ "Other neighbourhoods in this district" if lang == "en"
           else "Andere buurten in deze wijk" }}
      </h3>
      <ul class="hierarchy-list">
        {% for s in hierarchy.siblings %}
        <li><a href="/area/{{ s.buurt_slug }}">{{ s.buurt_name }}</a></li>
        {% endfor %}
      </ul>
    </div>
    {% endif %}
    {% if hierarchy.buurten is defined and hierarchy.buurten %}
    <div class="hierarchy-section">
      <h3>{{ "Neighbourhoods" if lang == "en" else "Buurten" }}</h3>
      <ul class="hierarchy-list">
        {% for b in hierarchy.buurten %}
        <li><a href="/area/{{ b.buurt_slug }}">{{ b.buurt_name }}</a></li>
        {% endfor %}
      </ul>
    </div>
    {% endif %}
  </div>
  {% endif %}

</div>
{% endblock %}
```

- [ ] **Step 5: Create ui/templates/partials/stats_body.html (stub for now)**

```html
<p class="stats-placeholder">
  {{ "Loading statistics…" if lang == "en" else "Statistieken laden…" }}
</p>
```

- [ ] **Step 6: Run tests**

```bash
uv run pytest tests/ui/test_routes.py -v
```

Expected: all tests PASS (stats_body stub is enough for area page tests).

- [ ] **Step 7: Commit**

```bash
git add ui/main.py ui/templates/area.html ui/templates/partials/stats_body.html tests/ui/test_routes.py
git commit -m "feat: add area detail page"
```

---

## Task 9: Stats HTMX partial (GET /area/{slug}/stats)

**Files:**
- Modify: `ui/main.py`
- Modify: `ui/templates/partials/stats_body.html`
- Modify: `tests/ui/test_routes.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/ui/test_routes.py`:

```python
def test_stats_partial_returns_fragment(client):
    resp = client.get("/area/oud-west-amsterdam/stats")
    assert resp.status_code == 200
    assert "<!DOCTYPE" not in resp.text


def test_stats_browse_mode_uses_details(client):
    resp = client.get("/area/oud-west-amsterdam/stats?q=")
    assert "<details" in resp.text
    assert "Bevolking" in resp.text


def test_stats_search_mode_returns_flat_table(client):
    resp = client.get("/area/oud-west-amsterdam/stats?q=inkomen")
    assert "<details" not in resp.text
    assert "Gemiddeld inkomen per inwoner" in resp.text


def test_stats_search_no_results(client):
    resp = client.get("/area/oud-west-amsterdam/stats?q=xyznonexistent")
    assert resp.status_code == 200
    assert "details" not in resp.text


def test_stats_english_translates_topics(client):
    client.post("/set-lang", data={"lang": "en"})
    resp = client.get("/area/oud-west-amsterdam/stats")
    assert "Demographics" in resp.text  # translated category name
    assert "Residents" in resp.text     # translated topic
```

- [ ] **Step 2: Run to verify failure**

```bash
uv run pytest tests/ui/test_routes.py::test_stats_partial_returns_fragment -v
```

Expected: 404 — `/area/{slug}/stats` route not defined.

- [ ] **Step 3: Add /area/{slug}/stats route to ui/main.py**

Append to `ui/main.py`:

```python
@app.get("/area/{slug}/stats", response_class=HTMLResponse)
async def area_stats(
    request: Request,
    slug: str,
    q: str = "",
    lang: str = Cookie(default="nl"),
):
    stats = db.get_area_stats(slug, q)
    return templates.TemplateResponse(
        "partials/stats_body.html",
        {"request": request, "stats": stats, "q": q, "lang": lang},
    )
```

- [ ] **Step 4: Replace ui/templates/partials/stats_body.html with full implementation**

```html
{% if q %}
  {% if stats %}
  <table class="stats-table">
    <thead>
      <tr>
        <th>{{ "Category" if lang == "en" else "Categorie" }}</th>
        <th>{{ "Topic" if lang == "en" else "Onderwerp" }}</th>
        <th>{{ "Value" if lang == "en" else "Waarde" }}</th>
        <th>{{ "Unit" if lang == "en" else "Eenheid" }}</th>
        <th>{{ "Year" if lang == "en" else "Jaar" }}</th>
      </tr>
    </thead>
    <tbody>
      {% for cat, rows in stats.items() %}
        {% for row in rows %}
        <tr>
          <td class="cell-category">{{ translate(row.category, lang) }}</td>
          <td>{{ translate(row.topic, lang) }}</td>
          <td class="cell-value">{{ row.value }}</td>
          <td class="cell-unit">{{ row.unit }}</td>
          <td class="cell-year">{{ row.year }}</td>
        </tr>
        {% endfor %}
      {% endfor %}
    </tbody>
  </table>
  {% else %}
  <p class="no-results">
    {{ "No matching statistics." if lang == "en" else "Geen overeenkomende statistieken." }}
  </p>
  {% endif %}
{% else %}
  {% for cat, rows in stats.items() %}
  <details class="category-group">
    <summary class="category-header">
      <span>{{ translate(cat, lang) }}</span>
      <span class="category-count">{{ rows | length }}</span>
    </summary>
    <table class="stats-table">
      <thead>
        <tr>
          <th>{{ "Topic" if lang == "en" else "Onderwerp" }}</th>
          <th>{{ "Value" if lang == "en" else "Waarde" }}</th>
          <th>{{ "Unit" if lang == "en" else "Eenheid" }}</th>
          <th>{{ "Year" if lang == "en" else "Jaar" }}</th>
        </tr>
      </thead>
      <tbody>
        {% for row in rows %}
        <tr>
          <td>{{ translate(row.topic, lang) }}</td>
          <td class="cell-value">{{ row.value }}</td>
          <td class="cell-unit">{{ row.unit }}</td>
          <td class="cell-year">{{ row.year }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </details>
  {% endfor %}
{% endif %}
```

- [ ] **Step 5: Run all tests**

```bash
uv run pytest tests/ui/ -v
```

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add ui/main.py ui/templates/partials/stats_body.html tests/ui/test_routes.py
git commit -m "feat: add stats HTMX partial with browse and search modes"
```

---

## Task 10: CSS

**Files:**
- Modify: `ui/static/style.css`

- [ ] **Step 1: Replace stub with full stylesheet**

Replace the contents of `ui/static/style.css`:

```css
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: system-ui, sans-serif;
  font-size: 14px;
  color: #222;
  background: #f7f8fa;
  line-height: 1.5;
}

/* Nav */
.nav {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 52px;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  position: sticky;
  top: 0;
  z-index: 10;
}
.nav-brand {
  font-weight: 700;
  font-size: 16px;
  color: #4f6ef7;
  text-decoration: none;
}
.lang-toggle { display: flex; gap: 4px; }
.lang-btn {
  padding: 4px 10px;
  border: 1px solid #d1d5db;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  color: #555;
}
.lang-btn.active {
  background: #4f6ef7;
  color: #fff;
  border-color: #4f6ef7;
}

/* Layout */
.container { max-width: 900px; margin: 0 auto; padding: 32px 20px; }

/* Search page */
.search-page h1 { font-size: 24px; font-weight: 700; margin-bottom: 4px; }
.subtitle { color: #6b7280; font-size: 13px; margin-bottom: 20px; }

.search-input {
  width: 100%;
  padding: 10px 14px;
  font-size: 15px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  outline: none;
  margin-bottom: 12px;
}
.search-input:focus { border-color: #4f6ef7; box-shadow: 0 0 0 3px #e8eeff; }

.chips { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
.chip-label { font-size: 12px; color: #6b7280; }
.chip { display: flex; align-items: center; gap: 4px; cursor: pointer; }
.chip input[type=radio] { display: none; }
.chip span, .chip {
  padding: 3px 10px;
  border: 1px solid #d1d5db;
  border-radius: 12px;
  font-size: 12px;
  color: #374151;
  background: #fff;
  transition: all .1s;
}
.chip:has(input:checked) {
  background: #4f6ef7;
  border-color: #4f6ef7;
  color: #fff;
}

/* Results list */
.results-list { list-style: none; margin-top: 16px; }
.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  margin-bottom: 6px;
  text-decoration: none;
  color: inherit;
  transition: border-color .1s;
}
.result-item:hover { border-color: #4f6ef7; }
.result-name { font-weight: 500; }
.result-badges { display: flex; gap: 6px; }
.no-results { color: #6b7280; margin-top: 16px; }

/* Badges */
.badge {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 500;
}
.badge-type { background: #e8eeff; color: #4f6ef7; }
.badge-city { background: #f3f4f6; color: #6b7280; }

/* Area page */
.area-page { }
.area-header { margin-bottom: 20px; }
.area-header h1 { font-size: 26px; font-weight: 700; margin-bottom: 6px; }
.area-meta { display: flex; align-items: center; gap: 8px; }
.back-link { font-size: 12px; color: #6b7280; text-decoration: none; margin-left: 8px; }
.back-link:hover { color: #4f6ef7; }

/* Summary cards */
.summary-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.summary-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 14px 16px;
  text-align: center;
}
.card-value { font-size: 22px; font-weight: 700; color: #4f6ef7; }
.card-label { font-size: 11px; color: #6b7280; margin-top: 2px; }
.card-unit { font-size: 10px; color: #9ca3af; }

/* Stats search */
.stats-search {
  width: 100%;
  padding: 9px 14px;
  font-size: 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  outline: none;
  margin-bottom: 16px;
}
.stats-search:focus { border-color: #4f6ef7; box-shadow: 0 0 0 3px #e8eeff; }

/* Category groups */
.category-group {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  margin-bottom: 8px;
  overflow: hidden;
}
.category-group summary.category-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  cursor: pointer;
  font-weight: 600;
  user-select: none;
  border-left: 3px solid #4f6ef7;
  list-style: none;
}
.category-group summary.category-header::-webkit-details-marker { display: none; }
.category-count {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 400;
}

/* Stats table */
.stats-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.stats-table th {
  text-align: left;
  padding: 6px 10px;
  background: #f9fafb;
  color: #6b7280;
  font-weight: 500;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: .04em;
  border-bottom: 1px solid #e5e7eb;
}
.stats-table td { padding: 6px 10px; border-bottom: 1px solid #f3f4f6; }
.stats-table tr:last-child td { border-bottom: none; }
.stats-table tr:nth-child(even) td { background: #fafafa; }
.cell-value { text-align: right; font-variant-numeric: tabular-nums; }
.cell-unit, .cell-year, .cell-category { color: #9ca3af; white-space: nowrap; }

/* Hierarchy */
.hierarchy {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid #e5e7eb;
}
.hierarchy-section { margin-bottom: 20px; }
.hierarchy-section h3 { font-size: 13px; font-weight: 600; color: #6b7280; margin-bottom: 8px; text-transform: uppercase; letter-spacing: .05em; }
.hierarchy-link {
  display: inline-block;
  padding: 6px 12px;
  background: #e8eeff;
  color: #4f6ef7;
  border-radius: 6px;
  text-decoration: none;
  font-weight: 500;
  font-size: 13px;
}
.hierarchy-list { list-style: none; display: flex; flex-wrap: wrap; gap: 6px; }
.hierarchy-list a {
  padding: 4px 10px;
  background: #f3f4f6;
  border-radius: 4px;
  text-decoration: none;
  color: #374151;
  font-size: 12px;
}
.hierarchy-list a:hover { background: #e8eeff; color: #4f6ef7; }
```

- [ ] **Step 2: Smoke-test visually**

```bash
uv run fastapi dev ui/main.py
```

Open http://localhost:8000. Verify:
- Nav with NL/EN toggle renders correctly
- Home page shows search input and filter chips
- Typing in search box shows results via HTMX
- Clicking a result navigates to area detail
- Summary cards display values
- Category `<details>` collapse/expand
- Typing in stats search switches to flat table
- Hierarchy panel shows parent/siblings/children links
- Toggling EN translates category names and topic names

- [ ] **Step 3: Run full test suite**

```bash
uv run pytest tests/ui/ -v
```

Expected: all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add ui/static/style.css
git commit -m "feat: add full stylesheet"
```

---

## Self-Review

**Spec coverage check:**
- ✅ GET / — search page with omnisearch + filter chips (Task 7)
- ✅ GET /search — HTMX partial (Task 7)
- ✅ GET /area/{slug} — detail page with summary cards + hierarchy (Task 8)
- ✅ GET /area/{slug}/stats — browse + search modes (Task 9)
- ✅ POST /set-lang — cookie-based language toggle (Task 6)
- ✅ NL/EN translation via `translate()` in templates (Tasks 2, 9)
- ✅ Collapsible `<details>` categories (Task 9)
- ✅ Flat table in search mode (Task 9)
- ✅ Hierarchy panel: buurt→wijk, wijk→buurten (Task 8)
- ✅ HTMX CDN, no custom JS (base.html, Task 6)
- ✅ Summary cards: Inwoners, Gemiddeld inkomen per inwoner, % Huurwoningen, Misdrijven (Task 8)
- ✅ DB path: `allecijfers/data/allecijfers.db` (Task 2)
- ✅ Translations path: `allecijfers/data/translations.csv` (Task 2)

**Type consistency check:**
- `translate(term, lang)` — used consistently in templates and registered in `templates.env.globals`
- `get_area_stats` returns `dict[str, list[dict]]` — consumed correctly in routes and `stats_body.html`
- `get_area_hierarchy` returns `dict` with keys `parent_wijk`, `siblings`, `buurten` — template checks `is defined` before accessing

**Placeholder scan:** None found.
