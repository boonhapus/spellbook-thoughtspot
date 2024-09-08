from __future__ import annotations

from typing import AsyncIterator, TypedDict
import contextlib
import logging
import os
import pathlib

from fasthtml import common as fh  # type: ignore
from starlette.requests import Request
import uvicorn

from spellbook import _utils, auth, components, const, types
from spellbook.components import thoughtspot_sdk
from spellbook.components.shadcn import shadcn
from spellbook.components.toaster import Toaster
from spellbook.routes import login
from spellbook.spellbook import Spellbook

log = logging.getLogger(__name__)


class AppLifespanState(TypedDict):
    """Global namespace for the app."""
    lifetime: _utils.State
    toast: Toaster


MageAsHelper = fh.Div(
    components.Mage(
        hx_trigger="has-available-spell from:body",
        hx_on__trigger="htmx.toggleClass(htmx.find('#mage'), 'mage-glow');",
        cls="w-12 opacity-70 absolute -bottom-5 -right-5",
    ),
    # So, this works.. but it requires you to have the dialog on the page already? (So we can swap it).
    hx_trigger="click", hx_get="/read-spells", hx_target="#active_spellbook", hx_swap="outerHTML",
)


@contextlib.asynccontextmanager
async def lifespan(app: fh.FastHTML) -> AsyncIterator[AppLifespanState]:
    # STARTUP
    lifetime = _utils.State()
    lifetime.spellbook = Spellbook()

    yield {
        "lifetime": lifetime,
        "toast": Toaster.__setup_fh__(app=app),
    }

    # TEARDOWN


app = fh.FastHTML(
    # htmlkw={"data-theme": "spellbook"},
    hdrs=(
        # fh.Script(src=const.HTMX_SSE),
        fh.Script(src=const.THOUGHTSPOT_SDK),
        shadcn.ShadHead(tw_link=True),
        fh.Link(href="/static/minified.css", rel="stylesheet", type="text/css"),
        fh.Link(href="/static/style.css", rel="stylesheet", type="text/css"),
    ),
    lifespan=lifespan,
    # secret_key=os.environ.get("SECRET_KEY", "default-secret-key"),
    routes=[
        *login.routes,
    ],
)


@app.get("/favicon.ico")
async def _() -> fh.FileResponse:
    return fh.FileResponse(const.DIR_STATIC.joinpath("favicon.ico").as_posix())


@app.get("/static/{file:path}")
async def static_files(file: pathlib.Path) -> fh.FileResponse:
    fp = const.DIR_STATIC.joinpath(file)
    log.info(f"File '/static/{file}' was requested, exists={fp.exists()}")
    return fh.FileResponse(fp.as_posix())


@app.get("/")
@auth.is_authorized
async def _(request: Request) -> types.PageRenderableFull:
    """Homepage."""
    lifetime = request.state.lifetime
    init = thoughtspot_sdk.Init(thoughtspot_host=str(lifetime.api_session.base_url), authentication="passthru")
    full = thoughtspot_sdk.FullAppEmbed(div_id="embed-container")

    page = fh.Body(
        fh.Div(
            full,
            MageAsHelper,
            id="embed-container", cls="h-[90vh] ml-16 mt-16 mr-16 relative skeleton",
        ),
        shadcn.Dialog(id="active_spellbook", standard=True),
    )

    request.state.toast.warning(request, message="5 new Security Events!")
    return fh.Title("Spellbook"), init, page


@app.post("/toaster")
async def _(request: Request):
    """Test the Toaster."""
    log.info(f"<< {request=}")
    request.state.toast.warning(request, message="5 new Security Events!")
    return fh.Response(None, status_code=200)


@app.post("/is-spellbook-enabled-for")
async def _(request: Request) -> fh.HttpHeader:
    """Check whether or not any Spells are available."""
    lifetime = request.state.lifetime
    data = await request.json()

    if data.get("type", None) == "ROUTE_CHANGE":
        lifetime.current_page = data["data"]["currentPath"]
        log.info(f"Route Changed: {lifetime.current_page}")

    lifetime.active_spells = spells = await request.state.lifetime.spellbook.lookup_spells(request)
    log.info(f"Spells: {spells}")

    return fh.HttpHeader("hx-trigger", "has-available-spell") if spells else fh.HttpHeader()
    # return fh.Response(None, status_code=200, headers={"hx-trigger": "has-available-spell"} if spells else None)


@app.get("/read-spells")
async def _(request: Request):
    """Check whether or not any Spells are available."""
    # Gather our spells..
    import random
    children = [fh.Div(fh.H3("Hello, world!")) for _ in range(random.randint(1, 10))]
    # ../

    request.state.toast.warning(request, message="Hello, world!")

    component = shadcn.Dialog(
        *children,
        title="Active Spells",
        description="Click on a spell to learn more about it.",
        state="open",
        id="active_spellbook", 
    )

    # Overide the component's style so we can ensure it's shown.
    component.style = "display: flex;"

    return component


if __name__ == "__main__":
    from spellbook import _logging

    os.environ["DEV"] = "true"

    uvicorn.run("spellbook.__main__:app", port=5002, reload=True, log_config=_logging.CONFIG)
