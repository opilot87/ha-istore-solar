"""Static tests for Home Assistant entity configuration text."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SENSOR_PY = ROOT / "custom_components" / "istore_solar" / "sensor.py"
API_PY = ROOT / "custom_components" / "istore_solar" / "api.py"
STRINGS_JSON = ROOT / "custom_components" / "istore_solar" / "strings.json"


class TestStaticConfig(unittest.TestCase):
    """Verify cumulative entity declarations remain semantic and stable."""

    def test_cumulative_entity_suffixes_are_declared(self) -> None:
        text = (ROOT / "custom_components" / "istore_solar" / "const.py").read_text()
        for suffix in (
            "total_solar_production",
            "total_grid_imported_energy",
            "total_grid_exported_energy",
            "total_battery_charged_energy",
            "total_battery_discharged_energy",
        ):
            self.assertIn(f'"{suffix}"', text)

    def test_cumulative_sensors_are_energy_total_increasing_kwh(self) -> None:
        text = SENSOR_PY.read_text()
        self.assertEqual(text.count("state_class=SensorStateClass.TOTAL_INCREASING"), 5)
        self.assertGreaterEqual(
            text.count("device_class=SensorDeviceClass.ENERGY"),
            7,
        )
        self.assertGreaterEqual(
            text.count("native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR"),
            7,
        )

    def test_battery_total_request_uses_confirmed_shape(self) -> None:
        text = API_PY.read_text()
        self.assertIn("/hossain-bff/monitor/v1.0/measurement-point/time-series", text)
        self.assertIn('"mdmTypes": "Res_Storage"', text)
        self.assertIn('"interval": "5m"', text)
        self.assertIn('"measurementPoints": BATTERY_TOTAL_MEASUREMENT_POINTS', text)
        self.assertIn('"autoInterpolate": True', text)

    def test_cumulative_translations_exist(self) -> None:
        text = STRINGS_JSON.read_text()
        for name in (
            "Total solar production",
            "Total grid imported energy",
            "Total grid exported energy",
            "Total battery charged energy",
            "Total battery discharged energy",
        ):
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
