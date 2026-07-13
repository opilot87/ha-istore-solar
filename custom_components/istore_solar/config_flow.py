"""Config flow for iStore Solar."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    IStoreSolarApiClient,
    IStoreSolarApiError,
    IStoreSolarAuthenticationError,
    IStoreSolarConnectionError,
    IStoreSolarMalformedResponseError,
    IStoreSolarUnsupportedResponseError,
)
from .const import CONF_ACCESS_TOKEN, DEFAULT_NAME, DOMAIN


def _token_schema(*, include_name: bool) -> vol.Schema:
    """Return the access-token form schema."""
    fields: dict[Any, Any] = {
        vol.Required(CONF_ACCESS_TOKEN): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        )
    }
    if include_name:
        fields[vol.Optional(CONF_NAME, default=DEFAULT_NAME)] = str
    return vol.Schema(fields)


async def _validate_token(
    hass: HomeAssistant,
    access_token: str,
) -> dict[str, Any]:
    """Validate a bearer token and return user info."""
    client = IStoreSolarApiClient(
        async_get_clientsession(hass),
        access_token=access_token,
    )
    return await client.async_get_user_info()


def _error_from_exception(err: Exception) -> str:
    """Map API exceptions to config-flow error keys."""
    if isinstance(err, IStoreSolarAuthenticationError):
        return "invalid_auth"
    if isinstance(err, IStoreSolarConnectionError):
        return "cannot_connect"
    if isinstance(err, IStoreSolarMalformedResponseError):
        return "malformed_response"
    if isinstance(err, IStoreSolarUnsupportedResponseError):
        return "unsupported_response"
    if isinstance(err, IStoreSolarApiError):
        return "server_error"
    return "unknown"


class IStoreSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an iStore Solar config flow."""

    VERSION = 1

    _reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            access_token = user_input[CONF_ACCESS_TOKEN]
            try:
                user_info = await _validate_token(self.hass, access_token)
            except Exception as err:  # noqa: BLE001 - mapped to HA form errors.
                errors["base"] = _error_from_exception(err)
            else:
                unique_id = user_info.get("userId")
                if isinstance(unique_id, str) and unique_id:
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured(
                        updates={CONF_ACCESS_TOKEN: access_token}
                    )

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_ACCESS_TOKEN: access_token,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_token_schema(include_name=True),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: dict[str, Any],
    ) -> FlowResult:
        """Handle a request to replace an expired access token."""
        entry_id = self.context.get("entry_id")
        if isinstance(entry_id, str):
            self._reauth_entry = self.hass.config_entries.async_get_entry(entry_id)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Ask the user for a replacement access token."""
        errors: dict[str, str] = {}

        if user_input is not None:
            access_token = user_input[CONF_ACCESS_TOKEN]
            try:
                user_info = await _validate_token(self.hass, access_token)
            except Exception as err:  # noqa: BLE001 - mapped to HA form errors.
                errors["base"] = _error_from_exception(err)
            else:
                entry = self._reauth_entry
                if entry is None:
                    return self.async_abort(reason="reauth_failed")

                unique_id = user_info.get("userId")
                if isinstance(unique_id, str) and entry.unique_id:
                    await self.async_set_unique_id(unique_id)
                    if unique_id != entry.unique_id:
                        return self.async_abort(reason="wrong_account")

                self.hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, CONF_ACCESS_TOKEN: access_token},
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_token_schema(include_name=False),
            errors=errors,
        )
