"""Power value helpers for iStore Solar."""

from __future__ import annotations


def positive_power(value: float | int | str | None) -> float | int | None:
    """Return the positive part of a signed power value."""
    if not isinstance(value, (float, int)):
        return None
    return max(value, 0)


def inverted_positive_power(value: float | int | str | None) -> float | int | None:
    """Return the positive magnitude of a negative signed power value."""
    if not isinstance(value, (float, int)):
        return None
    return max(-value, 0)
