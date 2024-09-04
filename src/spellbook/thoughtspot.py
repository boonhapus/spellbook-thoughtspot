from __future__ import annotations

from typing import AsyncIterator
import asyncio
import datetime as dt
import json
import logging

import httpx
import pydantic

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
    
    async def search_users(self, **options) -> httpx.Response:
        """
        READ:
        """
        r = await self.post("api/rest/2.0/users/search", json=options)
        return r

    async def collect_security_logs(
        self,
        *,
        since: pydantic.AwareDatetime,
        until: pydantic.AwareDatetime | None = None,
    ) -> AsyncIterator[httpx.Response]:
        """
        READ: 
        """
        if since.tzinfo != dt.timezone.utc:
            since = since.astimezone(tz=dt.timezone.utc)
        
        if until is None:
            streaming = True
            final = dt.datetime.now(tz=dt.timezone.utc)

        else:
            streaming = False
            final = until if until.tzinfo == dt.timezone.utc else until.astimezone(tz=dt.timezone.utc)

        pending = set()
        until = since + dt.timedelta(days=1)

        # Collect all the past log records
        while until <= final:
            d = {
                "log_type": "SECURITY_AUDIT",
                "start_epoch_time_in_millis": int(since.timestamp() * 1000),
                "end_epoch_time_in_millis": int(until.timestamp() * 1000),
                "get_all_logs": True,
            }
            pending.add(asyncio.create_task(self.post("api/rest/2.0/logs/fetch", json=d)))

            since = until
            until = since + dt.timedelta(days=1)
        
        r = httpx.Response(status_code=httpx.codes.PARTIAL_CONTENT)
        b = []

        try:
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED, timeout=5)

                for task in done:
                    response = task.result()

                    if streaming:
                        yield response

                    elif logs := response.json():
                        b.extend(logs)

                    else:
                        log.warning(f"No content (api/rest/2.0/logs/fetch): HTTP {response.status_code}")
                        log.debug(f"Response content\n{json.dumps(response.__getstate__(), indent=4, default=str)}")

                if streaming and done:
                    lifo_security_logs = sorted(response.json(), key=lambda log: log["date"], reverse=True)

                    if not lifo_security_logs:
                        await asyncio.sleep(5)
                    
                    else:
                        since = dt.datetime.fromisoformat(lifo_security_logs[0]["date"])
                        until = dt.datetime.now(tz=dt.timezone.utc)
                        d["start_epoch_time_in_millis"] = int(since.timestamp() * 1000)
                        d["end_epoch_time_in_millis"] = int(until.timestamp() * 1000)

                    pending.add(asyncio.create_task(self.post("api/rest/2.0/logs/fetch", json=d)))
        
        except asyncio.CancelledError:
            pass

        except Exception:
            log.exception("Something went wrong fetching logs..", exc_info=True)

        if not streaming:
            r.status_code = 200
            r.is_closed = True
            r._content = json.dumps(b).encode()
            yield r
