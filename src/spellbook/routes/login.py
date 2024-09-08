from __future__ import annotations

import logging

from fasthtml import common as fh
from starlette.requests import Request
from starlette.routing import Route
import httpx

from spellbook import auth, components, types

log = logging.getLogger(__name__)

AuthenticationForm = fh.Form(
    fh.Label(
        fh.Img(src="/static/icons/link.svg", cls="w-6"),
        fh.Input(
            name="host", type="url", required=True,
            placeholder="https://customer.thoughtspot.cloud",
            cls="grow",
        ),
        cls="input input-bordered flex items-center gap-4"
    ),
    fh.Label(
        fh.Img(src="/static/icons/user.svg", cls="w-6"),
        fh.Input(
            name="user", type="text", required=True,
            placeholder="tsadmin", minlength=1,
            cls="grow",
        ),
        cls="input input-bordered flex items-center gap-4"
    ),
    fh.Label(
        fh.Img(src="/static/icons/key.svg", cls="w-6"),
        fh.Input(
            name="pass", type="text", required=True,
            placeholder="secret key", pattern="^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
            cls="grow",
        ),
        enctype="multipart/form-data",
        cls="input input-bordered flex items-center gap-4"
    ),
    fh.Button("Login", cls="btn btn-primary"),
    hx_post="/login/auth",
    cls="flex flex-col gap-4 w-full max-w-md",
)


async def login(request: Request) -> types.PageRenderableFull:
    """Login page."""
    if getattr(request.state.lifetime, "api_session", False):
        return fh.RedirectResponse("/", status_code=303)

    page = fh.Body(
        fh.Div(
            components.utils.update_classes(components.Mage, "w-24", method="ADD"),
            fh.H1("ThoughtSpot Spellbook", cls="text-2xl text-primary"),
            AuthenticationForm,
            cls="h-screen flex flex-col gap-4 items-center justify-center",
        ),
        id="container",
    )
    
    return fh.Title("Spellbook"), page


async def login_auth(request: Request) -> types.PageRenderablePartial:
    """Authenticate the User to ThoughtSpot."""
    data = await request.form()

    try:
        await auth.do_authorization(request, url=data["host"], user=data["user"], secret=data["pass"])  # type: ignore[arg-type]
    
    except httpx.HTTPStatusError as e:
        log.error(f"Auth failed: {e}")
        return AuthenticationForm

    else:
        return fh.HttpHeader("hx-redirect", "/")


routes = [
    Route("/login", endpoint=login, methods=["GET"]),    
    Route("/login/auth", endpoint=login_auth, methods=["POST"]),
]