"""Config flow for iStore Solar."""

from __future__ import annotations

import logging
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
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_SCAN_INTERVAL,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    MAX_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
)

LOGGER = logging.getLogger(__name__)


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


def _options_schema(
    *,
    default_access_token: str = "",
    default_scan_interval: int = DEFAULT_SCAN_INTERVAL_SECONDS,
) -> vol.Schema:
    """Return the options form schema."""
    return vol.Schema(
        {
            vol.Optional(
                CONF_ACCESS_TOKEN,
                default=default_access_token,
            ): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=default_scan_interval,
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=MIN_SCAN_INTERVAL_SECONDS,
                    max=MAX_SCAN_INTERVAL_SECONDS,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
        }
    )


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


def _error_from_exception(err: Exception) -> tuple[str, str]:
    """Map API exceptions to config-flow error keys and safe form diagnostics."""
    if isinstance(err, IStoreSolarAuthenticationError):
        return "invalid_auth", ""
    if isinstance(err, IStoreSolarConnectionError):
        return "cannot_connect", ""
    if isinstance(err, IStoreSolarMalformedResponseError):
        return "unsupported_response", _development_error_detail(
            "Unexpected response",
            err,
        )
    if isinstance(err, IStoreSolarUnsupportedResponseError):
        return "unsupported_response", _development_error_detail(
            "Unsupported response",
            err,
        )
    if isinstance(err, IStoreSolarApiError):
        return "api_error", _development_error_detail("API error", err)
    LOGGER.debug("Unexpected iStore Solar config-flow exception", exc_info=err)
    return "unknown", ""


def _development_error_detail(prefix: str, err: Exception) -> str:
    """Return a temporary safe development-only form diagnostic."""
    operation = getattr(err, "operation", None) or "unknown operation"
    status = getattr(err, "status", None)
    if isinstance(status, int):
        return f"{prefix} during {operation} (HTTP {status})."
    return f"{prefix} during {operation}."


class IStoreSolarConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an iStore Solar config flow."""

    VERSION = 2

    _reauth_entry: config_entries.ConfigEntry | None = None

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow handler."""
        return IStoreSolarOptionsFlow(config_entry)

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        error_detail = ""

        if user_input is not None:
            access_token = user_input[CONF_ACCESS_TOKEN]
            try:
                user_info = await _validate_token(self.hass, access_token)
            except Exception as err:  # noqa: BLE001 - mapped to HA form errors.
                errors["base"], error_detail = _error_from_exception(err)
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
            description_placeholders={"error_detail": error_detail},
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
        error_detail = ""

        if user_input is not None:
            access_token = user_input[CONF_ACCESS_TOKEN]
            try:
                user_info = await _validate_token(self.hass, access_token)
            except Exception as err:  # noqa: BLE001 - mapped to HA form errors.
                errors["base"], error_detail = _error_from_exception(err)
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
            description_placeholders={"error_detail": error_detail},
        )


class IStoreSolarOptionsFlow(config_entries.OptionsFlow):
    """Handle iStore Solar options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage iStore Solar options."""
        errors: dict[str, str] = {}
        error_detail = ""
        current_scan_interval = int(
            self._config_entry.options.get(
                CONF_SCAN_INTERVAL,
                DEFAULT_SCAN_INTERVAL_SECONDS,
            )
        )

        if user_input is not None:
            scan_interval = int(user_input[CONF_SCAN_INTERVAL])
            if not (
                MIN_SCAN_INTERVAL_SECONDS
                <= scan_interval
                <= MAX_SCAN_INTERVAL_SECONDS
            ):
                errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
            else:
                token_input = str(user_input.get(CONF_ACCESS_TOKEN, "")).strip()
                data = dict(self._config_entry.data)
                if token_input:
                    try:
                        user_info = await _validate_token(self.hass, token_input)
                    except Exception as err:  # noqa: BLE001 - mapped to HA form errors.
                        errors["base"], error_detail = _error_from_exception(err)
                    else:
                        unique_id = user_info.get("userId")
                        if (
                            isinstance(unique_id, str)
                            and self._config_entry.unique_id
                            and unique_id != self._config_entry.unique_id
                        ):
                            errors["base"] = "wrong_account"
                        else:
                            data[CONF_ACCESS_TOKEN] = token_input

                if not errors:
                    if token_input:
                        self.hass.config_entries.async_update_entry(
                            self._config_entry,
                            data=data,
                        )
                    return self.async_create_entry(
                        title="",
                        data={CONF_SCAN_INTERVAL: scan_interval},
                    )

        return self.async_show_form(
            step_id="init",
            data_schema=_options_schema(default_scan_interval=current_scan_interval),
            errors=errors,
            description_placeholders={"error_detail": error_detail},
        )
