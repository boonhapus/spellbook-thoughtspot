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
            async function replicate_event_to_spellbook(payload) {{
                //
                r = await fetch("/is-spellbook-enabled-for", {{
                    headers: {{"content-type": "application/json"}},
                    method: "POST",
                    body: JSON.stringify(payload),
                }});

                // We need to process the Response headers from
                // spellbook/is-spellbook-enabled-for so that we can trigger
                // the HX attributes.
                for (const [header, data] of r.headers.entries()) {{
                    if (header.toLowerCase() == 'hx-trigger') {{
                        htmx.trigger("body", data)
                    }}
                }}
           }}

            const app = new window.tsembed.AppEmbed(document.getElementById('{self.div_id}'), {{
                showPrimaryNavbar: {json.dumps(self.show_primary_navbar)},
                pageId: window.tsembed.Page.Home,
            }});

            app
            .on(window.tsembed.EmbedEvent.RouteChange, replicate_event_to_spellbook)
            .on(window.tsembed.EmbedEvent.DialogOpen, replicate_event_to_spellbook)
            .on(window.tsembed.EmbedEvent.DialogClose, replicate_event_to_spellbook)
            .on(window.tsembed.EmbedEvent.Error, replicate_event_to_spellbook)
            .render();
            """
        )