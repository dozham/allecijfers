# Crawl Modal Design

**Date:** 2026-05-28  
**Status:** Approved

## Overview

Add a "Crawl new municipality" modal to the existing index page. The user enters a municipality slug, submits, and the spider + hierarchy script are launched as a fire-and-forget background process. A confirmation message appears inside the modal.

## Backend

**New endpoint:** `POST /crawl/start`

- Accepts `municipality` form field (string)
- Normalizes input: strips whitespace, lowercases
- Validates: non-empty, only `[a-z0-9-]` characters after normalization
- On valid input: launches the following shell command as a fire-and-forget background task (`asyncio.create_task`):
  ```
  cd allecijfers && ../.venv/bin/scrapy crawl neighborhood -a municipality=<municipality> && cd .. && .venv/bin/python scrape_hierarchy.py
  ```
  via `asyncio.create_subprocess_shell` with `cwd` set to the project root
- Returns HTMX partial HTML swapped into `#crawl-result`:
  - Success: green alert — "Crawl started for `<municipality>`. This runs in the background."
  - Validation error: red alert — "Invalid municipality name."

No state tracking. No DB writes. The endpoint returns immediately after spawning.

## Frontend

**Changes to `index.html`:**

1. Add a small "+" button at the end of the municipality filter row that opens a DaisyUI `<dialog>` modal via `document.getElementById('crawl-modal').showModal()`.
2. The modal contains:
   - A heading: "Crawl municipality" (NL: "Gemeente crawlen")
   - A text input for the municipality slug, with placeholder `e.g. rotterdam`
   - A submit button that triggers `hx-post="/crawl/start"` `hx-target="#crawl-result"` `hx-swap="innerHTML"`
   - A `<div id="crawl-result">` below the form for the confirmation message
3. No page navigation or reload on success.

## Constraints

- The subprocess runs with the project root as its working directory.
- The spider command must be run from the `allecijfers/` subdirectory (where `scrapy.cfg` lives); the hierarchy script from the project root.
- No auth or rate-limiting — this is a local tool.
