from __future__ import annotations

from fasthtml import common as fh
import pydantic


class Spell(pydantic.BaseModel):
    """Some additional magic that can be done to augment ThoughtSpot."""
    ui_key: str

    def __ft__(self) -> fh.FT:
        """Renderable for the spell."""
        ...

    async def invoke(self) -> None:
        ...
