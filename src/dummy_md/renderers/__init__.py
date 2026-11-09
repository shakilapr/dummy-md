"""Dialect renderers."""

from dummy_md.core.dialects import Dialect
from dummy_md.renderers.base import BaseRenderer, InlineMode, escape_text
from dummy_md.renderers.commonmark import CommonMarkRenderer
from dummy_md.renderers.gfm import GFMRenderer

RENDERERS: dict[str, type[CommonMarkRenderer]] = {
    "commonmark": CommonMarkRenderer,
    "gfm": GFMRenderer,
}


def get_renderer(dialect: Dialect) -> BaseRenderer:
    renderer_type = RENDERERS.get(dialect.renderer)
    if renderer_type is None:
        raise LookupError(f"no renderer registered for {dialect.renderer!r}")
    return renderer_type(dialect)


__all__ = [
    "RENDERERS",
    "BaseRenderer",
    "CommonMarkRenderer",
    "GFMRenderer",
    "InlineMode",
    "escape_text",
    "get_renderer",
]
