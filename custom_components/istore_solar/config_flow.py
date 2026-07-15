"""Config flow for iStore Solar."""

from __future__ import annotations

import logging
from datetime import datetime
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
    IStoreSolarEncryptionError,
    IStoreSolarLoginResult,
    IStoreSolarMalformedPublicKeyError,
    IStoreSolarMalformedResponseError,
    IStoreSolarTokenMismatchError,
    IStoreSolarUnexpectedLoginResponseError,
    IStoreSolarUnsupportedResponseError,
)
from .const import (
    AUTH_MODE_AUTOMATIC,
    AUTH_MODE_MANUAL_TOKEN,
    CONF_ACCESS_TOKEN,
    CONF_ACCOUNT,
    CONF_AUTH_MODE,
    CONF_AUTOMATIC_RELOGIN_COUNT,
    CONF_LAST_AUTH_ERROR_CLASS,
    CONF_LATEST_LOGIN_SUCCESS,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_TOKEN_CREATE_TIME,
    CONF_TOKEN_EXPIRES,
    CONF_TOKEN_REFRESH_TIME,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    MAX_SCAN_INTERVAL_SECONDS,
    MIN_SCAN_INTERVAL_SECONDS,
)

LOGGER = logging.getLogger(__name__)
CONF_PASSWORD_REPLACEMENT = "password_replacement"


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


def _automatic_schema(*, include_name: bool) -> vol.Schema:
    """Return the automatic account/password login schema."""
    fields: dict[Any, Any] = {
        vol.Required(CONF_ACCOUNT): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
        ),
        vol.Required(CONF_PASSWORD): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
    if include_name:
        fields[vol.Optional(CONF_NAME, default=DEFAULT_NAME)] = str
    return vol.Schema(fields)


def _automatic_options_schema(
    *,
    default_account: str = "",
    default_scan_interval: int = DEFAULT_SCAN_INTERVAL_SECONDS,
) -> vol.Schema:
    """Return the automatic-login options schema."""
    return vol.Schema(
        {
            vol.Required(CONF_ACCOUNT, default=default_account): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
            ),
            vol.Optional(CONF_PASSWORD_REPLACEMENT, default=""): selector.TextSelector(
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


async def _validate_login(
    hass: HomeAssistant,
    account: str,
    password: str,
) -> IStoreSolarLoginResult:
    """Validate account/password credentials and return a login result."""
    client = IStoreSolarApiClient(async_get_clientsession(hass))
    return await client.async_login_and_get_token(account, password)


def _entry_data_from_login(
    *,
    name: str,
    account: str,
    password: str,
    result: IStoreSolarLoginResult,
) -> dict[str, Any]:
    """Return config-entry data for an automatic-login entry."""
    return {
        CONF_NAME: name,
        CONF_AUTH_MODE: AUTH_MODE_AUTOMATIC,
        CONF_ACCOUNT: account,
        CONF_PASSWORD: password,
        CONF_ACCESS_TOKEN: result.access_token,
        CONF_TOKEN_EXPIRES: result.expires,
        CONF_TOKEN_CREATE_TIME: result.create_time,
        CONF_TOKEN_REFRESH_TIME: result.refresh_time,
        CONF_LATEST_LOGIN_SUCCESS: datetime.now().isoformat(),
        CONF_AUTOMATIC_RELOGIN_COUNT: 0,
        CONF_LAST_AUTH_ERROR_CLASS: None,
    }


def _error_from_exception(err: Exception) -> tuple[str, str]:
    """Map API exceptions to config-flow error keys and safe form diagnostics."""
    if isinstance(err, IStoreSolarAuthenticationError):
        return "invalid_auth", ""
    if isinstance(err, IStoreSolarConnectionError):
        return "cannot_connect", ""
    if isinstance(err, IStoreSolarMalformedPublicKeyError):
        return "malformed_public_key", ""
    if isinstance(err, IStoreSolarEncryptionError):
        return "encryption_failed", ""
    if isinstance(err, IStoreSolarTokenMismatchError):
        return "token_mismatch", ""
    if isinstance(err, IStoreSolarUnexpectedLoginResponseError):
        return "unexpected_login_response", _development_error_detail(
            "Unexpected login response",
            err,
        )
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

    VERSION = 4

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
        """Let the user choose an authentication mode."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["automatic", "manual_token"],
        )

    async def async_step_automatic(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle automatic account/password login setup."""
        errors: dict[str, str] = {}
        error_detail = ""

        if user_input is not None:
            account = str(user_input[CONF_ACCOUNT]).strip()
            password = str(user_input[CONF_PASSWORD])
            try:
                result = await _validate_login(self.hass, account, password)
            except Exception as err:  # noqa: BLE001 - mapped to HA form errors.
                errors["base"], error_detail = _error_from_exception(err)
            else:
                user_info = result.user_info
                unique_id = user_info.get("userId")
                if isinstance(unique_id, str) and unique_id:
                    await self.async_set_unique_id(unique_id)
                    self._abort_if_unique_id_configured(
                        updates={
                            **_entry_data_from_login(
                                name=user_input[CONF_NAME],
                                account=account,
                                password=password,
                                result=result,
                            )
                        }
                    )

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=_entry_data_from_login(
                        name=user_input[CONF_NAME],
                        account=account,
                        password=password,
                        result=result,
                    ),
                )

        return self.async_show_form(
            step_id="automatic",
            data_schema=_automatic_schema(include_name=True),
            errors=errors,
            description_placeholders={"error_detail": error_detail},
        )

    async def async_step_manual_token(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle advanced manual bearer-token setup."""
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
                        updates={
                            CONF_ACCESS_TOKEN: access_token,
                            CONF_AUTH_MODE: AUTH_MODE_MANUAL_TOKEN,
                        }
                    )

                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_NAME: user_input[CONF_NAME],
                        CONF_AUTH_MODE: AUTH_MODE_MANUAL_TOKEN,
                        CONF_ACCESS_TOKEN: access_token,
                    },
                )

        return self.async_show_form(
            step_id="manual_token",
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
        """Ask the user for replacement credentials."""
        entry = self._reauth_entry
        if entry is None:
            return self.async_abort(reason="reauth_failed")
        if entry.data.get(CONF_AUTH_MODE, AUTH_MODE_MANUAL_TOKEN) == AUTH_MODE_AUTOMATIC:
            return await self.async_step_reauth_automatic(user_input)
        return await self.async_step_reauth_manual_token(user_input)

    async def async_step_reauth_automatic(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Ask the user for replacement account/password credentials."""
        errors: dict[str, str] = {}
        error_detail = ""
        entry = self._reauth_entry
        if entry is None:
            return self.async_abort(reason="reauth_failed")

        if user_input is not None:
            account = str(user_input[CONF_ACCOUNT]).strip()
            password = str(user_input[CONF_PASSWORD])
            try:
                result = await _validate_login(self.hass, account, password)
            except Exception as err:  # noqa: BLE001 - mapped to HA form errors.
                errors["base"], error_detail = _error_from_exception(err)
            else:
                user_info = result.user_info
                unique_id = user_info.get("userId")
                if isinstance(unique_id, str) and entry.unique_id:
                    await self.async_set_unique_id(unique_id)
                    if unique_id != entry.unique_id:
                        return self.async_abort(reason="wrong_account")

                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        **_entry_data_from_login(
                            name=entry.data.get(CONF_NAME, DEFAULT_NAME),
                            account=account,
                            password=password,
                            result=result,
                        ),
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_automatic",
            data_schema=_automatic_schema(include_name=False),
            errors=errors,
            description_placeholders={"error_detail": error_detail},
        )

    async def async_step_reauth_manual_token(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Ask the user for a replacement manual access token."""
        errors: dict[str, str] = {}
        error_detail = ""
        entry = self._reauth_entry
        if entry is None:
            return self.async_abort(reason="reauth_failed")

        if user_input is not None:
            access_token = user_input[CONF_ACCESS_TOKEN]
            try:
                user_info = await _validate_token(self.hass, access_token)
            except Exception as err:  # noqa: BLE001 - mapped to HA form errors.
                errors["base"], error_detail = _error_from_exception(err)
            else:
                unique_id = user_info.get("userId")
                if isinstance(unique_id, str) and entry.unique_id:
                    await self.async_set_unique_id(unique_id)
                    if unique_id != entry.unique_id:
                        return self.async_abort(reason="wrong_account")

                self.hass.config_entries.async_update_entry(
                    entry,
                    data={
                        **entry.data,
                        CONF_AUTH_MODE: AUTH_MODE_MANUAL_TOKEN,
                        CONF_ACCESS_TOKEN: access_token,
                    },
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        return self.async_show_form(
            step_id="reauth_manual_token",
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
        if self._config_entry.data.get(CONF_AUTH_MODE, AUTH_MODE_MANUAL_TOKEN) == AUTH_MODE_AUTOMATIC:
            return await self.async_step_automatic(user_input)
        return await self.async_step_manual_token(user_input)

    async def async_step_automatic(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage automatic-login options."""
        errors: dict[str, str] = {}
        error_detail = ""
        current_scan_interval = int(
            self._config_entry.options.get(
                CONF_SCAN_INTERVAL,
                DEFAULT_SCAN_INTERVAL_SECONDS,
            )
        )
        current_account = str(self._config_entry.data.get(CONF_ACCOUNT, ""))

        if user_input is not None:
            scan_interval = int(user_input[CONF_SCAN_INTERVAL])
            if not (
                MIN_SCAN_INTERVAL_SECONDS
                <= scan_interval
                <= MAX_SCAN_INTERVAL_SECONDS
            ):
                errors[CONF_SCAN_INTERVAL] = "invalid_scan_interval"
            else:
                account = str(user_input.get(CONF_ACCOUNT, "")).strip()
                password_input = str(user_input.get(CONF_PASSWORD_REPLACEMENT, ""))
                password = password_input or str(
                    self._config_entry.data.get(CONF_PASSWORD, "")
                )
                data = dict(self._config_entry.data)
                credentials_changed = (
                    account != self._config_entry.data.get(CONF_ACCOUNT)
                    or bool(password_input)
                )
                if credentials_changed:
                    try:
                        result = await _validate_login(self.hass, account, password)
                    except Exception as err:  # noqa: BLE001 - mapped to HA form errors.
                        errors["base"], error_detail = _error_from_exception(err)
                    else:
                        user_info = result.user_info
                        unique_id = user_info.get("userId")
                        if (
                            isinstance(unique_id, str)
                            and self._config_entry.unique_id
                            and unique_id != self._config_entry.unique_id
                        ):
                            errors["base"] = "wrong_account"
                        else:
                            data.update(
                                _entry_data_from_login(
                                    name=data.get(CONF_NAME, DEFAULT_NAME),
                                    account=account,
                                    password=password,
                                    result=result,
                                )
                            )

                if not errors:
                    if credentials_changed:
                        self.hass.config_entries.async_update_entry(
                            self._config_entry,
                            data=data,
                        )
                    return self.async_create_entry(
                        title="",
                        data={CONF_SCAN_INTERVAL: scan_interval},
                    )

        return self.async_show_form(
            step_id="automatic",
            data_schema=_automatic_options_schema(
                default_account=current_account,
                default_scan_interval=current_scan_interval,
            ),
            errors=errors,
            description_placeholders={"error_detail": error_detail},
        )

    async def async_step_manual_token(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage manual-token options."""
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
                            data[CONF_AUTH_MODE] = AUTH_MODE_MANUAL_TOKEN
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
            step_id="manual_token",
            data_schema=_options_schema(default_scan_interval=current_scan_interval),
            errors=errors,
            description_placeholders={"error_detail": error_detail},
        )
