"""Constants for the iStore Solar integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "istore_solar"
DEFAULT_NAME = "iStore Solar"
DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

CONF_EMAIL = "email"
CONF_ACCESS_TOKEN = "access_token"

ATTRIBUTION = "Data provided by the iStore Solar cloud portal"
MANUFACTURER = "iStore"

API_HOST = "home.istore.net.au"
API_BASE_URL = f"https://{API_HOST}"
DEFAULT_LOCALE = "en-US"

SENSOR_SOLAR_POWER = "solar_power"
SENSOR_HOME_CONSUMPTION_POWER = "home_consumption_power"
SENSOR_GRID_POWER = "grid_power"
SENSOR_BATTERY_POWER = "battery_power"
SENSOR_BATTERY_SOC = "battery_state_of_charge"
SENSOR_BATTERY_CHARGED_TODAY = "battery_energy_charged_today"
SENSOR_BATTERY_DISCHARGED_TODAY = "battery_energy_discharged_today"
SENSOR_SITE_STATUS = "site_status"
SENSOR_INVERTER_STATUS = "inverter_status"
SENSOR_BATTERY_STATUS = "battery_status"
