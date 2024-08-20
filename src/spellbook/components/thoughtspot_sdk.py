from __future__ import annotations

from typing import Any
import json

from fasthtml import common as fh
import pydantic


class Init(pydantic.BaseModel):
    """ """
    thoughtspot_host: str
    # auth_type: ...

    def __ft__(self) -> Any:
        return fh.Script(
            f"""
            window.tsembed.init({{
                thoughtSpotHost: "{self.thoughtspot_host}",
                authType: window.tsembed.AuthType.None,

            }});
            """
        )


class FullAppEmbed(pydantic.BaseModel):
    """ """
    div_id: str
    show_primary_navbar: bool = True

    def __ft__(self) -> Any:
        return fh.Script(
            f"""
            async function mirror_event(payload) {{
                await fetch('/mirror-embed-event', {{
                    headers: {{'content-type': 'application/json'}},
                    method: 'POST',
                    body: JSON.stringify(payload),
                }});
            }}

            const app = new window.tsembed.AppEmbed(document.getElementById('{self.div_id}'), {{
                showPrimaryNavbar: {json.dumps(self.show_primary_navbar)},
                pageId: window.tsembed.Page.Home,
            }});

            app
            .on(window.tsembed.EmbedEvent.RouteChange, mirror_event)
            .on(window.tsembed.EmbedEvent.DialogOpen, mirror_event)
            .on(window.tsembed.EmbedEvent.DialogClose, mirror_event)
            .on(window.tsembed.EmbedEvent.Error, mirror_event)
            .render();
            """
        )