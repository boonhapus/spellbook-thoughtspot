from __future__ import annotations

from typing import Any, AsyncIterator, Callable, TypedDict
import asyncio
import contextlib
import logging
import os
import pathlib

from fasthtml import common as fh  # type: ignore
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
import httpx
import uvicorn

from spellbook import _utils, components, const, thoughtspot, types
from spellbook.components import AuthenticationForm, thoughtspot_sdk
from spellbook.components.shadcn import shadcn
from spellbook.components.toaster import Toaster
from spellbook.components.utils import update_classes
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


def check_authorization(fn) -> Callable[[...], fh.RedirectResponse | Any]:
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
)


@app.get("/favicon.ico")
async def _() -> fh.FileResponse:
    return fh.FileResponse(const.DIR_STATIC.joinpath("favicon.ico").as_posix())


@app.get("/static/{file}")
async def static_files(file: pathlib.Path) -> fh.FileResponse:
    fp = const.DIR_STATIC.joinpath(file)
    log.debug(f"File '/static/{file}' was requested, exists={fp.exists()}")
    return fh.FileResponse(fp.as_posix())


@app.get("/")
@check_authorization
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

    request.state.toast.warning(request, message=f"5 new Security Events!")
    return fh.Title("Spellbook"), init, page

#
#
#

@app.post("/toaster")
async def _(request: Request):
    """Test the Toaster."""
    log.info(f"<< {request=}")
    request.state.toast.warning(request, message=f"5 new Security Events!")
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


if __name__ == "__main__":
    from spellbook import _logging

    os.environ["DEV"] = "true"

    uvicorn.run("spellbook.__main__:app", port=5002, reload=True, log_config=_logging.CONFIG)
