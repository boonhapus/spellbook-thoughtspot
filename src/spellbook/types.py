from __future__ import annotations

from typing import TypeAlias

from fasthtml import common as fh

PageRenderableFull = tuple[fh.Title, *tuple[fh.Header | fh.Script, ...], fh.Body]
# DOCS: https://docs.fastht.ml/ref/handlers.html
"""
Handler functions can return multiple FT objects as a tuple. The first item is
treated as the Title, and the rest are added to the Body.
"""

PageRenderablePartial: TypeAlias = fh.FT
# DOCS: https://docs.fastht.ml/ref/handlers.html
"""
When a handler function returns a single FT object for an HTMX request, it's
rendered as a single HTML partial.
"""
