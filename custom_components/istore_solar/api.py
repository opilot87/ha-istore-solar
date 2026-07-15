"""API models and client for iStore Solar."""

from __future__ import annotations

import asyncio
from asyncio import TimeoutError as AsyncTimeoutError
import base64
from dataclasses import dataclass, field
from datetime import datetime
import json
import logging
import time
from typing import Any, Final, NoReturn

from aiohttp import ClientError, ClientSession, ClientTimeout
from cryptography.exceptions import InvalidKey
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .const import (
    API_BASE_URL,
    APP_ID,
    AUTH_MODE_AUTOMATIC,
    AUTH_MODE_MANUAL_TOKEN,
    DEFAULT_LOCALE,
    DOMAIN,
    MANUFACTURER,
    SENSOR_BATTERY_CHARGED_TODAY,
    SENSOR_BATTERY_CHARGING_POWER,
    SENSOR_BATTERY_DISCHARGED_TODAY,
    SENSOR_BATTERY_DISCHARGING_POWER,
    SENSOR_BATTERY_POWER,
    SENSOR_BATTERY_SOC,
    SENSOR_BATTERY_STATUS,
    SENSOR_GRID_ENERGY_EXPORTED_TODAY,
    SENSOR_GRID_ENERGY_IMPORTED_TODAY,
    SENSOR_GRID_EXPORT_POWER,
    SENSOR_GRID_IMPORT_POWER,
    SENSOR_GRID_POWER,
    SENSOR_HOME_CONSUMPTION_POWER,
    SENSOR_INVERTER_STATUS,
    SENSOR_SITE_STATUS,
    SENSOR_SOLAR_POWER,
    SENSOR_TOTAL_BATTERY_CHARGED_ENERGY,
    SENSOR_TOTAL_BATTERY_DISCHARGED_ENERGY,
    SENSOR_TOTAL_GRID_EXPORTED_ENERGY,
    SENSOR_TOTAL_GRID_IMPORTED_ENERGY,
    SENSOR_TOTAL_SOLAR_PRODUCTION,
)
from .cumulative import (
    CumulativeFieldObservation,
    cumulative_native_value,
    observe_cumulative_value,
    value_type_name,
)
from .power import inverted_positive_power, positive_power
from .privacy import (
    redact_sensitive_data,
    sanitize_content_type as _sanitize_content_type,
    sanitize_response_preview as _sanitize_response_preview,
    sanitize_text as _sanitize_text,
)

REQUEST_TIMEOUT: Final = ClientTimeout(total=20)
LOGGER = logging.getLogger(__name__)
PERMISSION_DENIED_CODE: Final = 88203
INVALID_CREDENTIALS_CODE: Final = 88915
JSON_UNSET: Final = object()
ASSET_TREE_SITE_TYPE: Final = "Hossain-site"
BATTERY_TOTAL_MEASUREMENT_POINTS: Final = (
    "BS.TotalChargingEng,BS.TotalDischargingEng"
)
METER_TOTAL_MEASUREMENT_POINTS: Final = (
    "METER.APConsumedKWH,METER.APProductionKWH"
)
TEMPORARY_HTTP_STATUSES: Final = {429, 502, 503, 504}
MAX_TEMPORARY_REQUEST_ATTEMPTS: Final = 2
RETRY_BACKOFF_SECONDS: Final = 1
LOGIN_TOKEN_KEYS: Final = (
    "id",
    "token",
    "accessToken",
    "access_token",
    "accessTokenKey",
)
SESSION_TOKEN_MIN_LENGTH: Final = 20

SITE_LIVE_MEASUREMENT_POINTS: Final = ",".join(
    (
        "PUB_SITE.PVOutputPower",
        "PUB_SITE.METERActivePW",
        "PUB_SITE.BSActivePW",
        "ConsPower",
        "SITE.GenActivePW",
        "PUB_SITE.Soc",
        "PUB_SITE.EVChargingPW",
    )
)
SITE_LIVE_ATTRIBUTES: Final = "gmtAmount,batteryStorageAmount,strInvAmount,powerDirection"
DEVICE_LIST_TYPES: Final = (
    "Res_Inverter,Res_Meter,Res_Storage,Dongle,Smart_Logger,"
    "Res_WeatherStation,Res_EV_Charger,Res_EV_Connector"
)


class IStoreSolarError(Exception):
    """Base error for iStore Solar API failures."""

    def __init__(
        self,
        message: str,
        *,
        path: str | None = None,
        status: int | None = None,
        content_type: str | None = None,
        response_preview: str | None = None,
        operation: str | None = None,
    ) -> None:
        """Initialize the exception with sanitized diagnostics."""
        super().__init__(message)
        self.path = path
        self.status = status
        self.content_type = content_type
        self.response_preview = response_preview
        self.operation = operation


class IStoreSolarAuthenticationError(IStoreSolarError):
    """Raised when authentication fails or expires."""


class IStoreSolarConnectionError(IStoreSolarError):
    """Raised when the cloud portal cannot be reached."""


class IStoreSolarMalformedResponseError(IStoreSolarError):
    """Raised when the cloud portal returns an unexpected response shape."""


class IStoreSolarUnsupportedResponseError(IStoreSolarError):
    """Raised when the API response is valid but unsupported by this version."""


class IStoreSolarApiError(IStoreSolarError):
    """Raised for non-authentication API errors."""


class IStoreSolarPermissionDeniedError(IStoreSolarApiError):
    """Raised when the API denies a specific authorized request."""


class IStoreSolarMalformedPublicKeyError(IStoreSolarError):
    """Raised when the login public key cannot be used."""


class IStoreSolarEncryptionError(IStoreSolarError):
    """Raised when password encryption fails."""


class IStoreSolarUnexpectedLoginResponseError(IStoreSolarError):
    """Raised when the login/session response shape is unsupported."""


class IStoreSolarTokenMismatchError(IStoreSolarAuthenticationError):
    """Raised when session and user-info tokens do not match."""


@dataclass(slots=True, frozen=True)
class _ResponseContext:
    """Sanitized response context for downstream schema validation."""

    payload: dict[str, Any]
    path: str
    status: int
    content_type: str | None
    response_preview: str | None
    application_code: int | str | None
    auth_token_header: str | None = None


@dataclass(slots=True, frozen=True)
class IStoreSolarPublicKey:
    """Public key and strategy returned by the login endpoint."""

    public_key: str
    strategy: str


@dataclass(slots=True, frozen=True)
class IStoreSolarLoginResult:
    """Validated login result safe for config-entry storage."""

    access_token: str
    user_info: dict[str, Any]
    expires: int | str | None = None
    create_time: int | str | None = None
    refresh_time: int | str | None = None


@dataclass(slots=True, frozen=True)
class _DiscoveredSite:
    """Authorized site data discovered from the browser sequence."""

    site_id: str
    assets: list[dict[str, Any]]


@dataclass(slots=True, frozen=True)
class _AssetTreeCandidate:
    """Sanitized candidate node found in the asset tree."""

    identifier: str
    identifier_field: str
    path: str
    node: dict[str, Any]


@dataclass(slots=True, frozen=True)
class _AssetTreeDiagnostics:
    """Sanitized asset-tree diagnostics."""

    top_level_keys: tuple[str, ...]
    root_node_count: int
    recursive_node_count: int
    type_values: tuple[str, ...]
    resource_type_values: tuple[str, ...]
    mdm_type_values: tuple[str, ...]
    candidate_field_names: tuple[str, ...]
    identifier_fields: tuple[str, ...]
    identifier_lengths: tuple[int, ...]
    has_children_arrays: bool
    has_associated_resources_arrays: bool


@dataclass(slots=True, frozen=True)
class IStoreSolarDevice:
    """A normalized iStore Solar device."""

    identifiers: tuple[str, str]
    name: str
    model: str | None = None
    manufacturer: str | None = None
    via_device: tuple[str, str] | None = None
    serial_number: str | None = None
    sw_version: str | None = None
    hw_version: str | None = None


@dataclass(slots=True, frozen=True)
class IStoreSolarSensorValue:
    """A normalized sensor value returned by the iStore Solar client."""

    native_value: float | int | str | None
    available: bool = True


@dataclass(slots=True, frozen=True)
class IStoreSolarTelemetry:
    """Normalized telemetry used by coordinator-backed entities."""

    site: IStoreSolarDevice
    devices: dict[str, IStoreSolarDevice] = field(default_factory=dict)
    values: dict[str, IStoreSolarSensorValue] = field(default_factory=dict)
    discovered_asset_types: tuple[str, ...] = ()
    cumulative_observations: dict[str, CumulativeFieldObservation] = field(
        default_factory=dict
    )
    selected_solar_production_source: str | None = None
    meter_asset_discovered: bool = False


class IStoreSolarApiClient:
    """Async client for the experimental iStore Solar cloud API."""

    def __init__(
        self,
        session: ClientSession,
        *,
        access_token: str = "",
        auth_mode: str = AUTH_MODE_MANUAL_TOKEN,
        account: str | None = None,
        password: str | None = None,
        token_update_callback: Any | None = None,
        base_url: str = API_BASE_URL,
        locale: str = DEFAULT_LOCALE,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._access_token = access_token.strip()
        self._auth_mode = auth_mode
        self._account = account
        self._password = password
        self._token_update_callback = token_update_callback
        self._base_url = base_url.rstrip("/")
        self._locale = locale
        self._user_info: dict[str, Any] | None = None
        self._discovered_site: _DiscoveredSite | None = None
        self._previous_cumulative_values: dict[str, float | int] = {}
        self._cumulative_decreases: set[str] = set()
        self._login_lock = asyncio.Lock()
        self._automatic_relogin_count = 0
        self._latest_login_success: float | None = None
        self._last_auth_error_class: str | None = None

    @property
    def discovery_cached(self) -> bool:
        """Return whether site discovery has completed and been cached."""
        return self._discovered_site is not None

    @property
    def auth_diagnostics(self) -> dict[str, Any]:
        """Return sanitized authentication diagnostics."""
        return {
            "auth_mode": self._auth_mode,
            "token_present": bool(self._access_token),
            "password_configured": bool(self._password)
            if self._auth_mode == AUTH_MODE_AUTOMATIC
            else False,
            "latest_login_success": self._latest_login_success,
            "automatic_relogin_count": self._automatic_relogin_count,
            "last_auth_error_class": self._last_auth_error_class,
        }

    async def async_get_public_key(self) -> IStoreSolarPublicKey:
        """Return the RSA public key used by the login form."""
        response = await self._request(
            "GET",
            "/hossain-bff/framework/v1.0/user/public-key",
            authenticated=False,
            operation="public-key retrieval",
        )
        data = response.payload.get("data")
        if not isinstance(data, dict):
            err = IStoreSolarUnexpectedLoginResponseError(
                "public-key response missing data",
                path=response.path,
                status=response.status,
                content_type=response.content_type,
                response_preview=response.response_preview,
                operation="public-key retrieval",
            )
            _raise_logged_api_exception(err)
        public_key = data.get("publicKey")
        strategy = data.get("strategy")
        if not isinstance(public_key, str) or not isinstance(strategy, str):
            err = IStoreSolarUnexpectedLoginResponseError(
                "public-key response missing expected fields",
                path=response.path,
                status=response.status,
                content_type=response.content_type,
                response_preview=response.response_preview,
                operation="public-key retrieval",
            )
            _raise_logged_api_exception(err)
        return IStoreSolarPublicKey(public_key=public_key, strategy=strategy)

    async def async_encrypt_password(self, public_key: str, password: str) -> str:
        """Encrypt a plaintext password with the confirmed browser algorithm."""
        try:
            key_bytes = base64.b64decode(public_key, validate=True)
            loaded_key = serialization.load_der_public_key(key_bytes)
        except (ValueError, TypeError) as err:
            raise IStoreSolarMalformedPublicKeyError(
                "iStore Solar public key was malformed",
                operation="password encryption",
            ) from err

        if not isinstance(loaded_key, rsa.RSAPublicKey):
            raise IStoreSolarMalformedPublicKeyError(
                "iStore Solar public key was not RSA",
                operation="password encryption",
            )

        try:
            ciphertext = loaded_key.encrypt(
                password.encode("utf-8"),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
        except (ValueError, InvalidKey) as err:
            raise IStoreSolarEncryptionError(
                "could not encrypt iStore Solar password",
                operation="password encryption",
            ) from err

        return base64.b64encode(ciphertext).decode("ascii")

    async def async_login(self, account: str, password: str) -> tuple[str, str]:
        """Perform the login request and return the login token and organization ID."""
        key = await self.async_get_public_key()
        encrypted_password = await self.async_encrypt_password(key.public_key, password)
        response = await self._request(
            "POST",
            "/hossain-bff/framework/v1.0/user/login",
            authenticated=False,
            json_data={
                "strategy": key.strategy,
                "account": account,
                "password": encrypted_password,
            },
            operation="login",
        )
        token = _extract_login_token(response.payload, response.auth_token_header)
        org_id = _extract_login_org_id(response.payload)
        if token is None:
            err = IStoreSolarUnexpectedLoginResponseError(
                "login response missing access token",
                path=response.path,
                status=response.status,
                content_type=response.content_type,
                response_preview=response.response_preview,
                operation="login",
            )
            _raise_logged_api_exception(err)
        if org_id is None:
            err = IStoreSolarUnexpectedLoginResponseError(
                "login response missing organization",
                path=response.path,
                status=response.status,
                content_type=response.content_type,
                response_preview=response.response_preview,
                operation="login",
            )
            _raise_logged_api_exception(err)
        return token, org_id

    async def async_set_session(self, token: str, org_id: str) -> None:
        """Select the working organization for the freshly logged-in token."""
        await self._request(
            "POST",
            "/hossain-bff/framework/v1.0/user/set-session",
            access_token=token,
            json_data={"orgId": org_id},
            operation="set-session",
        )

    async def async_get_portal_session(self, token: str) -> dict[str, Any]:
        """Return the portal session data for a freshly logged-in token."""
        response = await self._request(
            "POST",
            "/app-portal/web/v1/session/get",
            access_token=token,
            raw_data="null",
            extra_headers={"Locale": self._locale},
            params={"_sid_": str(int(time.time() * 1000))},
            operation="session retrieval",
        )
        data = response.payload.get("data")
        if not isinstance(data, dict):
            err = IStoreSolarUnexpectedLoginResponseError(
                "session response missing data",
                path=response.path,
                status=response.status,
                content_type=response.content_type,
                response_preview=response.response_preview,
                operation="session retrieval",
            )
            _raise_logged_api_exception(err)
        return data

    async def async_validate_token(self, access_token: str) -> dict[str, Any]:
        """Validate one bearer token without mutating the client token."""
        previous_token = self._access_token
        self._access_token = access_token.strip()
        try:
            return await self.async_get_user_info()
        finally:
            self._access_token = previous_token

    async def async_login_and_get_token(
        self,
        account: str,
        password: str,
    ) -> IStoreSolarLoginResult:
        """Perform the full confirmed login sequence and validate the bearer token."""
        login_token, org_id = await self.async_login(account, password)
        await self.async_set_session(login_token, org_id)
        session_data = await self.async_get_portal_session(login_token)
        session_token = session_data.get("id")
        if not isinstance(session_token, str) or len(session_token) < SESSION_TOKEN_MIN_LENGTH:
            raise IStoreSolarUnexpectedLoginResponseError(
                "session response missing access token",
                operation="token extraction",
            )

        previous_token = self._access_token
        self._access_token = session_token
        try:
            user_info = await self.async_get_user_info()
        finally:
            self._access_token = previous_token
        user_info_token = user_info.get("token")
        if isinstance(user_info_token, str) and user_info_token != session_token:
            raise IStoreSolarTokenMismatchError(
                "session token did not match user-info token",
                operation="token validation",
            )
        if not isinstance(user_info_token, str):
            raise IStoreSolarUnexpectedLoginResponseError(
                "user-info response missing token",
                operation="token validation",
            )

        return IStoreSolarLoginResult(
            access_token=session_token,
            user_info=user_info,
            expires=_safe_session_metadata(session_data.get("expires")),
            create_time=_safe_session_metadata(session_data.get("createTime")),
            refresh_time=_safe_session_metadata(session_data.get("refreshTime")),
        )

    async def async_refresh_access_token(self) -> IStoreSolarLoginResult:
        """Perform one automatic relogin and replace the current token."""
        if self._auth_mode != AUTH_MODE_AUTOMATIC or not self._account or not self._password:
            raise IStoreSolarAuthenticationError(
                "automatic login credentials are not configured",
                operation="automatic relogin",
            )
        async with self._login_lock:
            result = await self.async_login_and_get_token(self._account, self._password)
            self._access_token = result.access_token
            self._latest_login_success = time.time()
            self._last_auth_error_class = None
            self._automatic_relogin_count += 1
            if self._token_update_callback is not None:
                await self._token_update_callback(result, self._automatic_relogin_count)
            return result

    async def async_get_user_info(self) -> dict[str, Any]:
        """Return account metadata for the configured bearer token."""
        response = await self._request(
            "GET",
            "/hossain-bff/user/v1.0/user-info",
            operation="user-info validation",
        )
        data = response.payload.get("data")
        if not isinstance(data, dict):
            err = IStoreSolarMalformedResponseError(
                "user-info response missing data",
                path=response.path,
                status=response.status,
                content_type=response.content_type,
                response_preview=response.response_preview,
                operation="user-info validation",
            )
            _raise_logged_api_exception(err)
        self._user_info = data
        return data

    async def async_get_assets(self, site_id: str) -> list[dict[str, Any]]:
        """Return site child assets from the confirmed asset-list request."""
        response = await self._request(
            "POST",
            "/hossain-bff/monitor/v1.0/asset/list",
            json_data={
                "mdmIds": site_id,
                "mdmTypes": DEVICE_LIST_TYPES,
                "view": "WebSiteDetailDeviceList",
                "pageNo": 1,
                "pageSize": 500,
            },
            operation="asset discovery",
        )
        data = response.payload.get("data")
        if not isinstance(data, list):
            err = IStoreSolarMalformedResponseError(
                "asset-list response missing data",
                path=response.path,
                status=response.status,
                content_type=response.content_type,
                response_preview=response.response_preview,
                operation="asset discovery",
            )
            _raise_logged_api_exception(err)
        assets = [item for item in data if isinstance(item, dict)]
        _log_discovery_result(
            endpoint_name="asset/list",
            asset_type_requested=DEVICE_LIST_TYPES,
            identifier_source="asset-tree result",
            identifier=site_id,
            application_code=response.application_code,
            assets=assets,
        )
        return assets

    async def async_get_asset_detail(
        self,
        mdm_id: str,
        *,
        view: str | None = None,
        attributes: str | None = None,
        measurement_points: str | None = None,
    ) -> dict[str, Any]:
        """Return asset detail for one site or device."""
        body: dict[str, Any] = {"mdmIds": mdm_id}
        if view is not None:
            body["view"] = view
        if attributes is not None:
            body["attributes"] = attributes
        if measurement_points is not None:
            body["measurementPoints"] = measurement_points

        response = await self._request(
            "POST",
            "/hossain-bff/monitor/v1.0/asset/detail",
            json_data=body,
            operation="asset detail retrieval",
        )
        data = response.payload.get("data")
        if not isinstance(data, dict):
            err = IStoreSolarMalformedResponseError(
                "asset-detail response missing data",
                path=response.path,
                status=response.status,
                content_type=response.content_type,
                response_preview=response.response_preview,
                operation="asset detail retrieval",
            )
            _raise_logged_api_exception(err)
        return data

    async def async_get_battery_total_energy(
        self,
        battery_id: str,
    ) -> dict[str, Any]:
        """Return optional battery total energy counters from the confirmed endpoint."""
        now = datetime.now()
        response = await self._request(
            "POST",
            "/hossain-bff/monitor/v1.0/measurement-point/time-series",
            json_data={
                "mdmTypes": "Res_Storage",
                "mdmIds": battery_id,
                "startTime": now.replace(
                    hour=0,
                    minute=0,
                    second=0,
                    microsecond=0,
                ).strftime("%Y-%m-%d %H:%M:%S"),
                "endTime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "interval": "5m",
                "measurementPoints": BATTERY_TOTAL_MEASUREMENT_POINTS,
                "autoInterpolate": True,
            },
            operation="optional battery cumulative retrieval",
        )
        data = response.payload.get("data")
        if not isinstance(data, list):
            err = IStoreSolarMalformedResponseError(
                "battery cumulative response missing data",
                path=response.path,
                status=response.status,
                content_type=response.content_type,
                response_preview=response.response_preview,
                operation="optional battery cumulative retrieval",
            )
            _raise_logged_api_exception(err)

        for item in reversed(data):
            if isinstance(item, dict) and any(
                field_name in item
                for field_name in ("BS.TotalChargingEng", "BS.TotalDischargingEng")
            ):
                return item
        return {}

    async def async_get_meter_total_energy(
        self,
        site_id: str,
    ) -> dict[str, dict[str, Any]]:
        """Return optional experimental meter total energy candidate points."""
        response = await self._request(
            "POST",
            "/hossain-bff/monitor/v1.0/asset/list",
            json_data={
                "pageSize": 50,
                "pageNo": 1,
                "mdmIds": site_id,
                "mdmTypes": "Res_Meter",
                "measurementPoints": METER_TOTAL_MEASUREMENT_POINTS,
            },
            operation="optional meter cumulative retrieval",
        )
        data = response.payload.get("data")
        if not isinstance(data, list):
            err = IStoreSolarMalformedResponseError(
                "meter cumulative response missing data",
                path=response.path,
                status=response.status,
                content_type=response.content_type,
                response_preview=response.response_preview,
                operation="optional meter cumulative retrieval",
            )
            _raise_logged_api_exception(err)

        for item in data:
            if not isinstance(item, dict) or _asset_type(item) != "Res_Meter":
                continue
            measurement_points = _dict_value(item, "measurementPoints")
            if measurement_points:
                return measurement_points
        return {}

    async def async_get_live_telemetry(self) -> IStoreSolarTelemetry:
        """Return normalized live telemetry for the first discovered site."""
        discovered_site = await self._async_discover_site()
        site_id = discovered_site.site_id
        battery_total_energy: dict[str, Any] = {}
        meter_total_energy: dict[str, dict[str, Any]] = {}

        try:
            overview_detail = await self.async_get_asset_detail(
                site_id,
                view="WebSiteDetailMonitorOverview",
            )
            site_live_detail = await self.async_get_asset_detail(
                site_id,
                attributes=SITE_LIVE_ATTRIBUTES,
                measurement_points=SITE_LIVE_MEASUREMENT_POINTS,
            )
        except IStoreSolarPermissionDeniedError as err:
            raise IStoreSolarUnsupportedResponseError(
                "Site discovery failed: asset detail request was denied",
                path=err.path,
                status=err.status,
                content_type=err.content_type,
                response_preview=err.response_preview,
                operation="asset detail retrieval",
            ) from err

        battery_asset = _first_asset_by_type(discovered_site.assets, "Res_Storage")
        battery_id = _asset_identifier(battery_asset)
        if battery_id is not None:
            try:
                battery_total_energy = await self.async_get_battery_total_energy(
                    battery_id
                )
            except IStoreSolarError as err:
                LOGGER.warning(
                    (
                        "iStore Solar optional battery cumulative request failed: "
                        "path=%s status=%s exception_type=%s"
                    ),
                    err.path or "unknown",
                    err.status if err.status is not None else "unknown",
                    type(err).__name__,
                )
        meter_asset = _first_asset_by_type(discovered_site.assets, "Res_Meter")
        if _asset_identifier(meter_asset) is not None:
            try:
                meter_total_energy = await self.async_get_meter_total_energy(site_id)
            except IStoreSolarError as err:
                LOGGER.warning(
                    (
                        "iStore Solar optional meter cumulative request failed: "
                        "path=%s status=%s exception_type=%s"
                    ),
                    err.path or "unknown",
                    err.status if err.status is not None else "unknown",
                    type(err).__name__,
                )

        return self._normalize_telemetry(
            site_id,
            overview_detail,
            site_live_detail,
            discovered_site.assets,
            battery_total_energy,
            meter_total_energy,
        )

    async def async_get_data(self) -> IStoreSolarTelemetry:
        """Return the latest normalized telemetry for Home Assistant."""
        return await self.async_get_live_telemetry()

    async def _async_discover_site(self) -> _DiscoveredSite:
        """Discover authorized site assets using the confirmed browser sequence."""
        if self._discovered_site is not None:
            return self._discovered_site

        await self.async_get_user_info()
        tree = await self._async_get_asset_tree()
        tree_diagnostics = _asset_tree_diagnostics(tree.payload)
        _log_asset_tree_diagnostics(tree, tree_diagnostics)

        candidates = _site_candidates_from_asset_tree(tree.payload)
        if not candidates:
            observed_types = ", ".join(tree_diagnostics.type_values) or "none"
            observed_resource_types = (
                ", ".join(tree_diagnostics.resource_type_values) or "none"
            )
            observed_mdm_types = ", ".join(tree_diagnostics.mdm_type_values) or "none"
            err = IStoreSolarUnsupportedResponseError(
                (
                    "could not discover a residential solar site from asset tree; "
                    f"observed type values: {observed_types}; "
                    f"resourceType values: {observed_resource_types}; "
                    f"mdmType values: {observed_mdm_types}"
                ),
                path=tree.path,
                status=tree.status,
                content_type=tree.content_type,
                response_preview=tree.response_preview,
                operation="asset discovery",
            )
            _raise_logged_api_exception(err)

        if len(candidates) == 1:
            LOGGER.debug(
                (
                    "iStore Solar selected asset-tree site candidate: "
                    "reason=exactly_one_confirmed_candidate path=%s "
                    "identifier_field=%s identifier_length=%d"
                ),
                candidates[0].path,
                candidates[0].identifier_field,
                len(candidates[0].identifier),
            )

        site_id = candidates[0].identifier
        _log_discovery_result(
            endpoint_name="asset/tree",
            asset_type_requested=ASSET_TREE_SITE_TYPE,
            identifier_source="asset-tree result",
            identifier=site_id,
            application_code=tree.application_code,
            assets=[candidate.node for candidate in candidates],
        )
        assets = await self.async_get_assets(site_id)
        self._discovered_site = _DiscoveredSite(site_id=site_id, assets=assets)
        return self._discovered_site

    async def _async_get_asset_tree(self) -> _ResponseContext:
        """Return the app-portal asset tree used by the browser before asset detail."""
        return await self._request(
            "POST",
            "/app-portal/web/v1/user/app/asset/tree",
            params={
                "appId": APP_ID,
                "needAssociateAsset": "true",
                "resourceTypes": "all",
                "_sid_": str(int(time.time() * 1000)),
            },
            raw_data="null",
            extra_headers={"Locale": self._locale},
            operation="asset discovery",
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json_data: Any = JSON_UNSET,
        raw_data: str | None = None,
        extra_headers: dict[str, str] | None = None,
        authenticated: bool = True,
        access_token: str | None = None,
        allow_relogin: bool = True,
        operation: str,
    ) -> _ResponseContext:
        """Send one API request and return the JSON object body."""
        token = access_token if access_token is not None else self._access_token
        if authenticated and not token:
            err = IStoreSolarAuthenticationError(
                "missing access token",
                path=path,
                operation=operation,
            )
            _raise_logged_api_exception(err)

        headers = {
            "Content-Type": "application/json",
            "locale": self._locale,
        }
        if authenticated:
            headers["Authorization"] = f"Bearer {token}"
        if extra_headers is not None:
            headers.update(extra_headers)

        LOGGER.debug("Starting iStore Solar setup-stage request: %s", operation)
        last_connection_error: IStoreSolarConnectionError | None = None
        for attempt in range(1, MAX_TEMPORARY_REQUEST_ATTEMPTS + 1):
            try:
                request_kwargs: dict[str, Any] = {
                    "headers": headers,
                    "params": params,
                    "timeout": REQUEST_TIMEOUT,
                }
                if raw_data is not None:
                    request_kwargs["data"] = raw_data
                elif json_data is not JSON_UNSET:
                    request_kwargs["json"] = json_data
                response = await self._session.request(
                    method,
                    f"{self._base_url}{path}",
                    **request_kwargs,
                )
                content_type = _sanitize_content_type(
                    response.headers.get("Content-Type")
                )
                response_text = await response.text()
                response_preview = _sanitize_response_preview(
                    response_text, content_type
                )
                if response.status in (401, 403):
                    raise IStoreSolarAuthenticationError(
                        "access token was rejected",
                        path=path,
                        status=response.status,
                        content_type=content_type,
                        response_preview=response_preview,
                        operation=operation,
                    )
                if response.status in TEMPORARY_HTTP_STATUSES and attempt == 1:
                    LOGGER.debug(
                        "Retrying temporary iStore Solar HTTP status: path=%s status=%s",
                        path,
                        response.status,
                    )
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                    continue
                if response.status >= 400:
                    raise IStoreSolarApiError(
                        "iStore Solar request failed",
                        path=path,
                        status=response.status,
                        content_type=content_type,
                        response_preview=response_preview,
                        operation=operation,
                    )
                try:
                    payload = json.loads(response_text)
                except ValueError as err:
                    raise IStoreSolarMalformedResponseError(
                        "response was not valid JSON",
                        path=path,
                        status=response.status,
                        content_type=content_type,
                        response_preview=response_preview,
                        operation=operation,
                    ) from err
                break
            except (AsyncTimeoutError, TimeoutError) as err:
                last_connection_error = IStoreSolarConnectionError(
                    "timed out connecting to iStore Solar",
                    path=path,
                    operation=operation,
                )
                if attempt == 1:
                    LOGGER.debug(
                        "Retrying temporary iStore Solar timeout: path=%s", path
                    )
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                    continue
                _log_api_exception(last_connection_error, err)
                raise last_connection_error from err
            except ClientError as err:
                last_connection_error = IStoreSolarConnectionError(
                    "could not connect to iStore Solar",
                    path=path,
                    operation=operation,
                )
                if attempt == 1:
                    LOGGER.debug(
                        "Retrying temporary iStore Solar client error: path=%s",
                        path,
                    )
                    await asyncio.sleep(RETRY_BACKOFF_SECONDS)
                    continue
                _log_api_exception(last_connection_error, err)
                raise last_connection_error from err
            except IStoreSolarError as err:
                _log_api_exception(err, err)
                if (
                    allow_relogin
                    and authenticated
                    and access_token is None
                    and isinstance(err, IStoreSolarAuthenticationError)
                    and self._auth_mode == AUTH_MODE_AUTOMATIC
                ):
                    try:
                        await self.async_refresh_access_token()
                    except IStoreSolarError as login_err:
                        self._last_auth_error_class = type(login_err).__name__
                        raise login_err from err
                    return await self._request(
                        method,
                        path,
                        params=params,
                        json_data=json_data,
                        raw_data=raw_data,
                        extra_headers=extra_headers,
                        authenticated=authenticated,
                        access_token=None,
                        allow_relogin=False,
                        operation=operation,
                    )
                raise
        else:
            assert last_connection_error is not None
            raise last_connection_error
        LOGGER.debug("Finished iStore Solar setup-stage request: %s", operation)

        if not isinstance(payload, dict):
            err = IStoreSolarMalformedResponseError(
                "response JSON was not an object",
                path=path,
                status=response.status,
                content_type=content_type,
                response_preview=response_preview,
                operation=operation,
            )
            try:
                raise err
            except IStoreSolarMalformedResponseError as raised:
                _log_api_exception(raised, raised)
                raise

        code = payload.get("code")
        if code not in (None, 0, 200, "0", "200"):
            if code in (401, 403, "401", "403"):
                err = IStoreSolarAuthenticationError(
                    "access token was rejected",
                    path=path,
                    status=response.status,
                    content_type=content_type,
                    response_preview=response_preview,
                    operation=operation,
                )
                if (
                    allow_relogin
                    and authenticated
                    and access_token is None
                    and self._auth_mode == AUTH_MODE_AUTOMATIC
                ):
                    try:
                        await self.async_refresh_access_token()
                    except IStoreSolarError as login_err:
                        self._last_auth_error_class = type(login_err).__name__
                        raise login_err from err
                    return await self._request(
                        method,
                        path,
                        params=params,
                        json_data=json_data,
                        raw_data=raw_data,
                        extra_headers=extra_headers,
                        authenticated=authenticated,
                        access_token=None,
                        allow_relogin=False,
                        operation=operation,
                    )
                try:
                    raise err
                except IStoreSolarAuthenticationError as raised:
                    _log_api_exception(raised, raised)
                    raise
            if (
                operation == "login"
                and code in (INVALID_CREDENTIALS_CODE, str(INVALID_CREDENTIALS_CODE))
            ):
                err = IStoreSolarAuthenticationError(
                    "iStore Solar credentials were rejected",
                    path=path,
                    status=response.status,
                    content_type=content_type,
                    response_preview=response_preview,
                    operation=operation,
                )
                try:
                    raise err
                except IStoreSolarAuthenticationError as raised:
                    _log_api_exception(raised, raised)
                    raise
            if code in (PERMISSION_DENIED_CODE, str(PERMISSION_DENIED_CODE)):
                err = IStoreSolarPermissionDeniedError(
                    "iStore Solar denied this request",
                    path=path,
                    status=response.status,
                    content_type=content_type,
                    response_preview=response_preview,
                    operation=operation,
                )
                try:
                    raise err
                except IStoreSolarPermissionDeniedError as raised:
                    _log_api_exception(raised, raised)
                    raise
            err = IStoreSolarApiError(
                "iStore Solar returned an error",
                path=path,
                status=response.status,
                content_type=content_type,
                response_preview=response_preview,
                operation=operation,
            )
            try:
                raise err
            except IStoreSolarApiError as raised:
                _log_api_exception(raised, raised)
                raise

        return _ResponseContext(
            payload=payload,
            path=path,
            status=response.status,
            content_type=content_type,
            response_preview=response_preview,
            application_code=code,
            auth_token_header=_auth_token_from_headers(response.headers),
        )

    def _normalize_telemetry(
        self,
        site_id: str,
        overview_detail: dict[str, Any],
        site_live_detail: dict[str, Any],
        assets: list[dict[str, Any]],
        battery_total_energy: dict[str, Any] | None = None,
        meter_total_energy: dict[str, dict[str, Any]] | None = None,
    ) -> IStoreSolarTelemetry:
        """Normalize API responses into Home Assistant entity data."""
        battery_total_energy = battery_total_energy or {}
        meter_total_energy = meter_total_energy or {}
        overview_item = _detail_item(overview_detail, site_id)
        site_live_item = _detail_item(site_live_detail, site_id)

        site_attrs = _dict_value(overview_item, "attributes")
        site_name = _string_value(site_attrs.get("name")) or "iStore Solar Site"
        site_device = IStoreSolarDevice(
            identifiers=(DOMAIN, site_id),
            name=site_name,
            model=_string_value(site_attrs.get("modelName")),
            manufacturer=MANUFACTURER,
        )

        devices = _devices_from_assets(assets, site_device.identifiers)
        measurement_points = _dict_value(site_live_item, "measurementPoints")
        overview_points = _dict_value(overview_item, "measurementPoints")
        overview_metrics = _dict_value(overview_item, "metrics")
        grid_power = _first_point_value(
            measurement_points,
            ("PUB_SITE.METERActivePW", "METER.ActivePW"),
        )
        battery_power = _first_point_value(
            measurement_points,
            ("PUB_SITE.BSActivePW", "BS.ActivePW"),
        )

        values: dict[str, IStoreSolarSensorValue] = {
            SENSOR_SOLAR_POWER: IStoreSolarSensorValue(
                _first_point_value(
                    measurement_points,
                    ("PUB_SITE.PVOutputPower", "SITE.GenActivePW"),
                )
            ),
            SENSOR_HOME_CONSUMPTION_POWER: IStoreSolarSensorValue(
                _first_point_value(measurement_points, ("ConsPower",))
            ),
            SENSOR_GRID_POWER: IStoreSolarSensorValue(grid_power),
            SENSOR_GRID_IMPORT_POWER: IStoreSolarSensorValue(positive_power(grid_power)),
            SENSOR_GRID_EXPORT_POWER: IStoreSolarSensorValue(
                inverted_positive_power(grid_power)
            ),
            SENSOR_BATTERY_POWER: IStoreSolarSensorValue(battery_power),
            SENSOR_BATTERY_CHARGING_POWER: IStoreSolarSensorValue(
                positive_power(battery_power)
            ),
            SENSOR_BATTERY_DISCHARGING_POWER: IStoreSolarSensorValue(
                inverted_positive_power(battery_power)
            ),
            SENSOR_BATTERY_SOC: IStoreSolarSensorValue(
                _first_point_value(measurement_points, ("PUB_SITE.Soc", "BS.Soc"))
            ),
            SENSOR_SITE_STATUS: IStoreSolarSensorValue(
                _first_point_value(overview_points, ("OperatingStatus", "OperationState"))
            ),
        }

        inverter_asset = _first_asset_by_type(assets, "Res_Inverter")
        battery_asset = _first_asset_by_type(assets, "Res_Storage")
        meter_asset = _first_asset_by_type(assets, "Res_Meter")

        inverter_points = _dict_value(inverter_asset, "measurementPoints")
        battery_points = _dict_value(battery_asset, "measurementPoints")
        meter_points = _dict_value(meter_asset, "measurementPoints")
        cumulative_observations: dict[str, CumulativeFieldObservation] = {}
        selected_solar_source = _selected_solar_production_source(overview_metrics)

        values[SENSOR_INVERTER_STATUS] = IStoreSolarSensorValue(
            _first_point_value(inverter_points, ("INV.State", "DeviceState"))
        )
        values[SENSOR_BATTERY_STATUS] = IStoreSolarSensorValue(
            _first_point_value(battery_points, ("BS.State", "DeviceState"))
        )
        values[SENSOR_BATTERY_CHARGED_TODAY] = IStoreSolarSensorValue(
            _first_point_value(battery_points, ("BS.ChargingEngDay",))
        )
        values[SENSOR_BATTERY_DISCHARGED_TODAY] = IStoreSolarSensorValue(
            _first_point_value(battery_points, ("BS.DischargingEngDay",))
        )

        values[SENSOR_TOTAL_SOLAR_PRODUCTION] = IStoreSolarSensorValue(
            self._cumulative_value_from_metric(
                cumulative_observations,
                selected_solar_source,
                overview_metrics,
                SENSOR_TOTAL_SOLAR_PRODUCTION,
            )
            if selected_solar_source is not None
            else None
        )
        if selected_solar_source is not None:
            LOGGER.debug(
                "iStore Solar selected cumulative solar source field=%s",
                selected_solar_source,
            )
        else:
            _mark_missing(
                cumulative_observations,
                SENSOR_TOTAL_SOLAR_PRODUCTION,
                ("TotalActiveProduction:BOL", "ActiveProduction:BOL"),
            )

        meter_has_valid_energy = False
        grid_import_value = _daily_energy_value_from_point(
            "METER.APConsumed",
            meter_points,
            SENSOR_GRID_ENERGY_IMPORTED_TODAY,
        )
        if grid_import_value is not None:
            meter_has_valid_energy = True
        values[SENSOR_GRID_ENERGY_IMPORTED_TODAY] = IStoreSolarSensorValue(
            grid_import_value
        )

        grid_export_value = _daily_energy_value_from_point(
            "METER.APProduction",
            meter_points,
            SENSOR_GRID_ENERGY_EXPORTED_TODAY,
        )
        if grid_export_value is not None:
            meter_has_valid_energy = True
        values[SENSOR_GRID_ENERGY_EXPORTED_TODAY] = IStoreSolarSensorValue(
            grid_export_value
        )

        grid_total_import_value = self._cumulative_value_from_point(
            cumulative_observations,
            "METER.APConsumedKWH",
            meter_total_energy,
            SENSOR_TOTAL_GRID_IMPORTED_ENERGY,
        )
        if grid_total_import_value is not None:
            meter_has_valid_energy = True
        values[SENSOR_TOTAL_GRID_IMPORTED_ENERGY] = IStoreSolarSensorValue(
            grid_total_import_value
        )

        grid_total_export_value = self._cumulative_value_from_point(
            cumulative_observations,
            "METER.APProductionKWH",
            meter_total_energy,
            SENSOR_TOTAL_GRID_EXPORTED_ENERGY,
        )
        if grid_total_export_value is not None:
            meter_has_valid_energy = True
        values[SENSOR_TOTAL_GRID_EXPORTED_ENERGY] = IStoreSolarSensorValue(
            grid_total_export_value
        )

        if not meter_has_valid_energy:
            devices.pop("meter", None)

        values[SENSOR_TOTAL_BATTERY_CHARGED_ENERGY] = IStoreSolarSensorValue(
            self._cumulative_value_from_raw(
                cumulative_observations,
                "BS.TotalChargingEng",
                battery_total_energy.get("BS.TotalChargingEng"),
                SENSOR_TOTAL_BATTERY_CHARGED_ENERGY,
            )
        )
        values[SENSOR_TOTAL_BATTERY_DISCHARGED_ENERGY] = IStoreSolarSensorValue(
            self._cumulative_value_from_raw(
                cumulative_observations,
                "BS.TotalDischargingEng",
                battery_total_energy.get("BS.TotalDischargingEng"),
                SENSOR_TOTAL_BATTERY_DISCHARGED_ENERGY,
            )
        )

        return IStoreSolarTelemetry(
            site=site_device,
            devices=devices,
            values=values,
            discovered_asset_types=tuple(
                sorted(
                    {
                        asset_type
                        for asset in assets
                        if (asset_type := _asset_type(asset)) is not None
                    }
                )
            ),
            cumulative_observations=cumulative_observations,
            selected_solar_production_source=selected_solar_source,
            meter_asset_discovered=bool(meter_asset),
        )

    def _cumulative_value_from_metric(
        self,
        observations: dict[str, CumulativeFieldObservation],
        source_field: str,
        metrics: dict[str, Any],
        sensor_key: str,
    ) -> float | int | None:
        """Extract a cumulative value from a metric object."""
        metric = _dict_value(metrics, source_field)
        return self._cumulative_value_from_raw(
            observations,
            source_field,
            metric.get("value") if metric else None,
            sensor_key,
        )

    def _cumulative_value_from_point(
        self,
        observations: dict[str, CumulativeFieldObservation],
        source_field: str,
        points: dict[str, Any],
        sensor_key: str,
    ) -> float | int | None:
        """Extract a cumulative value from a measurement-point object."""
        point = _dict_value(points, source_field)
        return self._cumulative_value_from_raw(
            observations,
            source_field,
            point.get("value") if point else None,
            sensor_key,
        )

    def _cumulative_value_from_raw(
        self,
        observations: dict[str, CumulativeFieldObservation],
        source_field: str,
        raw_value: Any,
        sensor_key: str,
    ) -> float | int | None:
        """Normalize and observe one cumulative counter source."""
        value = observe_cumulative_value(
            observations,
            self._previous_cumulative_values,
            self._cumulative_decreases,
            sensor_key,
            raw_value,
        )
        observation = observations[sensor_key]
        if observation.missing:
            LOGGER.debug(
                "iStore Solar cumulative field missing: field=%s sensor=%s type=%s",
                source_field,
                sensor_key,
                observation.value_type,
            )
            return None
        if observation.malformed:
            LOGGER.debug(
                "iStore Solar cumulative field malformed: field=%s sensor=%s type=%s",
                source_field,
                sensor_key,
                observation.value_type,
            )
            return None
        if observation.decreased:
            LOGGER.warning(
                "iStore Solar cumulative counter decreased: field=%s sensor=%s type=%s",
                source_field,
                sensor_key,
                observation.value_type,
            )
        LOGGER.debug(
            "iStore Solar cumulative field detected: field=%s sensor=%s type=%s",
            source_field,
            sensor_key,
            observation.value_type,
        )
        return value


def _site_candidates_from_asset_tree(
    payload: dict[str, Any],
) -> list[_AssetTreeCandidate]:
    """Return confirmed residential site candidates from asset-tree data."""
    candidates: list[_AssetTreeCandidate] = []
    for path, node in _asset_tree_nodes(payload):
        if (
            node.get("tag") != "asset"
            or _string_value(node.get("type")) != ASSET_TREE_SITE_TYPE
        ):
            continue
        identifier = _asset_tree_identifier(node)
        if identifier is None:
            continue
        identifier_field, identifier_value = identifier
        candidates.append(
            _AssetTreeCandidate(
                identifier=identifier_value,
                identifier_field=identifier_field,
                path=path,
                node=node,
            )
        )
    return candidates


def _asset_tree_nodes(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Return primary and associated asset-tree nodes with sanitized paths."""
    data = payload.get("data")
    root_nodes: list[tuple[str, dict[str, Any]]] = []
    if isinstance(data, dict):
        root_nodes.append(("data", data))
    elif isinstance(data, list):
        root_nodes.extend(
            (f"data[{index}]", item)
            for index, item in enumerate(data)
            if isinstance(item, dict)
        )
    return _walk_asset_tree_nodes(root_nodes)


def _walk_asset_tree_nodes(
    pending: list[tuple[str, dict[str, Any]]],
) -> list[tuple[str, dict[str, Any]]]:
    """Walk confirmed asset-tree child containers."""
    nodes: list[tuple[str, dict[str, Any]]] = []
    stack = list(reversed(pending))
    while stack:
        path, node = stack.pop()
        nodes.append((path, node))
        for child_key in (
            "children",
            "associatedResources",
            "associatedAssets",
            "associatedAsset",
            "assets",
        ):
            children = node.get(child_key)
            if isinstance(children, list):
                for index, child in reversed(list(enumerate(children))):
                    if isinstance(child, dict):
                        stack.append((f"{path}.{child_key}[{index}]", child))
            elif isinstance(children, dict):
                stack.append((f"{path}.{child_key}", children))
    return nodes


def _asset_tree_identifier(node: dict[str, Any]) -> tuple[str, str] | None:
    """Return the confirmed site identifier field and value from a tree node."""
    for field_name in ("id", "assetId", "mdmId", "resourceId", "uri", "nodeId"):
        value = _string_value(node.get(field_name))
        if value is not None:
            return field_name, value
    return None


def _asset_tree_diagnostics(payload: dict[str, Any]) -> _AssetTreeDiagnostics:
    """Build sanitized asset-tree diagnostics."""
    nodes_with_paths = _asset_tree_nodes(payload)
    nodes = [node for _, node in nodes_with_paths]
    candidates = _site_candidates_from_asset_tree(payload)
    candidate_nodes = [candidate.node for candidate in candidates]
    identifier_pairs = [
        identifier
        for node in nodes
        if (identifier := _asset_tree_identifier(node)) is not None
    ]

    return _AssetTreeDiagnostics(
        top_level_keys=tuple(sorted(str(key) for key in payload)),
        root_node_count=_asset_tree_root_node_count(payload),
        recursive_node_count=len(nodes),
        type_values=_distinct_string_values(nodes, "type"),
        resource_type_values=_distinct_string_values(nodes, "resourceType"),
        mdm_type_values=_distinct_string_values(nodes, "mdmType"),
        candidate_field_names=tuple(
            sorted({str(key) for node in candidate_nodes for key in node})
        ),
        identifier_fields=tuple(sorted({field for field, _ in identifier_pairs})),
        identifier_lengths=tuple(
            sorted({len(value) for _, value in identifier_pairs})
        ),
        has_children_arrays=any(
            isinstance(node.get("children"), list) for node in nodes
        ),
        has_associated_resources_arrays=any(
            isinstance(node.get(key), list)
            for node in nodes
            for key in (
                "associatedResources",
                "associatedAssets",
                "associatedAsset",
                "assets",
            )
        ),
    )


def _asset_tree_root_node_count(payload: dict[str, Any]) -> int:
    """Return the number of root nodes in the asset-tree wrapper."""
    data = payload.get("data")
    if isinstance(data, dict):
        return 1
    if isinstance(data, list):
        return sum(1 for item in data if isinstance(item, dict))
    return 0


def _distinct_string_values(
    nodes: list[dict[str, Any]],
    field_name: str,
) -> tuple[str, ...]:
    """Return sanitized distinct string values for a field."""
    values = {
        value
        for node in nodes
        if (value := _string_value(node.get(field_name))) is not None
    }
    return tuple(sorted(values))


def _detail_item(detail: dict[str, Any], preferred_id: str) -> dict[str, Any]:
    """Return the preferred detail item or the first object item."""
    item = detail.get(preferred_id)
    if isinstance(item, dict):
        return item
    for value in detail.values():
        if isinstance(value, dict):
            return value
    return {}


def _selected_solar_production_source(metrics: dict[str, Any]) -> str | None:
    """Return the preferred available solar production total field."""
    for field_name in ("TotalActiveProduction:BOL", "ActiveProduction:BOL"):
        metric = metrics.get(field_name)
        if isinstance(metric, dict) and metric.get("value") is not None:
            return field_name
    return None


def _mark_missing(
    observations: dict[str, CumulativeFieldObservation],
    sensor_key: str,
    source_fields: tuple[str, ...],
) -> None:
    """Mark an optional cumulative source as missing."""
    observation = observations.setdefault(sensor_key, CumulativeFieldObservation())
    observation.missing = True
    LOGGER.debug(
        "iStore Solar cumulative fields missing: fields=%s sensor=%s",
        ",".join(source_fields),
        sensor_key,
    )


def _daily_energy_value_from_point(
    source_field: str,
    points: dict[str, Any],
    sensor_key: str,
) -> float | int | None:
    """Extract an optional non-negative daily energy value."""
    point = _dict_value(points, source_field)
    if not point:
        LOGGER.debug(
            "iStore Solar daily energy field missing: field=%s sensor=%s",
            source_field,
            sensor_key,
        )
        return None
    value = cumulative_native_value(point.get("value"))
    if value is None:
        LOGGER.debug(
            "iStore Solar daily energy field malformed: field=%s sensor=%s type=%s",
            source_field,
            sensor_key,
            value_type_name(point.get("value")),
        )
    return value


def _devices_from_assets(
    assets: list[dict[str, Any]],
    site_identifier: tuple[str, str],
) -> dict[str, IStoreSolarDevice]:
    """Build normalized device information from asset-list rows."""
    devices: dict[str, IStoreSolarDevice] = {}
    for asset in assets:
        attrs = _dict_value(asset, "attributes")
        mdm_type = _string_value(asset.get("mdmType")) or _string_value(
            attrs.get("mdmType")
        )
        mdm_id = _asset_identifier(asset)
        if mdm_type is None or mdm_id is None:
            continue

        key = _device_key_for_type(mdm_type)
        if key is None or key in devices:
            continue

        name = _string_value(attrs.get("name")) or f"iStore Solar {key.title()}"
        model = _string_value(attrs.get("modelName"))
        devices[key] = IStoreSolarDevice(
            identifiers=(DOMAIN, mdm_id),
            name=name,
            model=model,
            manufacturer=MANUFACTURER,
            via_device=site_identifier,
            serial_number=_serial_number_from_attrs(attrs),
            sw_version=_string_value(attrs.get("version"))
            or _string_value(attrs.get("rack1Version")),
        )

    return devices


def _asset_identifier(asset: dict[str, Any]) -> str | None:
    """Return the stable MDM identifier from an asset-list row."""
    attrs = _dict_value(asset, "attributes")
    return _string_value(asset.get("mdmId")) or _string_value(attrs.get("mdmId"))


def _serial_number_from_attrs(attrs: dict[str, Any]) -> str | None:
    """Return the confirmed serial-number style field for device metadata."""
    for field_name in ("sn", "rack1SN", "rack1PackSN"):
        if serial_number := _string_value(attrs.get(field_name)):
            return serial_number
    return None


def _device_key_for_type(mdm_type: str) -> str | None:
    """Map iStore MDM types to integration device keys."""
    return {
        "Res_Inverter": "inverter",
        "Res_Storage": "battery",
        "Res_Meter": "meter",
        "Dongle": "dongle",
    }.get(mdm_type)


def _first_asset_by_type(assets: list[dict[str, Any]], mdm_type: str) -> dict[str, Any]:
    """Return the first asset matching an MDM type."""
    for asset in assets:
        attrs = _dict_value(asset, "attributes")
        if asset.get("mdmType") == mdm_type or attrs.get("mdmType") == mdm_type:
            return asset
    return {}


def _asset_type(asset: dict[str, Any]) -> str | None:
    """Return a normalized asset type from common tree/list fields."""
    attrs = _dict_value(asset, "attributes")
    return (
        _string_value(asset.get("mdmType"))
        or _string_value(attrs.get("mdmType"))
        or _string_value(asset.get("assetType"))
        or _string_value(asset.get("resourceType"))
        or _string_value(asset.get("type"))
    )


def _first_point_value(
    measurement_points: dict[str, Any],
    field_names: tuple[str, ...],
) -> float | int | str | None:
    """Return the first available measurement point value."""
    for field_name in field_names:
        point = measurement_points.get(field_name)
        if isinstance(point, dict):
            return _coerce_native_value(point.get("value"))
    return None


def _coerce_native_value(value: Any) -> float | int | str | None:
    """Return a Home Assistant friendly native value."""
    if value is None or isinstance(value, (int, float, str)):
        return value
    return str(value)


def _dict_value(value: dict[str, Any], key: str) -> dict[str, Any]:
    """Return a nested dict value if present."""
    item = value.get(key)
    return item if isinstance(item, dict) else {}


def _string_value(value: Any) -> str | None:
    """Return a stripped string value if present."""
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _log_api_exception(err: IStoreSolarError, exc_info: BaseException) -> None:
    """Log sanitized API exception diagnostics."""
    LOGGER.warning(
        (
            "iStore Solar API exception during %s: path=%s status=%s "
            "content_type=%s response_preview=%s exception_type=%s"
        ),
        err.operation or "unknown operation",
        err.path or "unknown",
        err.status if err.status is not None else "unknown",
        err.content_type or "unknown",
        err.response_preview or "unavailable",
        type(err).__name__,
    )
    LOGGER.debug(
        "iStore Solar API exception traceback",
        exc_info=(type(exc_info), exc_info, exc_info.__traceback__),
    )


def _log_discovery_result(
    *,
    endpoint_name: str,
    asset_type_requested: str,
    identifier_source: str,
    identifier: str,
    application_code: int | str | None,
    assets: list[dict[str, Any]],
) -> None:
    """Log sanitized discovery progress without exposing identifiers or payloads."""
    asset_types = sorted(
        {
            asset_type
            for asset in assets
            if (asset_type := _asset_type(asset)) is not None
        }
    )
    LOGGER.debug(
        (
            "iStore Solar discovery endpoint=%s asset_type_requested=%s "
            "identifier_source=%s identifier_length=%d application_code=%s "
            "asset_count=%d asset_types=%s"
        ),
        endpoint_name,
        asset_type_requested,
        identifier_source,
        len(identifier),
        application_code if application_code is not None else "unknown",
        len(assets),
        ",".join(asset_types) if asset_types else "none",
    )


def _log_asset_tree_diagnostics(
    response: _ResponseContext,
    diagnostics: _AssetTreeDiagnostics,
) -> None:
    """Log sanitized asset-tree response diagnostics."""
    message = response.payload.get("message")
    if message is None:
        message = response.payload.get("msg")
    LOGGER.debug(
        (
            "iStore Solar asset-tree diagnostics: http_status=%s "
            "application_code=%s application_message=%s top_level_keys=%s "
            "root_node_count=%d recursive_node_count=%d type_values=%s "
            "resource_type_values=%s mdm_type_values=%s "
            "candidate_field_names=%s identifier_fields=%s "
            "identifier_value_lengths=%s has_children_arrays=%s "
            "has_associated_resources_arrays=%s"
        ),
        response.status,
        (
            response.application_code
            if response.application_code is not None
            else "unknown"
        ),
        _sanitize_application_message(message),
        ",".join(diagnostics.top_level_keys) or "none",
        diagnostics.root_node_count,
        diagnostics.recursive_node_count,
        ",".join(diagnostics.type_values) or "none",
        ",".join(diagnostics.resource_type_values) or "none",
        ",".join(diagnostics.mdm_type_values) or "none",
        ",".join(diagnostics.candidate_field_names) or "none",
        ",".join(diagnostics.identifier_fields) or "none",
        ",".join(str(length) for length in diagnostics.identifier_lengths) or "none",
        diagnostics.has_children_arrays,
        diagnostics.has_associated_resources_arrays,
    )


def _sanitize_application_message(value: Any) -> str:
    """Return a sanitized application message for diagnostics."""
    if not isinstance(value, str) or not value.strip():
        return "empty"
    return _sanitize_text(value)


def _extract_login_token(
    payload: dict[str, Any],
    auth_token_header: str | None = None,
) -> str | None:
    """Extract a token-like value from the confirmed login response family."""
    candidates: list[str] = []

    def walk(value: Any, key: str = "") -> None:
        if isinstance(value, dict):
            for child_key, child_value in value.items():
                walk(child_value, child_key)
        elif (
            isinstance(value, str)
            and key in LOGIN_TOKEN_KEYS
            and len(value) >= SESSION_TOKEN_MIN_LENGTH
        ):
            candidates.append(value)

    walk(payload)
    if auth_token_header is not None:
        candidates.append(auth_token_header)
    return candidates[0] if candidates else None


def _auth_token_from_headers(headers: Any) -> str | None:
    """Extract an internal token candidate from response headers."""
    for name in ("Authorization", "access-token", "x-access-token"):
        value = headers.get(name)
        if not isinstance(value, str):
            continue
        token = value.removeprefix("Bearer ").strip()
        if len(token) >= SESSION_TOKEN_MIN_LENGTH:
            return token
    return None


def _extract_login_org_id(payload: dict[str, Any]) -> str | None:
    """Extract an organization ID from login-shaped response data."""
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    for key in ("orgId", "organizationId"):
        value = _string_value(data.get(key))
        if value is not None:
            return value

    working_org = _dict_value(data, "workingOrganization")
    value = _string_value(working_org.get("id"))
    if value is not None:
        return value

    user = _dict_value(data, "user")
    return _string_value(user.get("orgId"))


def _safe_session_metadata(value: Any) -> int | str | None:
    """Return session metadata only when it is a scalar safe for storage."""
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value:
        return value
    return None


def _raise_logged_api_exception(err: IStoreSolarError) -> NoReturn:
    """Raise an API exception after logging it with traceback context."""
    try:
        raise err
    except IStoreSolarError as raised:
        _log_api_exception(raised, raised)
        raise
