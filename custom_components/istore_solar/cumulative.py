"""Cumulative energy helpers for iStore Solar."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CumulativeFieldObservation:
    """Runtime observation state for one cumulative counter source."""

    detected: bool = False
    missing: bool = False
    malformed: bool = False
    decreased: bool = False
    value_type: str | None = None


def cumulative_native_value(value: Any) -> float | int | None:
    """Return a non-negative cumulative counter value, or None if invalid."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, float):
        return value if value >= 0 else None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            number = float(stripped)
        except ValueError:
            return None
        if number < 0:
            return None
        return int(number) if number.is_integer() else number
    return None


def value_type_name(value: Any) -> str:
    """Return a stable sanitized type name for diagnostics."""
    if isinstance(value, bool):
        return "bool"
    if value is None:
        return "missing"
    return type(value).__name__


def observe_cumulative_value(
    observations: dict[str, CumulativeFieldObservation],
    previous_values: dict[str, float | int],
    decreased_keys: set[str],
    sensor_key: str,
    raw_value: Any,
) -> float | int | None:
    """Normalize and record one cumulative counter observation."""
    observation = observations.setdefault(sensor_key, CumulativeFieldObservation())
    observation.value_type = value_type_name(raw_value)
    if raw_value is None:
        observation.missing = True
        return None

    value = cumulative_native_value(raw_value)
    if value is None:
        observation.detected = True
        observation.malformed = True
        return None

    observation.detected = True
    previous = previous_values.get(sensor_key)
    if previous is not None and value < previous:
        observation.decreased = True
        decreased_keys.add(sensor_key)
    if sensor_key in decreased_keys:
        observation.decreased = True
    previous_values[sensor_key] = value
    return value
