from __future__ import annotations

from typing import Any, Callable
import asyncio
import logging
import os

from fasthtml import common as fh  # type: ignore
from starlette.requests import Request
import httpx

from spellbook import thoughtspot

log = logging.getLogger(__name__)


def is_authorized(fn) -> Callable[[...], fh.RedirectResponse | Any]:
    """Check if the user is authorized to access the page."""
    async def wrapper(request: Request):
        if "DEV" in os.environ:
            from dotenv import load_dotenv

            load_dotenv()

            try:
                site = os.environ["HOST"]
                user = os.environ["USER"]
                hush = os.environ["PASS"]
                await do_authorization(request, url=site, user=user, secret=hush)
            except KeyError as e:
                log.error(f"Environment variable not found: {e}")
                is_user_authorized = False
            except httpx.HTTPStatusError:
                is_user_authorized = False
            else:
                is_user_authorized = True
        else:
            is_user_authorized = getattr(request.state.lifetime, "api_session", False)

        if not is_user_authorized:
            return fh.RedirectResponse("/login", status_code=303)

        return await fn(request)
    return wrapper


async def do_authorization(request: Request, *, url: str, user: str, secret: str) -> None:
    """Perform the authorization check."""
    api = thoughtspot.ThoughtSpotAPIClient(base_url=url, username=user, secret_key=secret)
    r = await api.login()

    try:
        r.raise_for_status()
    except httpx.HTTPStatusError:
        log.warning(
            f"Authentication for {user=} with {secret=} failed."
            f"\nTS API Response: HTTP {r.status_code}\n{r.text}"
        )
        request.state.toast.error(request, message=f"Authentication for {user=} with {secret=} failed.")
        raise

    request.state.lifetime.api_session = api
    request.state.lifetime.api_keep_alive = asyncio.create_task(api.is_active_check())
    request.state.lifetime.current_page = "/"

    async def background_toaster():
        import datetime as dt

        NOW = dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(days=1)

        async for r in api.collect_security_logs(since=NOW):
            for d in r.json():
                # log.info(d)
                pass

    # request.state.lifetime.security_logger = asyncio.create_task(background_toaster())
