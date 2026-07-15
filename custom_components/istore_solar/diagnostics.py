"""Diagnostics support for iStore Solar."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import IStoreSolarConfigEntry
from .api import redact_sensitive_data
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_AUTH_MODE,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN_CREATE_TIME,
    CONF_TOKEN_EXPIRES,
    CONF_TOKEN_REFRESH_TIME,
    DEFAULT_SCAN_INTERVAL_SECONDS,
)


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: IStoreSolarConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry with sensitive data redacted."""
    coordinator = entry.runtime_data
    telemetry = coordinator.data
    client = coordinator.client
    last_success_time = getattr(coordinator, "last_update_success_time", None)

    data: dict[str, Any] = {
        "entry": {
            "domain": entry.domain,
            "options": dict(entry.options),
            "polling_interval_seconds": entry.options.get(
                CONF_SCAN_INTERVAL,
                DEFAULT_SCAN_INTERVAL_SECONDS,
            ),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "last_update_success_time": str(last_success_time)
            if last_success_time
            else None,
            "last_exception": str(coordinator.last_exception)
            if coordinator.last_exception
            else None,
        },
        "api": {
            "discovery_cached": client.discovery_cached,
            "auth": {
                **client.auth_diagnostics,
                "entry_auth_mode": entry.data.get(CONF_AUTH_MODE),
                "entry_token_present": bool(entry.data.get(CONF_ACCESS_TOKEN)),
                "entry_password_configured": bool(entry.data.get(CONF_PASSWORD)),
                "expiry_metadata": {
                    "expires_present": CONF_TOKEN_EXPIRES in entry.data,
                    "expires_type": type(entry.data.get(CONF_TOKEN_EXPIRES)).__name__,
                    "create_time_present": CONF_TOKEN_CREATE_TIME in entry.data,
                    "create_time_type": type(
                        entry.data.get(CONF_TOKEN_CREATE_TIME)
                    ).__name__,
                    "refresh_time_present": CONF_TOKEN_REFRESH_TIME in entry.data,
                    "refresh_time_type": type(
                        entry.data.get(CONF_TOKEN_REFRESH_TIME)
                    ).__name__,
                },
            },
        },
        "telemetry": {
            "has_data": telemetry is not None,
            "sensor_keys": sorted(telemetry.values) if telemetry else [],
            "device_keys": sorted(telemetry.devices) if telemetry else [],
            "discovered_asset_types": list(telemetry.discovered_asset_types)
            if telemetry
            else [],
            "meter_asset_discovered": telemetry.meter_asset_discovered
            if telemetry
            else False,
            "source_availability": {
                key: {
                    "available": value.available,
                    "has_native_value": value.native_value is not None,
                    "value_type": type(value.native_value).__name__
                    if value.native_value is not None
                    else "missing",
                }
                for key, value in telemetry.values.items()
            }
            if telemetry
            else {},
            "cumulative": {
                "selected_solar_production_source": (
                    telemetry.selected_solar_production_source
                ),
                "observations": {
                    key: {
                        "detected": observation.detected,
                        "missing": observation.missing,
                        "malformed": observation.malformed,
                        "decreased": observation.decreased,
                        "value_type": observation.value_type,
                    }
                    for key, observation in telemetry.cumulative_observations.items()
                },
            }
            if telemetry
            else {},
        },
    }

    return redact_sensitive_data(data)
