# Dockerfile — Cloud Run Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Package the `ui/` FastAPI app as a minimal read-only Docker image suitable for Cloud Run, with the SQLite database baked in and all scraping functionality removed.

**Architecture:** Single-stage `python:3.13-slim` image; installs only the three UI packages (`fastapi[standard]`, `jinja2`, `httpx`); copies `ui/` source and the two data files; serves via uvicorn on `$PORT`. Crawl route and its template UI are removed from the source before packaging.

**Tech Stack:** Docker, Python 3.13, FastAPI, uvicorn, Cloud Run (PORT env var)

**Spec:** `docs/superpowers/specs/2026-05-28-dockerfile-cloud-run-design.md`

---

### Task 1: Strip crawl code from `ui/main.py` and its tests

**Files:**
- Modify: `tests/ui/test_routes.py:218-254`
- Modify: `ui/main.py:1-14, 274-297`

- [ ] **Step 1: Remove crawl tests from `tests/ui/test_routes.py`**

  Delete lines 218–254 (the five crawl-related test functions). The file should end after `test_area_page_shows_in_comparison_when_added`:

  ```python
  def test_area_page_shows_in_comparison_when_added(client):
      client.cookies.set("compare", "oud-west-amsterdam")
      resp = client.get("/area/oud-west-amsterdam")
      assert "In vergelijking" in resp.text or "In comparison" in resp.text
  ```

  Remove everything after that (the five functions: `test_crawl_start_valid_municipality`, `test_crawl_start_normalizes_input`, `test_crawl_start_empty_municipality_returns_error`, `test_crawl_start_invalid_chars_returns_error`, `test_index_has_crawl_modal_trigger`).

- [ ] **Step 2: Run tests to confirm remaining tests still pass**

  ```bash
  .venv/bin/pytest tests/ui/ -v
  ```

  Expected: all remaining tests PASS (crawl tests are gone, nothing else changed yet).

- [ ] **Step 3: Remove crawl imports and globals from `ui/main.py`**

  Replace the top of the file (lines 1–14). Remove `import asyncio`, `import re`, `_PROJECT_ROOT`, and `_background_tasks` (all are only used by the crawl code being removed). The new file header:

  ```python
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
  ```

- [ ] **Step 4: Remove `_launch_crawl` and `crawl_start` from `ui/main.py`**

  Delete the following block (currently around lines 274–297):

  ```python
  async def _launch_crawl(municipality: str) -> None:
      cmd = (
          f"cd allecijfers && ../.venv/bin/scrapy crawl neighborhood "
          f"-a municipality={municipality} && "
          f"cd .. && .venv/bin/python scrape_hierarchy.py {municipality}"
      )
      proc = await asyncio.create_subprocess_shell(cmd, cwd=str(_PROJECT_ROOT))
      await proc.wait()


  @app.post("/crawl/start", response_class=HTMLResponse)
  async def crawl_start(request: Request):
      form = await request.form()
      municipality = str(form.get("crawl_municipality", "")).strip().lower()
      if not municipality or not re.fullmatch(r"[a-z0-9-]+", municipality):
          return HTMLResponse('<div class="alert alert-error text-sm">Invalid municipality name.</div>')
      task = asyncio.create_task(_launch_crawl(municipality))
      _background_tasks.add(task)
      task.add_done_callback(_background_tasks.discard)
      return HTMLResponse(
          f'<div class="alert alert-success text-sm">'
          f'Crawl started for <strong>{municipality}</strong>. Runs in the background.'
          f'</div>'
      )
  ```

- [ ] **Step 5: Run tests to confirm everything still passes**

  ```bash
  .venv/bin/pytest tests/ui/ -v
  ```

  Expected: all tests PASS.

- [ ] **Step 6: Commit**

  ```bash
  git add ui/main.py tests/ui/test_routes.py
  git commit -m "feat: remove crawl endpoint for read-only Cloud Run deployment"
  ```

---

### Task 2: Remove crawl modal from `ui/templates/index.html`

**Files:**
- Modify: `ui/templates/index.html:69-93`

- [ ] **Step 1: Remove the "+" button trigger from `index.html`**

  Delete lines 69–73 (the `<button>` that calls `showModal()`):

  ```html
        onclick="document.getElementById('crawl-modal').showModal()"
        class="btn btn-sm btn-circle btn-ghost flex-shrink-0"
        ...
  ```

  The municipality filter `<div>` (lines 51–68) ends with `</div>` after the `{% endfor %}`. Remove the button entirely so the flex container ends at `</div>` after `</div>` of the scrollable inner div.

  The result for that section should be:

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
  </div>
  ```

- [ ] **Step 2: Remove the crawl modal `<dialog>` from `index.html`**

  Delete lines 75–93 (the entire `{# Crawl modal #}` block):

  ```html
  {# Crawl modal #}
  <dialog id="crawl-modal" class="modal">
    ...
  </dialog>
  ```

  Nothing replaces it.

- [ ] **Step 3: Run tests**

  ```bash
  .venv/bin/pytest tests/ui/ -v
  ```

  Expected: all tests PASS.

- [ ] **Step 4: Commit**

  ```bash
  git add ui/templates/index.html
  git commit -m "feat: remove crawl modal from index page"
  ```

---

### Task 3: Create `.dockerignore`

**Files:**
- Create: `.dockerignore`

- [ ] **Step 1: Write `.dockerignore`**

  Create `/Users/hossein/src/allecijfers-spider/.dockerignore`:

  ```
  # Python / dev tooling
  .venv/
  .pytest_cache/
  .python-version
  **/__pycache__/
  *.pyc

  # Package management (not needed — deps installed via pip in Dockerfile)
  uv.lock
  pyproject.toml

  # Scrapy project (not needed for the UI)
  allecijfers/allecijfers/
  allecijfers/scrapy.cfg
  scrape_hierarchy.py

  # Tests and docs
  tests/
  docs/

  # Misc
  .claude/
  README.md
  TODO.md
  CLAUDE.md
  ```

- [ ] **Step 2: Commit**

  ```bash
  git add .dockerignore
  git commit -m "chore: add .dockerignore for Cloud Run image build"
  ```

---

### Task 4: Create `Dockerfile`

**Files:**
- Create: `Dockerfile`

- [ ] **Step 1: Write `Dockerfile`**

  Create `/Users/hossein/src/allecijfers-spider/Dockerfile`:

  ```dockerfile
  FROM python:3.13-slim
  WORKDIR /app

  RUN pip install --no-cache-dir \
      "fastapi[standard]>=0.115" \
      "jinja2>=3.1" \
      "httpx>=0.27"

  COPY ui/ ui/
  COPY allecijfers/data/allecijfers.db allecijfers/data/allecijfers.db
  COPY allecijfers/data/translations.csv allecijfers/data/translations.csv

  ENV PORT=8080
  EXPOSE 8080

  CMD exec uvicorn ui.main:app --host 0.0.0.0 --port "$PORT"
  ```

  **Note on CMD:** `exec` replaces the shell process with uvicorn so SIGTERM from Cloud Run is delivered directly to uvicorn (clean shutdown). `"$PORT"` is expanded by the shell before exec.

- [ ] **Step 2: Build the image**

  ```bash
  docker build -t allecijfers-ui .
  ```

  Expected: build completes without errors. The pip install step should pull `fastapi[standard]`, `jinja2`, `httpx` and their dependencies.

- [ ] **Step 3: Run the container and smoke-test**

  ```bash
  docker run --rm -p 8080:8080 allecijfers-ui
  ```

  In a second terminal:

  ```bash
  curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/
  ```

  Expected: `200`

  ```bash
  curl -s http://localhost:8080/ | grep -c "AlleCijfers"
  ```

  Expected: `1` (or more)

  Stop the container with Ctrl-C.

- [ ] **Step 4: Commit**

  ```bash
  git add Dockerfile
  git commit -m "feat: add Dockerfile for Cloud Run deployment"
  ```
