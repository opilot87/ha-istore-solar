"""Constants for the iStore Solar integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "istore_solar"
INTEGRATION_VERSION = "0.6.0"
DEFAULT_NAME = "iStore Solar"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)
DEFAULT_SCAN_INTERVAL_SECONDS = 30
MIN_SCAN_INTERVAL_SECONDS = 15
MAX_SCAN_INTERVAL_SECONDS = 300

CONF_EMAIL = "email"
CONF_ACCOUNT = "account"
CONF_PASSWORD = "password"
CONF_ACCESS_TOKEN = "access_token"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_AUTH_MODE = "auth_mode"
CONF_TOKEN_EXPIRES = "token_expires"
CONF_TOKEN_CREATE_TIME = "token_create_time"
CONF_TOKEN_REFRESH_TIME = "token_refresh_time"
CONF_LATEST_LOGIN_SUCCESS = "latest_login_success"
CONF_AUTOMATIC_RELOGIN_COUNT = "automatic_relogin_count"
CONF_LAST_AUTH_ERROR_CLASS = "last_auth_error_class"

AUTH_MODE_AUTOMATIC = "automatic"
AUTH_MODE_MANUAL_TOKEN = "manual_token"

ATTRIBUTION = "Data provided by the iStore Solar cloud portal"
MANUFACTURER = "iStore"

API_HOST = "home.istore.net.au"
API_BASE_URL = f"https://{API_HOST}"
APP_ID = "6508dd96-c72f-4c75-85d3-11c6e1380f75"
DEFAULT_LOCALE = "en-US"

SENSOR_SOLAR_POWER = "solar_power"
SENSOR_HOME_CONSUMPTION_POWER = "home_consumption_power"
SENSOR_GRID_POWER = "grid_power"
SENSOR_GRID_IMPORT_POWER = "grid_import_power"
SENSOR_GRID_EXPORT_POWER = "grid_export_power"
SENSOR_BATTERY_POWER = "battery_power"
SENSOR_BATTERY_CHARGING_POWER = "battery_charging_power"
SENSOR_BATTERY_DISCHARGING_POWER = "battery_discharging_power"
SENSOR_BATTERY_SOC = "battery_state_of_charge"
SENSOR_BATTERY_CHARGED_TODAY = "battery_energy_charged_today"
SENSOR_BATTERY_DISCHARGED_TODAY = "battery_energy_discharged_today"
SENSOR_TOTAL_SOLAR_PRODUCTION = "total_solar_production"
SENSOR_GRID_ENERGY_IMPORTED_TODAY = "grid_energy_imported_today"
SENSOR_GRID_ENERGY_EXPORTED_TODAY = "grid_energy_exported_today"
SENSOR_TOTAL_GRID_IMPORTED_ENERGY = "total_grid_imported_energy"
SENSOR_TOTAL_GRID_EXPORTED_ENERGY = "total_grid_exported_energy"
SENSOR_TOTAL_BATTERY_CHARGED_ENERGY = "total_battery_charged_energy"
SENSOR_TOTAL_BATTERY_DISCHARGED_ENERGY = "total_battery_discharged_energy"
SENSOR_SITE_STATUS = "site_status"
SENSOR_INVERTER_STATUS = "inverter_status"
SENSOR_BATTERY_STATUS = "battery_status"
