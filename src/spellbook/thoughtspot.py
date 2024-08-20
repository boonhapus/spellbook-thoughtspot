from __future__ import annotations

import asyncio
import logging

import httpx

from spellbook.__project__ import __version__

log = logging.getLogger(__name__)
CALLOSUM_DEFAULT_TIMEOUT_SECONDS = 60 * 5


class ThoughtSpotAPIClient(httpx.AsyncClient):
    """A small shim around the ThoughtSpot REST API."""

    def __init__(self, base_url: str, username: str, secret_key: str, **opts):
        if "headers" not in opts:
            opts["headers"] = {}

        opts["headers"]["x-requested-by"] = "ThoughtSpot Spellbook"
        opts["headers"]["user-agent"] = f"Spellbook v{__version__} (+github: thoughtspot/thoughtspot-spellbook)"
        opts["timeout"] = CALLOSUM_DEFAULT_TIMEOUT_SECONDS
        super().__init__(base_url=base_url, **opts)
        self.username = username
        self.secret_key = secret_key

    async def is_active_check(self) -> None:
        """Implement a lightweight check to keep the ThoughtSpot session alive."""
        try:
            while True:
                try:
                    r = await self.get("callosum/v1/session/isactive")
                    r.raise_for_status()
                except httpx.HTTPError as e:
                    log.warning(f"ThoughtSpot api keep-alive failed: {e}, retrying...")

                await asyncio.sleep(60)

        except asyncio.CancelledError:
            pass

    async def login(self) -> httpx.Response:
        """
        READ: https://developers.thoughtspot.com/docs/restV2-playground?apiResourceId=http%2Fapi-endpoints%2Fauthentication%2Flogin
        """
        d = {"username": self.username, "secret_key": self.secret_key, "validity_time_in_sec": 60 * 1000}
        r = await self.post("api/rest/2.0/auth/token/full", json=d)

        if r.is_success:
            self.headers["Authorization"] = f"Bearer {r.json()['token']}"

        return r
