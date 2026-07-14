"""iStore Solar integration for Home Assistant."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import entity_registry as er

from .api import IStoreSolarApiClient
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)
from .coordinator import IStoreSolarDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

IStoreSolarConfigEntry = ConfigEntry[IStoreSolarDataUpdateCoordinator]

GRID_UNIQUE_ID_SUFFIX_MIGRATIONS = {
    "total_grid_imported_energy": "grid_energy_imported_today",
    "total_grid_exported_energy": "grid_energy_exported_today",
    "experimental_total_grid_imported_energy": "total_grid_imported_energy",
    "experimental_total_grid_exported_energy": "total_grid_exported_energy",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IStoreSolarConfigEntry,
) -> bool:
    """Set up iStore Solar from a config entry."""
    client = IStoreSolarApiClient(
        async_get_clientsession(hass),
        access_token=entry.data[CONF_ACCESS_TOKEN],
    )
    scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS)
    coordinator = IStoreSolarDataUpdateCoordinator(
        hass,
        client,
        update_interval=timedelta(seconds=scan_interval),
    )
    entry.runtime_data = coordinator
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: IStoreSolarConfigEntry,
) -> bool:
    """Unload an iStore Solar config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_migrate_entry(
    hass: HomeAssistant,
    entry: IStoreSolarConfigEntry,
) -> bool:
    """Migrate experimental entity unique IDs."""
    entity_registry = er.async_get(hass)
    for registry_entry in er.async_entries_for_config_entry(
        entity_registry,
        entry.entry_id,
    ):
        for old_suffix, new_suffix in GRID_UNIQUE_ID_SUFFIX_MIGRATIONS.items():
            if registry_entry.unique_id.endswith(f"_{old_suffix}"):
                new_unique_id = (
                    registry_entry.unique_id[: -len(old_suffix)] + new_suffix
                )
                new_entity_id = None
                if registry_entry.entity_id.endswith(old_suffix):
                    new_entity_id = (
                        registry_entry.entity_id[: -len(old_suffix)] + new_suffix
                    )
                update_kwargs = {"new_unique_id": new_unique_id}
                if new_entity_id is not None:
                    update_kwargs["new_entity_id"] = new_entity_id
                entity_registry.async_update_entity(
                    registry_entry.entity_id,
                    **update_kwargs,
                )
                break

    if entry.version < 3:
        hass.config_entries.async_update_entry(entry, version=3)
    return True


async def _async_update_listener(
    hass: HomeAssistant,
    entry: IStoreSolarConfigEntry,
) -> None:
    """Reload the config entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
