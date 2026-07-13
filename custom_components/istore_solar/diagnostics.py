"""Diagnostics support for iStore Solar."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import IStoreSolarConfigEntry
from .api import redact_sensitive_data


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: IStoreSolarConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry with sensitive data redacted."""
    coordinator = entry.runtime_data
    telemetry = coordinator.data

    data: dict[str, Any] = {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_exception": str(coordinator.last_exception)
            if coordinator.last_exception
            else None,
        },
        "telemetry": {
            "has_data": telemetry is not None,
            "sensor_keys": sorted(telemetry.values) if telemetry else [],
            "device_keys": sorted(telemetry.devices) if telemetry else [],
        },
    }

    return redact_sensitive_data(data)
