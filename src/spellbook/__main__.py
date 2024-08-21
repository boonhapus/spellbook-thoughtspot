from __future__ import annotations

from typing import AsyncIterator, Callable, TypedDict
import asyncio
import contextlib
import logging
import os

from fasthtml import common as fh
from starlette.requests import Request
from starlette.responses import StreamingResponse
import httpx
import uvicorn

from spellbook import _utils, components, const, thoughtspot
from spellbook.components import AuthenticationForm, thoughtspot_sdk
from spellbook.components.utils import add_sse, update_classes
from spellbook.spellbook import Spellbook

log = logging.getLogger(__name__)

MageAsHelper = update_classes(
    components.Mage,
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


async def do_authorization(request, url: str, user: str, secret: str):
    """Perform the authorization check."""
    api = thoughtspot.ThoughtSpotAPIClient(base_url=url, username=user, secret_key=secret)
    r = await api.login()
    r.raise_for_status()

    request.state.lifetime.api_session = api
    request.state.lifetime.api_keep_alive = asyncio.create_task(api.is_active_check())
    request.state.lifetime.current_page = "/"


@contextlib.asynccontextmanager
async def lifespan(app: fh.FastHTML) -> AsyncIterator[TypedDict]:
    # STARTUP
    lifetime = _utils.State()
    lifetime.message_queue = asyncio.Queue()
    lifetime.spellbook = Spellbook()

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
    init = thoughtspot_sdk.Init(thoughtspot_host=str(request.state.lifetime.api_session.base_url))
    full = thoughtspot_sdk.FullAppEmbed(div_id="embed-container")

    page = fh.Body(
        fh.Div(
            full,
            fh.Button(MageAsHelper, hx_on__click="alert('mage-glow!');"),
            id="embed-container", cls="h-[90vh] ml-16 mt-16 mr-16 relative skeleton",
        ),
    )

    return fh.Title("Spellbook"), init, page


@app.post("/mirror-embed-event")
async def _(request: Request) -> None:
    """ """
    data = await request.json()

    if data.get("type", None) == "ROUTE_CHANGE":
        request.state.lifetime.current_page = data["data"]["currentPath"]
        log.info(f"Route Changed: {request.state.lifetime.current_page}")
        return fh.Response(None, status_code=200, headers={"hx-trigger": "toggle-mage"})

    spells = await request.state.lifetime.spellbook.lookup_spells(request)
    log.info(f"Spells: {spells}")

    # Send an update to the frontend to glow the Mage.
    # component = update_classes(MageAsHelper(hx_swap_oob="true"), "mage-glow", method="ADD" if spells else "REMOVE")
    # await request.state.lifetime.message_queue.put(("mage", fh.to_xml(component)))

    return fh.Response(None)


# @app.get("/process-event")
# async def send_sse_message(request: Request):
#     """Hook up ThoughtSpot events to HTMX."""
#     async def generate():
#         try:
#             while True:
#                 event, data = await request.state.lifetime.message_queue.get()
#                 # log.info(f"Sending event '{event}'\n{data}\n\n")
#                 yield f"event: {event}\ndata: {data}\n\n"
        
#         except Exception as e:
#             # log.info("Sending event 'close'\n\n")
#             yield "event: close\ndata: \n\n"

#     log.info(f"Connecting SSE: {request}")
#     return StreamingResponse(generate(), media_type="text/event-stream")


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
        await do_authorization(request, url=data["host"], user=data["user"], secret=data["pass"])
    
    except httpx.HTTPStatusError as e:
        log.error(f"Auth failed: {e}")
        return AuthenticationForm

    else:
        return fh.Response(None, headers={"hx-redirect": "/"})


if __name__ == "__main__":
    from spellbook import _logging

    os.environ["DEV"] = "true"

    uvicorn.run("spellbook.__main__:app", port=5002, reload=True, log_config=_logging.CONFIG)
