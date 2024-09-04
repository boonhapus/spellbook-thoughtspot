from __future__ import annotations

import json

from fasthtml import common as fh

from spellbook.spells.base import Spell


class RevealPrivilegedUsers(Spell):
    """ """
    ui_key: str = "/admin:*"

    def __init__(self):
        self.user_cache = set()
    
    async def fetch_privileged_users(self, org: int = 0, privilege: str = "ADMINISTRATION"):
        """Fetch the list of privileged users."""
        offset = 0
        limit  = 20

        while True:
            r = await api.search_users(
                record_offset=offset,
                record_size=limit,
                org_identifiers=[org],
                privileges=[privilege],
                sort_options={"field_name": "NAME", "order": "ASC"},
            )

            if not r.is_success:
                # log.error()
                break
            
            d = r.json()

            self.user_cache.add(user["name"] for user in d)

            if len(d) < limit:
                break

            offset = len(self.user_cache)

    async def invoke(self) -> None:
        """Perform some work whenever the spell is selected."""
        await self.fetch_privileged_users()

    def __ft__(self) -> fh.FT:
        """Renderable for the spell."""

        js = fh.Script(
            f"""
            function revealPrivilegedUsers() {{
                const privileged_users = {json.dumps(list(self.user_cache))};
                const spans = document.getElementsByTagName('span');

                // If we find a <span> which matches a privileged user, then we need add the 
                // class 'is-privileged-user' to it's nearest ancestor <li>.

                for (let i = 0; i < spans.length; i++) {{
                    if (privileged_users.includes(spans[i].textContent)) {{
                        spans[i].closet('li').classList.add('is-privileged-user');
                    }}
                }}
            }}

            // Call the function whenever we paginate in the UI.
            // TODO: find the appropriate even to listen for.
            // document.addEventListener('htmx:afterSwap', revealPrivilegedUsers)

            revealPrivilegedUsers();
            """
        )

        css = fh.Style(
            """
            .is-privileged-user {
                background-color: #f4e7fd;
            }
            """
        )
        return js, css
