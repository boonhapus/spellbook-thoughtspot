from __future__ import annotations

from fasthtml import common as fh

from spellbook.spells.base import Spell


class UserManager(Spell):
    """ """
    ui_key: str = "/admin:ROUTE_CHANGE"

    async def invoke(self) -> None:
        ...

    def __ft__(self) -> fh.FT:
        """Renderable for the spell."""
        ...