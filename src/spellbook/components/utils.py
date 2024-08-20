from __future__ import annotations

from typing import Literal

from fasthtml.common import FT, NotStr


def _copy_ft(tag: FT) -> FT:
    """Create a new tag with the same attributes and children."""
    if isinstance(tag, (NotStr, str)):
        return tag
    return FT(tag=tag.tag, cs=tuple(_copy_ft(t) for t in tag.children), attrs=dict(tag.attrs), void_=tag.void_)


def update_classes(tag: FT, *classes: str, method: Literal["ADD", "TOGGLE", "REMOVE"] = "ADD") -> FT:
    """Add, Toggle, or Remove classes from an element."""
    # Don't modify the tag in-place, in case it's being reused.
    new = _copy_ft(tag)
    old_classes = set(new.attrs.get("class", "").split())

    if method == "ADD":
        old_classes.update(classes)

    if method == "TOGGLE":
        old_classes.symmetric_difference_update(classes)
    
    if method == "REMOVE":
        old_classes.difference_update(classes)

    new.attrs["class"] = " ".join(old_classes)
    return new


def add_sse(tag: FT, *, connect: str, target: str, close: str | None = None, hx_swap: str | None = None, **kwargs) -> FT:
    """Inject SSE information into an element."""
    # Don't modify the tag in-place, in case it's being reused.
    new = _copy_ft(tag)

    new.attrs["hx-ext"] = "sse"
    new.attrs["sse-connect"] = connect
    new.attrs["sse-swap"] = target

    if close is not None:
        new.attrs["sse-close"] = close
    
    if hx_swap is not None:
        new.attrs["hx-swap"] = hx_swap
    
    if kwargs:
        new.attrs.update(kwargs)

    return new
