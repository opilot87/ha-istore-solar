"""Data update coordinator for iStore Solar."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    IStoreSolarApiClient,
    IStoreSolarAuthenticationError,
    IStoreSolarError,
    IStoreSolarTelemetry,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

LOGGER = logging.getLogger(__name__)


class IStoreSolarDataUpdateCoordinator(DataUpdateCoordinator[IStoreSolarTelemetry]):
    """Coordinate data updates from the future iStore Solar API."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: IStoreSolarApiClient,
        *,
        update_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )
        self.client = client

    async def _async_update_data(self) -> IStoreSolarTelemetry:
        """Fetch the latest data from the API client."""
        try:
            return await self.client.async_get_data()
        except IStoreSolarAuthenticationError as err:
            raise ConfigEntryAuthFailed("iStore Solar access token expired") from err
        except IStoreSolarError as err:
            raise UpdateFailed(str(err)) from err
