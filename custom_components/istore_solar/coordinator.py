"""Data update coordinator for iStore Solar."""

from __future__ import annotations

import logging
from datetime import timedelta
from time import perf_counter

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
        self.last_update_duration_seconds: float | None = None

    async def _async_update_data(self) -> IStoreSolarTelemetry:
        """Fetch the latest data from the API client."""
        started = perf_counter()
        try:
            data = await self.client.async_get_data()
        except IStoreSolarAuthenticationError as err:
            self.last_update_duration_seconds = perf_counter() - started
            LOGGER.warning(
                "iStore Solar coordinator update failed: stage=poll duration=%.3f exception_class=%s",
                self.last_update_duration_seconds,
                type(err).__name__,
            )
            raise ConfigEntryAuthFailed("iStore Solar access token expired") from err
        except IStoreSolarError as err:
            self.last_update_duration_seconds = perf_counter() - started
            LOGGER.warning(
                "iStore Solar coordinator update failed: stage=poll duration=%.3f exception_class=%s",
                self.last_update_duration_seconds,
                type(err).__name__,
            )
            raise UpdateFailed(str(err)) from err
        self.last_update_duration_seconds = perf_counter() - started
        LOGGER.debug(
            "iStore Solar coordinator update succeeded: stage=poll duration=%.3f",
            self.last_update_duration_seconds,
        )
        return data
