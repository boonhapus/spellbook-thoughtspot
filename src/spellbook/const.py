from __future__ import annotations

import pathlib

PROJECT_ROOT = pathlib.Path(__file__).parent.parent.parent
DIR_STATIC   = PROJECT_ROOT / "static"

TAILWIND_CSS = "https://cdn.tailwindcss.com"

THOUGHTSPOT_SDK = "https://cdn.jsdelivr.net/npm/@thoughtspot/visual-embed-sdk/dist/tsembed.js"
HTMX_SSE = "https://unpkg.com/htmx-ext-sse@2.2.1/sse.js"