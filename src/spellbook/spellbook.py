from __future__ import annotations

import logging

from starlette.requests import Request

from spellbook import spells
from spellbook.spells.user.bulk_manager import UserManager

log = logging.getLogger(__name__)


class Spellbook:

    def __init__(self):
        self.spells: list[spells.Base.Spell] = [
            UserManager(),
        ]

    async def lookup_spells(self, request: Request) -> list[spells.base.Spell]:
        """ """
        spells: list[spells.base.Spell] = []

        data = await request.json()

        path = request.state.lifetime.current_page
        type = data.get("type", "*")  # noqa: A001

        log.info(f"Spell Unique Key: {path}:{type}")

        for spell in self.spells:
            if spell.ui_key == f"{path}:{type}":
                spells.append(spell)

        return spells
