from __future__ import annotations

from typing import Any, Callable

from fasthtml import common as fh
import pydantic

from spellbook.components import utils

# TODO: MAYBE?
#
#
# class Component(pydantic.BaseModel):
#     """A base class for components."""
#     tag: fh.FT | fh.NotStr

#     model_config = pydantic.ConfigDict(extra="allow",arbitrary_types_allowed=True)

#     @classmethod
#     def component_factory(cls, tag: str) -> Callable[[...], Component]:
#         """Create a new component from a fasthtml tag."""
#         def _make(*children: fh.FT, target_id: str | None = None, **kwargs: _P.kwargs) -> Component:
#             fast_tag = fh.ft_hx(tag, *children, target_id=target_id, **kwargs)
#             return cls(tag=fast_tag)

#         return _make
    
#     @property
#     def children(self) -> tuple[Component, ...]:
#         """Get the children of the Component's tag."""
#         if not isinstance(self.tag, fh.FT) or not self.tag.children:
#             return tuple()

#         return tuple(Component(tag=child) for child in self.tag.children)
    
#     def __getitem__(self, id: str) -> Component:
#         for child in self.children:
#             if isinstance(child.tag, (str, fh.NotStr)):
#                 continue

#             if child.tag.attrs.get("id", None) == id:
#                 return child
            
#             try:
#                 return child[id]
#             except KeyError:
#                 continue

#         raise KeyError(f"No child found with {id=}")

#     def __ft__(self) -> fh.FT:
#         return self.tag

#     def copy(self) -> Component:  # type: ignore[override]
#         """Construct a new Component."""
#         return Component(tag=utils._copy_ft(self.tag))
    
#     def update_class(self, *classes: str, method: str = "ADD", new: bool = False) -> Component:
#         """ """
#         component = self.copy() if new else self
#         old_classes = set(component.tag.attrs["class"].split(" "))

#         if method == "ADD":
#             old_classes.update(classes)

#         if method == "TOGGLE":
#             old_classes.symmetric_difference_update(classes)
        
#         if method == "REMOVE":
#             old_classes.difference_update(classes)

#         component.tag.attrs["class"] = " ".join(old_classes)
#         return component


# DEVNOTE: @boonhapus, 2024-08-17
#  Need to add more SVG icons?
#
#  1. Go to https://www.svgrepo.com and find your SVG.
#  2. Edit the vector and select COPY SVG.
#  3. Paste it into https://www.svgviewer.dev/ -> Optimize -> Prettify.
#  4. Download the SVG and give it a shortname.
#  5. Add it to /static/icons.
#

AuthenticationForm = fh.Form(
    fh.Label(
        fh.Img(src="/static/icons/link.svg", cls="w-6"),
        fh.Input(
            name="site", type="url", required=True,
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
    hx_post="/auth",
    cls="flex flex-col gap-4 w-full max-w-md",
)


Mage = fh.Img(src="/static/icons/mage.svg", id="mage")


