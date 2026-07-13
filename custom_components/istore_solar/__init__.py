"""iStore Solar integration for Home Assistant."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import IStoreSolarApiClient
from .const import CONF_ACCESS_TOKEN, DOMAIN
from .coordinator import IStoreSolarDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]

IStoreSolarConfigEntry = ConfigEntry[IStoreSolarDataUpdateCoordinator]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IStoreSolarConfigEntry,
) -> bool:
    """Set up iStore Solar from a config entry."""
    client = IStoreSolarApiClient(
        async_get_clientsession(hass),
        access_token=entry.data[CONF_ACCESS_TOKEN],
    )
    coordinator = IStoreSolarDataUpdateCoordinator(hass, client)

    entry.runtime_data = coordinator
    await coordinator.async_config_entry_first_refresh()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: IStoreSolarConfigEntry,
) -> bool:
    """Unload an iStore Solar config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
