"""Static tests for Home Assistant entity configuration text."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SENSOR_PY = ROOT / "custom_components" / "istore_solar" / "sensor.py"
API_PY = ROOT / "custom_components" / "istore_solar" / "api.py"
STRINGS_JSON = ROOT / "custom_components" / "istore_solar" / "strings.json"
README_MD = ROOT / "README.md"


class TestStaticConfig(unittest.TestCase):
    """Verify cumulative entity declarations remain semantic and stable."""

    def test_cumulative_entity_suffixes_are_declared(self) -> None:
        text = (ROOT / "custom_components" / "istore_solar" / "const.py").read_text()
        for suffix in (
            "total_solar_production",
            "grid_energy_imported_today",
            "grid_energy_exported_today",
            "experimental_total_grid_imported_energy",
            "experimental_total_grid_exported_energy",
            "total_battery_charged_energy",
            "total_battery_discharged_energy",
        ):
            self.assertIn(f'"{suffix}"', text)
        self.assertNotIn('"total_grid_imported_energy"', text)
        self.assertNotIn('"total_grid_exported_energy"', text)

    def test_cumulative_sensors_are_energy_total_increasing_kwh(self) -> None:
        text = SENSOR_PY.read_text()
        self.assertEqual(text.count("state_class=SensorStateClass.TOTAL_INCREASING"), 5)
        self.assertGreaterEqual(
            text.count("device_class=SensorDeviceClass.ENERGY"),
            9,
        )
        self.assertGreaterEqual(
            text.count("native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR"),
            9,
        )

    def test_experimental_meter_total_entities_are_disabled_by_default(self) -> None:
        text = SENSOR_PY.read_text()
        description_start = text.index("SENSOR_DESCRIPTIONS")
        imported_section = text[
            text.index(
                "SENSOR_EXPERIMENTAL_TOTAL_GRID_IMPORTED_ENERGY",
                description_start,
            ):
            text.index(
                "SENSOR_EXPERIMENTAL_TOTAL_GRID_EXPORTED_ENERGY",
                description_start,
            )
        ]
        exported_section = text[
            text.index(
                "SENSOR_EXPERIMENTAL_TOTAL_GRID_EXPORTED_ENERGY",
                description_start,
            ):
            text.index("SENSOR_TOTAL_BATTERY_CHARGED_ENERGY", description_start)
        ]
        self.assertIn("device_key=\"meter\"", imported_section)
        self.assertIn("entity_registry_enabled_default=False", imported_section)
        self.assertIn("SensorStateClass.TOTAL_INCREASING", imported_section)
        self.assertIn("device_key=\"meter\"", exported_section)
        self.assertIn("entity_registry_enabled_default=False", exported_section)
        self.assertIn("SensorStateClass.TOTAL_INCREASING", exported_section)

    def test_battery_total_request_uses_confirmed_shape(self) -> None:
        text = API_PY.read_text()
        self.assertIn("/hossain-bff/monitor/v1.0/measurement-point/time-series", text)
        self.assertIn('"mdmTypes": "Res_Storage"', text)
        self.assertIn('"interval": "5m"', text)
        self.assertIn('"measurementPoints": BATTERY_TOTAL_MEASUREMENT_POINTS', text)
        self.assertIn('"autoInterpolate": True', text)

    def test_meter_total_request_uses_confirmed_asset_list_shape(self) -> None:
        text = API_PY.read_text()
        self.assertIn("/hossain-bff/monitor/v1.0/asset/list", text)
        self.assertIn('"pageSize": 50', text)
        self.assertIn('"pageNo": 1', text)
        self.assertIn('"mdmTypes": "Res_Meter"', text)
        self.assertIn('"measurementPoints": METER_TOTAL_MEASUREMENT_POINTS', text)
        self.assertIn("METER.APConsumedKWH,METER.APProductionKWH", text)

    def test_cumulative_translations_exist(self) -> None:
        text = STRINGS_JSON.read_text()
        for name in (
            "Total solar production",
            "Grid energy imported today",
            "Grid energy exported today",
            "Experimental total grid imported energy",
            "Experimental total grid exported energy",
            "Total battery charged energy",
            "Total battery discharged energy",
        ):
            self.assertIn(name, text)

    def test_grid_daily_sensors_are_not_documented_as_lifetime_energy_dashboard(self) -> None:
        readme = README_MD.read_text()
        self.assertIn("Do not use `Grid energy imported today`", readme)
        self.assertNotIn("| Grid consumption | Total grid imported energy |", readme)
        self.assertNotIn("| Return to grid | Total grid exported energy |", readme)
        self.assertNotIn("Total grid imported energy", readme)
        self.assertNotIn("Total grid exported energy", readme)
        self.assertIn("not Energy Dashboard recommended", readme)

    def test_old_lifetime_grid_names_are_not_created(self) -> None:
        combined = (
            (ROOT / "custom_components" / "istore_solar" / "const.py").read_text()
            + SENSOR_PY.read_text()
            + STRINGS_JSON.read_text()
        )
        self.assertNotIn('"total_grid_imported_energy"', combined)
        self.assertNotIn('"total_grid_exported_energy"', combined)

    def test_daily_grid_fields_map_from_meter_points(self) -> None:
        text = API_PY.read_text()
        self.assertIn('"METER.APConsumed"', text)
        self.assertIn("SENSOR_GRID_ENERGY_IMPORTED_TODAY", text)
        self.assertIn('"METER.APProduction"', text)
        self.assertIn("SENSOR_GRID_ENERGY_EXPORTED_TODAY", text)

    def test_daily_grid_decreases_are_not_tracked_as_cumulative(self) -> None:
        text = API_PY.read_text()
        imported_section = text[
            text.index("SENSOR_GRID_ENERGY_IMPORTED_TODAY"):
            text.index("SENSOR_GRID_ENERGY_EXPORTED_TODAY")
        ]
        self.assertNotIn("_cumulative_value", imported_section)


if __name__ == "__main__":
    unittest.main()
