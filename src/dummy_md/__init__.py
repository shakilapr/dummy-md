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
from dummy_md.config import DocumentSpec, ElementRule, LengthSpec
from dummy_md.core.engine import Generator
from dummy_md.exceptions import (
    BudgetError,
    ConfigurationError,
    DialectError,
    DummyMdError,
    RenderError,
)

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
    "RenderError",
    "ValidationReport",
    "__version__",
    "available_dialects",
    "available_elements",
    "available_presets",
    "generate",
    "iter_chunks",
    "validate",
    "write",
]
