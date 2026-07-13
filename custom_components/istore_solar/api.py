"""API models and client for iStore Solar."""

from __future__ import annotations

from asyncio import TimeoutError as AsyncTimeoutError
from collections.abc import Iterable
from dataclasses import dataclass, field
import json
import logging
import re
from typing import Any, Final, NoReturn

from aiohttp import ClientError, ClientSession, ClientTimeout

from .const import (
    API_BASE_URL,
    DEFAULT_LOCALE,
    DOMAIN,
    MANUFACTURER,
    SENSOR_BATTERY_CHARGED_TODAY,
    SENSOR_BATTERY_DISCHARGED_TODAY,
    SENSOR_BATTERY_POWER,
    SENSOR_BATTERY_SOC,
    SENSOR_BATTERY_STATUS,
    SENSOR_GRID_POWER,
    SENSOR_HOME_CONSUMPTION_POWER,
    SENSOR_INVERTER_STATUS,
    SENSOR_SITE_STATUS,
    SENSOR_SOLAR_POWER,
)

REDACTED: Final = "**REDACTED**"
REQUEST_TIMEOUT: Final = ClientTimeout(total=20)
LOGGER = logging.getLogger(__name__)
MAX_RESPONSE_PREVIEW_LENGTH: Final = 240

SENSITIVE_KEYS: Final[tuple[str, ...]] = (
    "account",
    "address",
    "authorization",
    "cookie",
    "customer",
    "device",
    "email",
    "id",
    "latitude",
    "longitude",
    "mdm",
    "name",
    "nmi",
    "owner",
    "password",
    "phone",
    "serial",
    "session",
    "sid",
    "sn",
    "token",
    "uri",
    "user",
)

SENSITIVE_VALUE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"Bearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE),
    re.compile(r"(?i)(authorization|cookie|password|token|sid)=([^&\s]+)"),
    re.compile(r"\b[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{24,}\b"),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b"),
)

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


@dataclass(slots=True, frozen=True)
class _ResponseContext:
    """Sanitized response context for downstream schema validation."""

    payload: dict[str, Any]
    path: str
    status: int
    content_type: str | None
    response_preview: str | None


@dataclass(slots=True, frozen=True)
class IStoreSolarDevice:
    """A normalized iStore Solar device."""

    identifiers: tuple[str, str]
    name: str
    model: str | None = None
    manufacturer: str | None = None
    via_device: tuple[str, str] | None = None


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


class IStoreSolarApiClient:
    """Async client for the experimental iStore Solar cloud API."""

    def __init__(
        self,
        session: ClientSession,
        *,
        access_token: str,
        base_url: str = API_BASE_URL,
        locale: str = DEFAULT_LOCALE,
    ) -> None:
        """Initialize the API client."""
        self._session = session
        self._access_token = access_token.strip()
        self._base_url = base_url.rstrip("/")
        self._locale = locale
        self._user_info: dict[str, Any] | None = None
        self._site_id: str | None = None

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
        return [item for item in data if isinstance(item, dict)]

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

    async def async_get_live_telemetry(self) -> IStoreSolarTelemetry:
        """Return normalized live telemetry for the first discovered site."""
        user_info = self._user_info or await self.async_get_user_info()
        site_id = self._site_id or await self._async_discover_site_id(user_info)
        self._site_id = site_id

        overview_detail = await self.async_get_asset_detail(
            site_id,
            view="WebSiteDetailMonitorOverview",
        )
        site_live_detail = await self.async_get_asset_detail(
            site_id,
            attributes=SITE_LIVE_ATTRIBUTES,
            measurement_points=SITE_LIVE_MEASUREMENT_POINTS,
        )
        assets = await self.async_get_assets(site_id)

        return self._normalize_telemetry(site_id, overview_detail, site_live_detail, assets)

    async def async_get_data(self) -> IStoreSolarTelemetry:
        """Return the latest normalized telemetry for Home Assistant."""
        return await self.async_get_live_telemetry()

    async def _async_discover_site_id(self, user_info: dict[str, Any]) -> str:
        """Discover the first site ID exposed by the current token."""
        candidates = list(_site_id_candidates(user_info))
        if not candidates:
            err = IStoreSolarUnsupportedResponseError(
                "user-info response did not expose a site candidate",
                operation="asset discovery",
            )
            _raise_logged_api_exception(err)

        for candidate in candidates:
            try:
                detail = await self.async_get_asset_detail(
                    candidate,
                    view="WebSiteDetailMonitorOverview",
                )
            except IStoreSolarAuthenticationError:
                raise
            except IStoreSolarError:
                continue

            site_id = _first_site_id_from_detail(detail)
            if site_id is not None:
                return site_id

        err = IStoreSolarUnsupportedResponseError(
            "could not discover a residential solar site from this token",
            operation="asset discovery",
        )
        _raise_logged_api_exception(err)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_data: dict[str, Any] | list[Any] | None = None,
        operation: str,
    ) -> _ResponseContext:
        """Send one authenticated request and return the JSON object body."""
        if not self._access_token:
            err = IStoreSolarAuthenticationError(
                "missing access token",
                path=path,
                operation=operation,
            )
            _raise_logged_api_exception(err)

        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "locale": self._locale,
        }

        LOGGER.debug("Starting iStore Solar setup-stage request: %s", operation)
        try:
            response = await self._session.request(
                method,
                f"{self._base_url}{path}",
                headers=headers,
                json=json_data,
                timeout=REQUEST_TIMEOUT,
            )
            content_type = _sanitize_content_type(response.headers.get("Content-Type"))
            response_text = await response.text()
            response_preview = _sanitize_response_preview(response_text, content_type)
            if response.status in (401, 403):
                raise IStoreSolarAuthenticationError(
                    "access token was rejected",
                    path=path,
                    status=response.status,
                    content_type=content_type,
                    response_preview=response_preview,
                    operation=operation,
                )
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
        except (AsyncTimeoutError, TimeoutError) as err:
            error = IStoreSolarConnectionError(
                "timed out connecting to iStore Solar",
                path=path,
                operation=operation,
            )
            _log_api_exception(error, err)
            raise error from err
        except ClientError as err:
            error = IStoreSolarConnectionError(
                "could not connect to iStore Solar",
                path=path,
                operation=operation,
            )
            _log_api_exception(error, err)
            raise error from err
        except IStoreSolarError as err:
            _log_api_exception(err, err)
            raise
        finally:
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
                try:
                    raise err
                except IStoreSolarAuthenticationError as raised:
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
        )

    def _normalize_telemetry(
        self,
        site_id: str,
        overview_detail: dict[str, Any],
        site_live_detail: dict[str, Any],
        assets: list[dict[str, Any]],
    ) -> IStoreSolarTelemetry:
        """Normalize API responses into Home Assistant entity data."""
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
            SENSOR_GRID_POWER: IStoreSolarSensorValue(
                _first_point_value(
                    measurement_points,
                    ("PUB_SITE.METERActivePW", "METER.ActivePW"),
                )
            ),
            SENSOR_BATTERY_POWER: IStoreSolarSensorValue(
                _first_point_value(
                    measurement_points,
                    ("PUB_SITE.BSActivePW", "BS.ActivePW"),
                )
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

        inverter_points = _dict_value(inverter_asset, "measurementPoints")
        battery_points = _dict_value(battery_asset, "measurementPoints")

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

        return IStoreSolarTelemetry(site=site_device, devices=devices, values=values)


def _site_id_candidates(user_info: dict[str, Any]) -> Iterable[str]:
    """Yield opaque site candidates from user-info without exposing them."""
    seen: set[str] = set()
    uri = _string_value(user_info.get("uri"))
    if uri:
        segments = [segment for segment in uri.split("/") if segment]
        for segment in reversed(segments):
            if segment not in seen:
                seen.add(segment)
                yield segment


def _first_site_id_from_detail(detail: dict[str, Any]) -> str | None:
    """Return the first residential solar site identifier in a detail response."""
    for mdm_id, item in detail.items():
        if not isinstance(item, dict):
            continue
        attrs = _dict_value(item, "attributes")
        mdm_type = _string_value(attrs.get("mdmType"))
        if mdm_type in (None, "Res_Solar_Site"):
            attr_id = _string_value(attrs.get("mdmId"))
            return attr_id or str(mdm_id)
    return None


def _detail_item(detail: dict[str, Any], preferred_id: str) -> dict[str, Any]:
    """Return the preferred detail item or the first object item."""
    item = detail.get(preferred_id)
    if isinstance(item, dict):
        return item
    for value in detail.values():
        if isinstance(value, dict):
            return value
    return {}


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
        mdm_id = _string_value(asset.get("mdmId")) or _string_value(attrs.get("mdmId"))
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
        )

    return devices


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


def redact_sensitive_data(value: Any) -> Any:
    """Return a recursively redacted copy of diagnostic data."""
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(sensitive in lowered for sensitive in SENSITIVE_KEYS):
                redacted[key] = REDACTED
            else:
                redacted[key] = redact_sensitive_data(item)
        return redacted

    if isinstance(value, list):
        return [redact_sensitive_data(item) for item in value]

    if isinstance(value, tuple):
        return tuple(redact_sensitive_data(item) for item in value)

    return value


def _sanitize_content_type(content_type: str | None) -> str | None:
    """Return a safe response content type without parameters."""
    if content_type is None:
        return None
    media_type = content_type.split(";", 1)[0].strip().lower()
    return _sanitize_text(media_type) if media_type else None


def _sanitize_response_preview(text: str, content_type: str | None) -> str | None:
    """Return a short sanitized response preview when it is safe enough."""
    if not text:
        return None

    preview_value: Any = text
    if content_type is not None and "json" in content_type:
        try:
            preview_value = redact_sensitive_data(json.loads(text))
        except ValueError:
            preview_value = text

    if isinstance(preview_value, str):
        preview_text = preview_value
    else:
        preview_text = json.dumps(preview_value, sort_keys=True)
    preview = _sanitize_text(preview_text)
    if not preview:
        return None
    return preview[:MAX_RESPONSE_PREVIEW_LENGTH]


def _sanitize_text(value: str) -> str:
    """Remove token-looking and identifier-looking values from diagnostic text."""
    sanitized = " ".join(value.split())
    for pattern in SENSITIVE_VALUE_PATTERNS:
        sanitized = pattern.sub(REDACTED, sanitized)
    return sanitized


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


def _raise_logged_api_exception(err: IStoreSolarError) -> NoReturn:
    """Raise an API exception after logging it with traceback context."""
    try:
        raise err
    except IStoreSolarError as raised:
        _log_api_exception(raised, raised)
        raise
