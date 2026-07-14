"""Sensor platform for iStore Solar."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import IStoreSolarConfigEntry
from .api import IStoreSolarDevice, IStoreSolarSensorValue
from .const import (
    ATTRIBUTION,
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
    SENSOR_TOTAL_SOLAR_PRODUCTION,
)
from .coordinator import IStoreSolarDataUpdateCoordinator


@dataclass(frozen=True, kw_only=True)
class IStoreSolarSensorEntityDescription(SensorEntityDescription):
    """Describe an iStore Solar sensor entity."""

    device_key: str = "site"


SENSOR_DESCRIPTIONS: tuple[IStoreSolarSensorEntityDescription, ...] = (
    IStoreSolarSensorEntityDescription(
        key=SENSOR_SOLAR_POWER,
        translation_key=SENSOR_SOLAR_POWER,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_HOME_CONSUMPTION_POWER,
        translation_key=SENSOR_HOME_CONSUMPTION_POWER,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_GRID_POWER,
        translation_key=SENSOR_GRID_POWER,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_GRID_IMPORT_POWER,
        translation_key=SENSOR_GRID_IMPORT_POWER,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_GRID_EXPORT_POWER,
        translation_key=SENSOR_GRID_EXPORT_POWER,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_BATTERY_POWER,
        translation_key=SENSOR_BATTERY_POWER,
        device_key="battery",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_BATTERY_CHARGING_POWER,
        translation_key=SENSOR_BATTERY_CHARGING_POWER,
        device_key="battery",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_BATTERY_DISCHARGING_POWER,
        translation_key=SENSOR_BATTERY_DISCHARGING_POWER,
        device_key="battery",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_BATTERY_SOC,
        translation_key=SENSOR_BATTERY_SOC,
        device_key="battery",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_BATTERY_CHARGED_TODAY,
        translation_key=SENSOR_BATTERY_CHARGED_TODAY,
        device_key="battery",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_BATTERY_DISCHARGED_TODAY,
        translation_key=SENSOR_BATTERY_DISCHARGED_TODAY,
        device_key="battery",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_TOTAL_SOLAR_PRODUCTION,
        translation_key=SENSOR_TOTAL_SOLAR_PRODUCTION,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_GRID_ENERGY_IMPORTED_TODAY,
        translation_key=SENSOR_GRID_ENERGY_IMPORTED_TODAY,
        device_key="meter",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_GRID_ENERGY_EXPORTED_TODAY,
        translation_key=SENSOR_GRID_ENERGY_EXPORTED_TODAY,
        device_key="meter",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=2,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_TOTAL_BATTERY_CHARGED_ENERGY,
        translation_key=SENSOR_TOTAL_BATTERY_CHARGED_ENERGY,
        device_key="battery",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_TOTAL_BATTERY_DISCHARGED_ENERGY,
        translation_key=SENSOR_TOTAL_BATTERY_DISCHARGED_ENERGY,
        device_key="battery",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=2,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_SITE_STATUS,
        translation_key=SENSOR_SITE_STATUS,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_INVERTER_STATUS,
        translation_key=SENSOR_INVERTER_STATUS,
        device_key="inverter",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    IStoreSolarSensorEntityDescription(
        key=SENSOR_BATTERY_STATUS,
        translation_key=SENSOR_BATTERY_STATUS,
        device_key="battery",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: IStoreSolarConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up iStore Solar sensors from a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        IStoreSolarSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class IStoreSolarSensor(
    CoordinatorEntity[IStoreSolarDataUpdateCoordinator],
    SensorEntity,
):
    """Representation of an iStore Solar sensor."""

    entity_description: IStoreSolarSensorEntityDescription
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IStoreSolarDataUpdateCoordinator,
        description: IStoreSolarSensorEntityDescription,
    ) -> None:
        """Initialize the sensor entity."""
        super().__init__(coordinator)
        self.entity_description = description
        device = self._device
        unique_device_id = (
            device.identifiers[1] if device is not None else description.device_key
        )
        self._attr_unique_id = f"{unique_device_id}_{description.key}"

    @property
    def native_value(self) -> float | int | str | None:
        """Return the native sensor value."""
        value = self._sensor_value
        return value.native_value if value is not None else None

    @property
    def available(self) -> bool:
        """Return whether the entity is available."""
        value = self._sensor_value
        return (
            super().available
            and value is not None
            and value.available
            and value.native_value is not None
        )

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return device information for this entity."""
        device = self._device
        if device is None:
            return None
        return DeviceInfo(
            identifiers={device.identifiers},
            manufacturer=device.manufacturer,
            model=device.model,
            name=device.name,
            via_device=device.via_device,
            serial_number=device.serial_number,
            sw_version=device.sw_version,
            hw_version=device.hw_version,
        )

    @property
    def _sensor_value(self) -> IStoreSolarSensorValue | None:
        """Return the normalized value for this sensor."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.values.get(self.entity_description.key)

    @property
    def _device(self) -> IStoreSolarDevice | None:
        """Return the normalized device for this sensor."""
        default_site = IStoreSolarDevice(
            identifiers=(DOMAIN, "site"),
            name="iStore Solar",
            manufacturer=MANUFACTURER,
        )

        if self.coordinator.data is None:
            if self.entity_description.device_key == "meter":
                return None
            if self.entity_description.device_key == "site":
                return default_site
            return IStoreSolarDevice(
                identifiers=(DOMAIN, self.entity_description.device_key),
                name=f"iStore Solar {self.entity_description.device_key.title()}",
                manufacturer=MANUFACTURER,
                via_device=(DOMAIN, "site"),
            )

        if self.entity_description.device_key == "site":
            return self.coordinator.data.site

        if self.entity_description.device_key == "meter":
            return self.coordinator.data.devices.get("meter")

        return self.coordinator.data.devices.get(
            self.entity_description.device_key,
            IStoreSolarDevice(
                identifiers=(DOMAIN, self.entity_description.device_key),
                name=f"iStore Solar {self.entity_description.device_key.title()}",
                manufacturer=MANUFACTURER,
                via_device=self.coordinator.data.site.identifiers,
            ),
        )
