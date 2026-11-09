"""dummy-md: generate valid, configurable Markdown placeholder documents."""

from dummy_md.api import (
    ValidationReport,
    available_dialects,
    available_elements,
    available_presets,
    generate,
    iter_chunks,
    validate,
    write,
)
from dummy_md.config import DocumentSpec, ElementRule, LengthSpec, LineEnding
from dummy_md.core.engine import Generator
from dummy_md.core.registry import Registry, registry
from dummy_md.exceptions import (
    BudgetError,
    ConfigurationError,
    DialectError,
    DummyMdError,
    RenderError,
)
from dummy_md.presets import Preset, register_preset
from dummy_md.text import register_text_style, text_styles

__version__ = "0.1.0"

__all__ = [
    "BudgetError",
    "ConfigurationError",
    "DialectError",
    "DocumentSpec",
    "DummyMdError",
    "ElementRule",
    "Generator",
    "LengthSpec",
    "LineEnding",
    "Preset",
    "Registry",
    "RenderError",
    "ValidationReport",
    "__version__",
    "available_dialects",
    "available_elements",
    "available_presets",
    "generate",
    "iter_chunks",
    "register_preset",
    "register_text_style",
    "registry",
    "text_styles",
    "validate",
    "write",
]
