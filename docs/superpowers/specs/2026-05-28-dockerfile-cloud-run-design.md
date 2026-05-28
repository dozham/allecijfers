# Dockerfile — Cloud Run Deployment

**Date:** 2026-05-28

## Goal

Deploy the `ui/` FastAPI app as a read-only neighborhood-statistics viewer on Cloud Run. The SQLite database is baked into the image at build time. No scraping functionality is included.

## Decisions

| Decision | Choice | Reason |
|---|---|---|
| DB strategy | Bake into image | No extra GCP infra; data is stable and updated by redeploying |
| Crawl endpoint | Remove | DB is read-only; crawled data wouldn't persist across restarts |
| Dependencies | UI-only (`fastapi[standard]`, `jinja2`, `httpx`) | Scrapy/Twisted stack is ~200MB; not needed in the viewer |
| Build style | Single-stage `python:3.13-slim` | Multi-stage complexity not warranted for this project size |

## Dockerfile

Location: `Dockerfile` (project root)

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

CMD ["sh", "-c", "uvicorn ui.main:app --host 0.0.0.0 --port $PORT"]
```

**DB path note:** `ui/db.py` resolves the DB as `Path(__file__).parent.parent / "allecijfers" / "data" / "allecijfers.db"`, which maps to `/app/allecijfers/data/allecijfers.db` inside the container — matching the COPY destination above.

**PORT note:** Cloud Run injects a `$PORT` environment variable at runtime (typically 8080). The CMD reads it via shell form so uvicorn binds to the correct port.

## Source change — `ui/main.py`

Remove the following (none are used by the viewer routes):

- `import asyncio`
- `import re`
- `_background_tasks: set = set()`
- `_PROJECT_ROOT = _HERE.parent` (only used by crawl)
- `async def _launch_crawl(...)` function
- `@app.post("/crawl/start", ...)` endpoint

## `.dockerignore`

Location: `.dockerignore` (project root)

Excludes from build context:

- `.venv/`
- `**/__pycache__/`
- `uv.lock`, `pyproject.toml`
- `tests/`
- `allecijfers/allecijfers/` (scrapy project source)
- `allecijfers/scrapy.cfg`
- `scrape_hierarchy.py`
- `docs/`
- `.claude/`, `.pytest_cache/`

## Out of scope

- Authentication / access control on the Cloud Run service
- CI/CD pipeline for automated rebuilds when data changes
- Migrating the database to Cloud SQL or Firestore
