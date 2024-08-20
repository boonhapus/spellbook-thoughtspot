from __future__ import annotations

from typing import AsyncIterator, TypedDict
import asyncio
import contextlib
import logging
import os

from fasthtml import common as fh
from starlette.requests import Request
from starlette.responses import StreamingResponse
import uvicorn

from spellbook import _utils, components, const, thoughtspot
from spellbook.components import AuthenticationForm, thoughtspot_sdk
from spellbook.components.utils import add_sse, update_classes

log = logging.getLogger(__name__)

MageAsHelper = update_classes(
    add_sse(components.Mage, connect="/process-event", target="mage", close="close", hx_swap="outerHTML"),
    "w-12", "opacity-70", "absolute", "-bottom-5", "-right-5",
    method="ADD",
)


async def is_user_authenticated(request: Request, session):
    """See if the User is authenticated."""
    is_authenticated = any(
        [
            getattr(request.state.lifetime, "api_session", None),
            session.get("auth", None) is not None,
            request.scope.get("auth", None) is not None,
        ],
    )

    if "DEV" in os.environ and not is_authenticated:
        api = thoughtspot.ThoughtSpotAPIClient(
            base_url="...",
            username="...",
            secret_key="...",
        )

        await api.login()

        request.state.lifetime.api_session = api
        request.state.lifetime.api_keep_alive = asyncio.create_task(api.is_active_check())
        return fh.RedirectResponse("/", status_code=303)

    if not is_authenticated:
        return fh.RedirectResponse("/login", status_code=303)


@contextlib.asynccontextmanager
async def lifespan(app: fh.FastHTML) -> AsyncIterator[TypedDict]:
    # STARTUP
    lifetime = _utils.State()
    lifetime.message_queue = asyncio.Queue()

    yield {"lifetime": lifetime}

    # TEARDOWN
    if "DEV" in os.environ:
        await lifetime.message_queue.put(("close", ""))


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
    before=fh.Beforeware(
        is_user_authenticated,
        skip=[
            r"/static/.*", "/favicon.ico",
            "/login", "/auth", "/mirror-embed-event", "/process-event",
        ],
    ),
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
async def _(request: Request):
    init = thoughtspot_sdk.Init(thoughtspot_host=str(request.state.lifetime.api_session.base_url))
    full = thoughtspot_sdk.FullAppEmbed(div_id="embed-container")

    page = fh.Body(
        fh.Div(
            full,
            MageAsHelper,
            id="embed-container", cls="h-[90vh] ml-16 mt-16 mr-16 relative",
        ),
    )

    return fh.Title("Spellbook"), init, page


class Spellbook:

    def __init__(self):
        self.spells: list[Spell] = []

    async def lookup_spells(self, request: Request) -> list[Spell]:
        """ """
        spells = []
        data = await request.json()
        return spells


class Spell:

    def __init__(self):
        ...


@app.post("/mirror-embed-event")
async def _(request: Request) -> None:
    """ """
    spells = await request.state.lifetime.spellbook.lookup_spells(request)
    component = update_classes(MageAsHelper, "mage-glow", method="ADD" if spells else "REMOVE")
    await request.state.lifetime.message_queue.put(("mage", fh.to_xml(component)))

    # if data["type"] == "ROUTE_CHANGE" and data["data"]["currentPath"] == "/insights/home/monitor-alerts":
    #     log.warning("Monitor Tab visited, CANCELLING ALL SSE LISTENERS !!!")
    #     await request.state.lifetime.message_queue.put(("close", ""))


@app.get("/process-event")
async def send_sse_message(request: Request):
    """Hook up ThoughtSpot events to HTMX."""
    async def generate():
        try:
            while True:
                event, data = await request.state.lifetime.message_queue.get()
                yield f"event: {event}\ndata: {data}\n\n"
        
        finally:
            yield "event: close\ndata: \n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/auth")
async def _(request: Request, session):
    """Authenticate the User to ThoughtSpot and initialize the SDK."""
    data = await request.form()

    # ATTEMPT AUTHENTICATION
    api = thoughtspot.ThoughtSpotAPIClient(base_url=data["site"], username=data["user"], secret_key=data["pass"])

    r = await api.login()

    if r.is_success:
        session["auth"] = True
        request.state.lifetime.api_session = api
        request.state.lifetime.api_keep_alive = asyncio.create_task(api.is_active_check())
        return fh.Response(None, headers={"hx-redirect": "/"})
    else:
        log.error(r.content)
        return AuthenticationForm


@app.get("/login")
async def _(session):
    """ """
    if session.get("auth", None) is not None:
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


if __name__ == "__main__":
    from spellbook import _logging

    os.environ["DEV"] = "true"

    uvicorn.run("spellbook.main:app", port=5002, reload=True, log_config=_logging.CONFIG)
