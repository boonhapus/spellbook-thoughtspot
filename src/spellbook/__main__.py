from __future__ import annotations

from typing import AsyncIterator, Callable, TypedDict
import asyncio
import contextlib
import logging
import os

from fasthtml import common as fh  # type: ignore
from starlette.requests import Request
import httpx
import uvicorn

from spellbook import _utils, components, const, thoughtspot
from spellbook.components import AuthenticationForm, thoughtspot_sdk
from spellbook.components.utils import update_classes
from spellbook.spellbook import Spellbook

log = logging.getLogger(__name__)


class AppLifespanState(TypedDict):
    """Global namespace for the app."""
    lifetime: _utils.State


MageAsHelper = update_classes(
    fh.Div(
        components.Mage(
            hx_trigger="has-available-spell from:body",
            hx_on__trigger="htmx.toggleClass(htmx.find('#mage'), 'mage-glow');",
        ),
        hx_trigger="click", hx_get="/read-spells", hx_target="#active_spellbook", hx_swap="outerHTML",
    ),
    "w-12", "opacity-70", "absolute", "-bottom-5", "-right-5",
    method="ADD",
)


def check_authorization(fn) -> Callable[[...], fh.RedirectResponse | None]:
    """Check if the user is authorized to access the page."""
    async def wrapper(request: Request, *args, **kwargs):
        if "DEV" in os.environ:
            from dotenv import load_dotenv

            load_dotenv()
            await do_authorization(request, url=os.environ["HOST"], user=os.environ["USER"], secret=os.environ["PASS"])
            is_user_authorized = True

        else:
            is_user_authorized = getattr(request.state.lifetime, "api_session", False)

        if not is_user_authorized:
            return fh.RedirectResponse("/login", status_code=303)

        log.info(f"{request=}, {args=}, {kwargs=}")
        # return await fn(request, *args, **kwargs)
        return await fn(request)
    return wrapper


async def do_authorization(request: Request, url: str, user: str, secret: str) -> None:
    """Perform the authorization check."""
    api = thoughtspot.ThoughtSpotAPIClient(base_url=url, username=user, secret_key=secret)
    r = await api.login()
    r.raise_for_status()

    request.state.lifetime.api_session = api
    request.state.lifetime.api_keep_alive = asyncio.create_task(api.is_active_check())
    request.state.lifetime.current_page = "/"


@contextlib.asynccontextmanager
async def lifespan(app: fh.FastHTML) -> AsyncIterator[AppLifespanState]:
    # STARTUP
    lifetime = _utils.State()
    lifetime.spellbook = Spellbook()

    yield {"lifetime": lifetime}

    # TEARDOWN


app = fh.FastHTML(
    htmlkw={"data-theme": "spellbook"},
    hdrs=(
        fh.Script(src=const.HTMX_SSE),
        fh.Script(src=const.THOUGHTSPOT_SDK),
        fh.Script(src=const.TAILWIND_CSS),
        fh.Link(href=const.DAISY_CSS, rel="stylesheet", type="text/css"),
        fh.Link(href="/static/style.css", rel="stylesheet", type="text/css"),
    ),
    lifespan=lifespan,
)


@app.get("/favicon.ico")
async def _() -> fh.FileResponse:
    return fh.FileResponse(const.DIR_STATIC.joinpath("favicon.ico").as_posix())


@app.get("/static/{filename:path}.{ext:static}")
async def static_files(filename: str, ext: str) -> fh.FileResponse:
    fp = const.DIR_STATIC.joinpath(f"{filename}.{ext}")
    log.debug(f"File '/static/{filename}.{ext}' was requested, exists={fp.exists()}")
    return fh.FileResponse(fp.as_posix())


@app.get("/")
@check_authorization
async def _(request: Request):
    """Homepage."""
    host = str(request.state.lifetime.api_session.base_url)
    init = thoughtspot_sdk.Init(thoughtspot_host=host, authentication="passthru")
    full = thoughtspot_sdk.FullAppEmbed(div_id="embed-container")

    page = fh.Body(
        fh.Div(
            full,
            MageAsHelper,
            id="embed-container", cls="h-[90vh] ml-16 mt-16 mr-16 relative skeleton",
        ),
        fh.Dialog(id="active_spellbook", cls="modal"),
    )

    return fh.Title("Spellbook"), init, page


@app.post("/is-spellbook-enabled-for")
async def _(request: Request) -> None:
    """Check whether or not any Spells are available."""
    lifetime = request.state.lifetime
    data = await request.json()

    if data.get("type", None) == "ROUTE_CHANGE":
        lifetime.current_page = data["data"]["currentPath"]
        log.info(f"Route Changed: {lifetime.current_page}")

    lifetime.active_spells = spells = await request.state.lifetime.spellbook.lookup_spells(request)
    log.info(f"Spells: {spells}")

    return fh.Response(None, status_code=200, headers={"hx-trigger": "has-available-spell"} if spells else None)


@app.get("/read-spells")
async def _(request: Request):
    """Check whether or not any Spells are available."""
    modal = fh.Dialog(
        fh.Div(
            fh.H3("Hello!", cls="text-lg font-bold"),
            fh.P("Press ESC key or click outside to close", cls="py-4"),
            cls="modal-box"
        ),
        fh.Form(fh.Button("close"), method="dialog", cls="modal-backdrop"),
        fh.Script("document.getElementById('active_spellbook').showModal();"),
        id="active_spellbook", cls="modal",
    )

    return modal


@app.get("/login")
async def _(request: Request):
    """Login page."""
    if getattr(request.state.lifetime, "api_session", False):
        return fh.RedirectResponse("/", status_code=303)

    page = fh.Body(
        fh.Div(
            update_classes(components.Mage, "w-24", method="ADD"),
            fh.H1("ThoughtSpot Spellbook", cls="text-2xl text-primary"),
            AuthenticationForm,
            cls="h-screen flex flex-col gap-4 items-center justify-center",
        ),
        id="container",
    )
    
    return fh.Title("Spellbook"), page


@app.post("/auth")
async def _(request: Request):
    """Authenticate the User to ThoughtSpot."""
    data = await request.form()

    try:
        await do_authorization(request, url=data["host"], user=data["user"], secret=data["pass"])  # type: ignore[arg-type]
    
    except httpx.HTTPStatusError as e:
        log.error(f"Auth failed: {e}")
        return AuthenticationForm

    else:
        return fh.Response(None, headers={"hx-redirect": "/"})


if __name__ == "__main__":
    from spellbook import _logging

    os.environ["DEV"] = "true"

    uvicorn.run("spellbook.__main__:app", port=5002, reload=True, log_config=_logging.CONFIG)
