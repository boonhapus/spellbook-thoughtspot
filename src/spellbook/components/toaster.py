from __future__ import annotations

from typing import Literal
import functools as ft
import logging

from fasthtml import common as fh
from starlette.requests import Request

log = logging.getLogger(__name__)
SPECIAL_SESSION_KEY = "X-FH-CONTAINS-TOASTS"


class Toaster:
    """
    Implements a component which can generate toasts.

    FastHTML doesn't yet have a way to set up "After" hooks for the RouterX,
    so it's recommended to use the lifespan to setup the Toaster.

    Usage
    -----
    >>> @contextlib.asynccontextmanager
    >>> async def lifespan(app: fh.FastHTML) -> AsyncIterator[AppLifespanState]:
    >>>     yield {"toast": Toaster.__setup__(app=app)}
    >>> ...
    >>> 
    >>> request.state.toast(request, message="Some message", type="info")
    >>> # or
    >>> request.state.toast.info(request, message="Some message")
    """
    _has_registered_on_app: bool = False

    CSS = fh.Style(
        """
        .fh-toast-container {
            position: fixed; top: 20px; left: 50%; transform: translateX(-50%); z-index: 1000;
            display: flex; flex-direction: column; align-items: center; width: 100%;
            opacity: 0; transition: opacity 0.3s ease-in-out;
            pointer-events: none;
        }
        .fh-toast {
            background-color: #333; color: white;
            padding: 12px 20px; border-radius: 4px; margin-bottom: 10px;
            max-width: 80%; width: auto; text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            pointer-events: auto;
        }
        .fh-toast-info { background-color: #2196F3; }
        .fh-toast-success { background-color: #4CAF50; }
        .fh-toast-warning { background-color: #FF9800; }
        .fh-toast-error { background-color: #F44336; }
        """
    )

    JS = fh.Script(
        """
        export function proc_htmx(selector, fn) {
            htmx.onLoad(element => {
                const arrayOfMatchingElements = any(selector, element, false);

                if (element.matches && element.matches(selector)) {
                    arrayOfMatchingElements.unshift(element)
                }

                arrayOfMatchingElements.forEach(fn);
            });
        }

        class ToastTimer {
            // A timer that will dismiss and remove the toast after 6 seconds.
            //
            constructor(timeout_duration, toast) {
                this.timeout_duration = timeout_duration;
                this.toast = toast
                this.current_timeout = null;
            }

            stop_timeout = () => {
                console.log("stopping timeout");
                clearTimeout(this.current_timeout);
            }

            reset_timeout = () => {
                console.log("resetting timeout");
                clearTimeout(this.current_timeout);
                this.toast.style.opacity = '0.8';
                this.current_timeout = setTimeout(this.dismiss_toast, this.timeout_duration);
            };

            dismiss_toast = () => {
                clearTimeout(this.current_timeout);
                this.toast.style.opacity = '0';
                setTimeout(this.remove_toast, 300);
            };

            remove_toast = () => {
                this.toast.remove();
            }
        }

        export async function handle_toast(toast_container) {
            console.log(toast_container);
            const timer = new ToastTimer(6000, toast_container);

            // Pause the timeout until the User stops hovering the toast.
            toast_container.addEventListener("mouseenter", timer.stop_timeout);
            toast_container.addEventListener("mouseleave", timer.reset_timeout);

            // Click to dismiss the toast
            toast_container.addEventListener("click", timer.dismiss_toast);

            // Start the timer.
            timer.reset_timeout();
        }

        proc_htmx(".fh-toast-container", handle_toast);
        """,
        type="module",
    )

    @classmethod
    def __setup_fh__(cls, app: fh.FastHTML) -> Toaster:
        if cls._has_registered_on_app:
            return cls()

        app.hdrs += (cls.CSS, cls.JS)
        app.after.append(cls.render_queued_toasts)
        cls._has_registered_on_app = True
        return cls()

    @staticmethod
    def render_queued_toasts(response, request) -> None:
        """Checks if there are any queued toasts, and ready to hx-swap them (oob) after the Body renders."""
        assert isinstance(request, fh.Request), "Request must be an instance of starlette.requests.Request"
        session_with_toasts = SPECIAL_SESSION_KEY in request.session
        response_is_fasttag = isinstance(response, (fh.FT, tuple))

        if not (session_with_toasts and response_is_fasttag):
            return

        is_fasttag_serializable = ft.partial(lambda t: isinstance(t, fh.FT) or hasattr(t, "__ft__"))
        assert all(map(is_fasttag_serializable, response)), "Not all objects in response are compatible with fasthtml"
        toasts: list[fh.Div] = []

        for (message, toast_type) in request.session.pop(SPECIAL_SESSION_KEY, []):
            toasts.append(fh.Div(message, cls=f"fh-toast fh-toast-{toast_type}"))

        toast_container = fh.Div(*toasts, cls="fh-toast-container")
        request.injects.append(toast_container)

    def __call__(self, r: Request, message: str, type: Literal["info", "success", "warning", "error"] = "info") -> None:
        """Add a new toast to the session."""
        toasts = r.session.setdefault(SPECIAL_SESSION_KEY, [])
        toasts.append((message, type))
    
    def info(self, request, *, message: str) -> None:
        """Add a new toast to the session with the type 'info'."""
        self.__call__(request, message=message, type="info")
    
    def success(self, request, *, message: str) -> None:
        """Add a new toast to the session with the type 'success'."""
        self.__call__(request, message=message, type="success")
    
    def warning(self, request, *, message: str) -> None:
        """Add a new toast to the session with the type 'warning'."""
        self.__call__(request, message=message, type="warning")
    
    def error(self, request, *, message: str) -> None:
        """Add a new toast to the session with the type 'error'."""
        self.__call__(request, message=message, type="error")