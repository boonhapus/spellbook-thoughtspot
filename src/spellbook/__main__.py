from __future__ import annotations

from typing import AsyncIterator, TypedDict
import contextlib
import datetime as dt
import logging
import os
import pathlib

from fasthtml import common as fh
from starlette.requests import Request

from spellbook import _utils, auth, const
from spellbook.components import thoughtspot_sdk
from spellbook.spellbook import Spellbook

log = logging.getLogger(__name__)

FRANKEN_UI_CSS = fh.Link(rel="stylesheet", href="https://unpkg.com/franken-wc@0.1.0/dist/css/zinc.min.css")
TAILWIND   = fh.Script(defer=True, src="https://cdn.tailwindcss.com")


@contextlib.asynccontextmanager
async def lifespan(app: fh.FastHTML) -> AsyncIterator[TypedDict]:
    # STARTUP
    lifetime = _utils.State()
    lifetime.spellbook = Spellbook()

    yield {
        "lifetime": lifetime,
        # "toast": Toaster.__setup_fh__(app=app),
    }

    # TEARDOWN


app = fh.FastHTML(
    htmlkw={"data-theme": "spellbook"},
    hdrs=(
        FRANKEN_UI_CSS, TAILWIND,
        fh.Script(src=const.THOUGHTSPOT_SDK),
        fh.Link(href="/static/style.css", rel="stylesheet", type="text/css"),
    ),
    lifespan=lifespan,
    secret_key=os.environ.get("SECRET_KEY", "default-secret-key"),
)


@app.get("/favicon.ico")
async def _() -> fh.FileResponse:
    return fh.FileResponse(const.DIR_STATIC.joinpath("favicon.ico").as_posix())


@app.get("/static/{file:path}")
async def static_files(file: pathlib.Path) -> fh.FileResponse:
    fp = const.DIR_STATIC.joinpath(file)

    if not fp.exists():
        log.warning(f"File '/static/{file}' was requested, but does not exist!")

    return fh.FileResponse(fp.as_posix())


@app.get("/")
@auth.is_authorized
async def _(app: fh.FastHTML, request: Request):
    """Homepage."""
    mage_icon = fh.Img(src="https://api.dicebear.com/9.x/adventurer-neutral/svg?seed=Annie")
    mage_name = "Mage Johnson"
    last_swap = dt.datetime.now(tz=dt.timezone.utc).strftime("%H:%M:%S")

    # lifetime = request.state.lifetime

    init = thoughtspot_sdk.Init(thoughtspot_host=os.environ["HOST"], authentication="passthru")
    full = thoughtspot_sdk.FullAppEmbed(div_id="embed-container")

    page = fh.Body(
        fh.Div(

            # ThoughtSpot iFrame Component
            fh.Div(full, id="embed-container", cls="h-[80vh] w-[80vw] uk-background-muted"),

            # Admin Comment
            fh.Div(
                fh.Article(
                    fh.Header(
                        fh.Div(
                            fh.Div(mage_icon, cls="uk-comment-avatar uk-margin-small-right"),
                            fh.Div(
                                fh.Div(mage_name, cls="uk-comment-title"),
                                fh.P(f"updated at {last_swap}", id="active-spells-last-update", cls="uk-comment-meta"),
                                cls="uk-flex-1"
                            ),
                            cls="uk-flex uk-flex-middle",
                        ),
                        cls="uk-comment-header",
                    ),
                    fh.Div(
                        fh.P(
                            "There are no spells available to cast!",
                            id="active-spells-amount",
                            hx_trigger="check-active-spells from:body",
                            hx_get="/update-spells-indicator",
                        ),
                        cls="uk-comment-body"
                    ),
                    cls="uk-comment uk-comment-primary uk-margin-small-top uk-width-1-5 uk-margin-auto-left",
                    tabindex="-1", role="comment",
                ),
            ),

            cls="uk-container uk-position-center",
        ),
    )

    return fh.Title("Spellbook"), init, page


@app.get("/update-spells-indicator")
async def _(request: Request):
    last_swap = dt.datetime.now(tz=dt.timezone.utc).strftime("%H:%M:%S")

    indicator = fh.P(
        f"There are {len(request.state.lifetime.active_spells) or 'no'} spells available to cast!",
        id="active-spells-amount",
        hx_trigger="check-active-spells from:body",
        hx_on__trigger="/active-spells",
    )

    last_update = fh.P(
        f"updated at {last_swap}",
        id="active-spells-last-update", cls="uk-comment-meta",
        hx_swap_oob="#active-spells-last-update",
    )

    return indicator, last_update


@app.post("/is-spellbook-enabled-for")
async def _(request: Request):
    """Check whether or not any Spells are available."""
    lifetime = request.state.lifetime
    data = await request.json()

    if data.get("type", None) == "ROUTE_CHANGE":
        lifetime.current_page = data["data"]["currentPath"]
        log.info(f"Route Changed: {lifetime.current_page}")

    lifetime.active_spells = spells = await request.state.lifetime.spellbook.lookup_spells(request)
    log.info(f"Spells: {spells}")

    tags = [
        fh.HttpHeader("hx-trigger", "check-active-spells"),
    ]

    if spells:
        tags.append(fh.HttpHeader("hx-trigger", "has-available-spell"))

    return tags


if __name__ == "__main__":
    from dotenv import load_dotenv
    import uvicorn

    from spellbook import _logging

    load_dotenv()
    os.environ["DEV"] = "true"

    uvicorn.run("spellbook.__main__:app", port=5002, reload=True, log_config=_logging.CONFIG)
