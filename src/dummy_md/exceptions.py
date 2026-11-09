"""Exception hierarchy for :mod:`dummy_md`."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


class DummyMdError(Exception):
    """Base class for every error raised by :mod:`dummy_md`."""


class ConfigurationError(DummyMdError, ValueError):
    """A specification, option, or registry request is invalid."""


class DialectError(DummyMdError, ValueError):
    """A feature or node is not expressible in the selected dialect."""

    def __init__(self, message: str, *, dialects: Sequence[str] = ()) -> None:
        self.dialects: tuple[str, ...] = tuple(dialects)
        if self.dialects:
            message = f"{message} (supported by: {', '.join(self.dialects)})"
        super().__init__(message)


class BudgetError(DummyMdError, ValueError):
    """A requested length is infeasible for the given constraints."""

    def __init__(
        self,
        message: str,
        *,
        requested: int | None = None,
        achievable: int | None = None,
    ) -> None:
        self.requested = requested
        self.achievable = achievable
        if requested is not None and achievable is not None:
            message = f"{message} (requested {requested}, achievable {achievable})"
        super().__init__(message)


class RenderError(DummyMdError, RuntimeError):
    """The renderer was asked to serialize a node it cannot handle."""
