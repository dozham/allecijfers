# Crawl Modal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "+" button to the index page municipality filter row that opens a modal where the user can type a municipality name and trigger a background Scrapy crawl + hierarchy scrape.

**Architecture:** One new `POST /crawl/start` FastAPI endpoint in `ui/main.py` validates the input, spawns a shell command (`scrapy crawl … && python scrape_hierarchy.py`) as a fire-and-forget `asyncio.create_task`, and returns an HTMX HTML partial. The modal lives entirely in `ui/templates/index.html` as a DaisyUI `<dialog>` triggered by a `+` button at the end of the municipality filter row.

**Tech Stack:** FastAPI, asyncio, Jinja2, DaisyUI, HTMX, pytest + httpx TestClient

---

## File Map

| File | Change |
|------|--------|
| `ui/main.py` | Add `import asyncio`, `import re`, `_PROJECT_ROOT`, `_launch_crawl()`, `POST /crawl/start` |
| `ui/templates/index.html` | Add `+` button + `<dialog id="crawl-modal">` at end of content block |
| `tests/ui/test_routes.py` | Add 5 new test functions for the endpoint and modal presence |

---

## Task 1: Backend endpoint

**Files:**
- Modify: `ui/main.py`
- Test: `tests/ui/test_routes.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/ui/test_routes.py`:

```python
from unittest.mock import AsyncMock


def test_crawl_start_valid_municipality(client, monkeypatch):
    monkeypatch.setattr("ui.main._launch_crawl", AsyncMock())
    resp = client.post("/crawl/start", data={"municipality": "rotterdam"})
    assert resp.status_code == 200
    assert "rotterdam" in resp.text
    assert "alert-success" in resp.text


def test_crawl_start_normalizes_input(client, monkeypatch):
    monkeypatch.setattr("ui.main._launch_crawl", AsyncMock())
    resp = client.post("/crawl/start", data={"municipality": "  Rotterdam  "})
    assert resp.status_code == 200
    assert "rotterdam" in resp.text
    assert "alert-success" in resp.text


def test_crawl_start_empty_municipality_returns_error(client):
    resp = client.post("/crawl/start", data={"municipality": ""})
    assert resp.status_code == 200
    assert "alert-error" in resp.text


def test_crawl_start_invalid_chars_returns_error(client):
    resp = client.post("/crawl/start", data={"municipality": "den haag!"})
    assert resp.status_code == 200
    assert "alert-error" in resp.text
```

- [ ] **Step 2: Run to verify they fail**

```bash
cd /Users/hossein/src/allecijfers-spider
.venv/bin/python -m pytest tests/ui/test_routes.py::test_crawl_start_valid_municipality tests/ui/test_routes.py::test_crawl_start_normalizes_input tests/ui/test_routes.py::test_crawl_start_empty_municipality_returns_error tests/ui/test_routes.py::test_crawl_start_invalid_chars_returns_error -v
```

Expected: 4 FAILs — `404` or `AttributeError: module 'ui.main' has no attribute '_launch_crawl'`

- [ ] **Step 3: Implement the endpoint**

In `ui/main.py`:

**a)** Add two imports at the top of the file (after the existing `from pathlib import Path` line):
```python
import asyncio
import re
```

**b)** Add `_PROJECT_ROOT` on the line after the existing `_HERE = Path(__file__).parent`:
```python
_PROJECT_ROOT = _HERE.parent
```

**c)** Add `_launch_crawl` and `crawl_start` before `set_lang` at the bottom of the file:

```python
async def _launch_crawl(municipality: str) -> None:
    cmd = (
        f"cd allecijfers && ../.venv/bin/scrapy crawl neighborhood "
        f"-a municipality={municipality} && "
        f"cd .. && .venv/bin/python scrape_hierarchy.py"
    )
    proc = await asyncio.create_subprocess_shell(cmd, cwd=str(_PROJECT_ROOT))
    await proc.wait()


@app.post("/crawl/start", response_class=HTMLResponse)
async def crawl_start(request: Request):
    form = await request.form()
    municipality = str(form.get("municipality", "")).strip().lower()
    if not municipality or not re.fullmatch(r"[a-z0-9-]+", municipality):
        return HTMLResponse('<div class="alert alert-error text-sm">Invalid municipality name.</div>')
    asyncio.create_task(_launch_crawl(municipality))
    return HTMLResponse(
        f'<div class="alert alert-success text-sm">'
        f'Crawl started for <strong>{municipality}</strong>. Runs in the background.'
        f'</div>'
    )
```

- [ ] **Step 4: Run to verify tests pass**

```bash
.venv/bin/python -m pytest tests/ui/test_routes.py::test_crawl_start_valid_municipality tests/ui/test_routes.py::test_crawl_start_normalizes_input tests/ui/test_routes.py::test_crawl_start_empty_municipality_returns_error tests/ui/test_routes.py::test_crawl_start_invalid_chars_returns_error -v
```

Expected: 4 PASSes

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: all existing tests still pass

- [ ] **Step 6: Commit**

```bash
git add ui/main.py tests/ui/test_routes.py
git commit -m "feat: add POST /crawl/start endpoint for background municipality crawl"
```

---

## Task 2: Frontend modal

**Files:**
- Modify: `ui/templates/index.html`
- Test: `tests/ui/test_routes.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/ui/test_routes.py`:

```python
def test_index_has_crawl_modal_trigger(client):
    resp = client.get("/")
    assert "crawl-modal" in resp.text
    assert 'hx-post="/crawl/start"' in resp.text
```

- [ ] **Step 2: Run to verify it fails**

```bash
.venv/bin/python -m pytest tests/ui/test_routes.py::test_index_has_crawl_modal_trigger -v
```

Expected: FAIL — `AssertionError`

- [ ] **Step 3: Add the "+" button and modal to index.html**

In `ui/templates/index.html`, replace the municipality filter div closing tag and everything after it:

Find this closing line of the municipality filter div (line 67):
```html
</div>
```
(the one closing `<div class="flex gap-2 mb-6 overflow-x-auto pb-1 scrollbar-none flex-nowrap">`)

Replace the entire municipality filter block (lines 51–67) with:

```html
{# Municipality filter — horizontally scrollable #}
<div class="flex items-center gap-2 mb-6">
  <div class="flex gap-2 overflow-x-auto pb-1 scrollbar-none flex-nowrap flex-1">
    <input type="radio" id="muni-all" name="municipality" value="" class="sr-only peer/muni-all" checked
      hx-get="/search" hx-trigger="change" hx-target="#results"
      hx-include="[name='q'],[name='municipality'],[name='type']">
    <label for="muni-all" class="btn btn-sm rounded-full btn-outline whitespace-nowrap peer-checked/muni-all:btn-neutral peer-checked/muni-all:border-neutral">
      {% if lang == "en" %}All{% else %}Alle{% endif %}
    </label>

    {% for m in municipalities %}
    <input type="radio" id="muni-{{ m }}" name="municipality" value="{{ m }}" class="sr-only peer/muni-{{ m }}"
      hx-get="/search" hx-trigger="change" hx-target="#results"
      hx-include="[name='q'],[name='municipality'],[name='type']">
    <label for="muni-{{ m }}" class="btn btn-sm rounded-full btn-outline whitespace-nowrap peer-checked/muni-{{ m }}:btn-neutral peer-checked/muni-{{ m }}:border-neutral">
      {{ m | capitalize }}
    </label>
    {% endfor %}
  </div>
  <button onclick="document.getElementById('crawl-modal').showModal()"
    class="btn btn-sm btn-circle btn-ghost flex-shrink-0"
    title="{% if lang == 'en' %}Crawl new municipality{% else %}Nieuwe gemeente crawlen{% endif %}">+</button>
</div>

{# Crawl modal #}
<dialog id="crawl-modal" class="modal">
  <div class="modal-box">
    <h3 class="font-bold text-lg mb-4">
      {% if lang == "en" %}Crawl municipality{% else %}Gemeente crawlen{% endif %}
    </h3>
    <form hx-post="/crawl/start" hx-target="#crawl-result" hx-swap="innerHTML">
      <label class="input input-bordered flex items-center gap-2 rounded-full mb-4 bg-base-100">
        <input type="text" name="municipality" class="grow"
          placeholder="{% if lang == 'en' %}e.g. rotterdam{% else %}bijv. rotterdam{% endif %}">
      </label>
      <button type="submit" class="btn btn-primary btn-sm rounded-full">
        {% if lang == "en" %}Start crawl{% else %}Start crawl{% endif %}
      </button>
    </form>
    <div id="crawl-result" class="mt-4"></div>
  </div>
  <form method="dialog" class="modal-backdrop"><button>close</button></form>
</dialog>
```

- [ ] **Step 4: Run to verify the new test passes**

```bash
.venv/bin/python -m pytest tests/ui/test_routes.py::test_index_has_crawl_modal_trigger -v
```

Expected: PASS

- [ ] **Step 5: Run the full test suite**

```bash
.venv/bin/python -m pytest tests/ -v
```

Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add ui/templates/index.html tests/ui/test_routes.py
git commit -m "feat: add crawl modal to index page"
```
