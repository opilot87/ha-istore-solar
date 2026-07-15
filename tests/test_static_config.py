"""Static tests for Home Assistant entity configuration text."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SENSOR_PY = ROOT / "custom_components" / "istore_solar" / "sensor.py"
API_PY = ROOT / "custom_components" / "istore_solar" / "api.py"
INIT_PY = ROOT / "custom_components" / "istore_solar" / "__init__.py"
CONFIG_FLOW_PY = ROOT / "custom_components" / "istore_solar" / "config_flow.py"
STRINGS_JSON = ROOT / "custom_components" / "istore_solar" / "strings.json"
MANIFEST_JSON = ROOT / "custom_components" / "istore_solar" / "manifest.json"
HACS_JSON = ROOT / "hacs.json"
README_MD = ROOT / "README.md"
CHANGELOG_MD = ROOT / "CHANGELOG.md"
FUNDING_YML = ROOT / ".github" / "FUNDING.yml"
BUG_TEMPLATE = ROOT / ".github" / "ISSUE_TEMPLATE" / "bug_report.md"
VALIDATE_WORKFLOW = ROOT / ".github" / "workflows" / "validate.yml"
RELEASE_NOTES = ROOT / "docs" / "release-notes-v0.6.0.md"


class TestStaticConfig(unittest.TestCase):
    """Verify cumulative entity declarations remain semantic and stable."""

    def test_cumulative_entity_suffixes_are_declared(self) -> None:
        text = (ROOT / "custom_components" / "istore_solar" / "const.py").read_text()
        for suffix in (
            "total_solar_production",
            "grid_energy_imported_today",
            "grid_energy_exported_today",
            "total_grid_imported_energy",
            "total_grid_exported_energy",
            "total_battery_charged_energy",
            "total_battery_discharged_energy",
        ):
            self.assertIn(f'"{suffix}"', text)
        self.assertNotIn('"experimental_total_grid_imported_energy"', text)
        self.assertNotIn('"experimental_total_grid_exported_energy"', text)

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

    def test_grid_total_entities_are_enabled_by_default(self) -> None:
        text = SENSOR_PY.read_text()
        description_start = text.index("SENSOR_DESCRIPTIONS")
        imported_section = text[
            text.index(
                "SENSOR_TOTAL_GRID_IMPORTED_ENERGY",
                description_start,
            ):
            text.index(
                "SENSOR_TOTAL_GRID_EXPORTED_ENERGY",
                description_start,
            )
        ]
        exported_section = text[
            text.index(
                "SENSOR_TOTAL_GRID_EXPORTED_ENERGY",
                description_start,
            ):
            text.index("SENSOR_TOTAL_BATTERY_CHARGED_ENERGY", description_start)
        ]
        self.assertIn("device_key=\"meter\"", imported_section)
        self.assertNotIn("entity_registry_enabled_default=False", imported_section)
        self.assertIn("SensorStateClass.TOTAL_INCREASING", imported_section)
        self.assertIn("device_key=\"meter\"", exported_section)
        self.assertNotIn("entity_registry_enabled_default=False", exported_section)
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
            "Grid imported today",
            "Grid exported today",
            "Total grid imported energy",
            "Total grid exported energy",
            "Total battery charged energy",
            "Total battery discharged energy",
            "Battery charged today",
            "Battery discharged today",
        ):
            self.assertIn(name, text)

    def test_energy_dashboard_mapping_documents_lifetime_sources(self) -> None:
        readme = README_MD.read_text()
        self.assertIn("| Grid consumption | Total grid imported energy |", readme)
        self.assertIn("| Return to grid | Total grid exported energy |", readme)
        self.assertIn("Do not use daily-resetting entities", readme)
        self.assertIn("- Grid imported today", readme)
        self.assertIn("- Grid exported today", readme)

    def test_experimental_lifetime_grid_names_are_not_created(self) -> None:
        combined = (
            (ROOT / "custom_components" / "istore_solar" / "const.py").read_text()
            + SENSOR_PY.read_text()
            + STRINGS_JSON.read_text()
        )
        self.assertNotIn('"experimental_total_grid_imported_energy"', combined)
        self.assertNotIn('"experimental_total_grid_exported_energy"', combined)

    def test_experimental_grid_unique_ids_migrate_to_stable_keys(self) -> None:
        text = INIT_PY.read_text()
        self.assertIn(
            '"experimental_total_grid_imported_energy": "total_grid_imported_energy"',
            text,
        )
        self.assertIn(
            '"experimental_total_grid_exported_energy": "total_grid_exported_energy"',
            text,
        )
        self.assertIn("new_unique_id", text)
        self.assertIn("new_entity_id", text)
        self.assertIn("version=4", text)
        self.assertIn("VERSION = 4", CONFIG_FLOW_PY.read_text())

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

    def test_lifetime_grid_fields_map_from_meter_kwh_points(self) -> None:
        text = API_PY.read_text()
        self.assertIn('"METER.APConsumedKWH"', text)
        self.assertIn("SENSOR_TOTAL_GRID_IMPORTED_ENERGY", text)
        self.assertIn('"METER.APProductionKWH"', text)
        self.assertIn("SENSOR_TOTAL_GRID_EXPORTED_ENERGY", text)

    def test_model_id_is_not_exposed_as_hardware_version(self) -> None:
        text = API_PY.read_text()
        self.assertNotIn('hw_version=_string_value(attrs.get("modelId"))', text)
        self.assertIn('model = _string_value(attrs.get("modelName"))', text)
        self.assertIn("serial_number=_serial_number_from_attrs(attrs)", text)

    def test_status_sensors_remain_raw_diagnostics(self) -> None:
        text = SENSOR_PY.read_text()
        self.assertNotIn("SensorDeviceClass.ENUM", text)
        self.assertIn("SENSOR_SITE_STATUS", text)
        self.assertIn("SENSOR_INVERTER_STATUS", text)
        self.assertIn("SENSOR_BATTERY_STATUS", text)
        self.assertGreaterEqual(
            text.count("entity_category=EntityCategory.DIAGNOSTIC"),
            3,
        )
        self.assertEqual(text.count("entity_registry_enabled_default=False"), 3)

    def test_public_beta_device_names_are_generic(self) -> None:
        api_text = API_PY.read_text()
        sensor_text = SENSOR_PY.read_text()
        self.assertIn('name="iStore Solar Site"', api_text)
        self.assertIn('"inverter": "Inverter"', api_text)
        self.assertIn('"battery": "Battery"', api_text)
        self.assertIn('"meter": "Meter"', api_text)
        self.assertIn('"inverter": "Inverter 1"', sensor_text)
        self.assertNotIn('name = _string_value(attrs.get("name"))', api_text)

    def test_readme_has_public_beta_sections(self) -> None:
        text = README_MD.read_text()
        for heading in (
            "## Overview",
            "## Supported Devices",
            "## Entities",
            "## Installation",
            "## Setup Using Account/Password",
            "## Manual Access-Token Fallback",
            "## Energy Dashboard Setup",
            "## Power Flow Card Plus Example",
            "## Sign Conventions",
            "## Options",
            "## Authentication Behaviour",
            "## Diagnostics",
            "## Troubleshooting",
            "## Security And Privacy",
            "## Known Limitations",
            "## Updating",
            "## Removing",
            "## Contributing",
            "## Support development",
        ):
            self.assertIn(heading, text)

    def test_branding_and_funding_are_declared(self) -> None:
        readme = README_MD.read_text()
        funding = FUNDING_YML.read_text()
        normalized_readme = " ".join(readme.split())
        for asset in ("icon.png", "icon@2x.png", "logo.png", "logo@2x.png"):
            self.assertTrue(
                (ROOT / "custom_components" / "istore_solar" / "brand" / asset).exists()
            )
        self.assertIn("buy_me_a_coffee: opilot87", funding)
        self.assertIn("independent community integration", normalized_readme)
        self.assertIn(
            "not affiliated with, endorsed by, or supported by iStore",
            normalized_readme,
        )
        self.assertIn("https://buymeacoffee.com/opilot87", readme)
        self.assertNotIn("buymeacoffee", (ROOT / "custom_components" / "istore_solar" / "strings.json").read_text().lower())

    def test_public_beta_release_metadata(self) -> None:
        manifest = MANIFEST_JSON.read_text()
        hacs = HACS_JSON.read_text()
        readme = README_MD.read_text()
        changelog = CHANGELOG_MD.read_text()
        self.assertIn('"version": "0.6.0"', manifest)
        self.assertIn('"codeowners": ["@opilot87"]', manifest)
        self.assertIn('"documentation": "https://github.com/opilot87/ha-istore-solar"', manifest)
        self.assertIn('"issue_tracker": "https://github.com/opilot87/ha-istore-solar/issues"', manifest)
        self.assertIn('"iot_class": "cloud_polling"', manifest)
        self.assertIn('"integration_type": "hub"', manifest)
        self.assertIn('"country": "AU"', hacs)
        self.assertNotIn("content_in_root", hacs)
        self.assertIn("https://github.com/opilot87/ha-istore-solar", readme)
        self.assertIn("RSA-OAEP", changelog)
        self.assertIn("Power Flow Card Plus", changelog)

    def test_release_notes_have_required_sections(self) -> None:
        text = RELEASE_NOTES.read_text()
        for heading in (
            "# iStore Solar v0.6.0 — Public Beta",
            "## Highlights",
            "## Supported data",
            "## Authentication",
            "## Installation",
            "## Updating",
            "## Known limitations",
            "## Reporting issues",
            "## Support development",
        ):
            self.assertIn(heading, text)
        self.assertIn(
            "This is an unofficial community integration and is not affiliated with,",
            text,
        )
        self.assertNotIn("private/", text)

    def test_bug_template_requests_public_beta_triage_fields(self) -> None:
        text = BUG_TEMPLATE.read_text()
        for expected in (
            "Home Assistant version",
            "iStore Solar integration version",
            "Install method",
            "Hardware model",
            "Authentication mode",
            "Reproduction Steps",
            "sanitized Home Assistant diagnostics",
            "password",
            "tokens",
            "HAR files",
            "private captures",
            "serial numbers",
        ):
            self.assertIn(expected, text)

    def test_validation_workflow_is_declared(self) -> None:
        text = VALIDATE_WORKFLOW.read_text()
        self.assertIn("hacs/action@main", text)
        self.assertIn("category: integration", text)
        self.assertIn("home-assistant/actions/hassfest@master", text)
        self.assertIn("actions/setup-python@v5", text)
        self.assertIn("python -m unittest discover -s tests", text)

    def test_diagnostics_include_public_beta_fields(self) -> None:
        text = (ROOT / "custom_components" / "istore_solar" / "diagnostics.py").read_text()
        self.assertIn("integration_version", text)
        self.assertIn("config_entry_version", text)
        self.assertIn("last_update_duration_seconds", text)
        self.assertIn("entity_count_by_platform", text)

    def test_optional_cumulative_failures_retain_last_values(self) -> None:
        text = API_PY.read_text()
        self.assertIn("self._last_battery_total_energy", text)
        self.assertIn("self._last_meter_total_energy", text)
        self.assertIn("battery_total_energy = self._last_battery_total_energy", text)
        self.assertIn("meter_total_energy = self._last_meter_total_energy", text)

    def test_coordinator_records_update_duration(self) -> None:
        text = (ROOT / "custom_components" / "istore_solar" / "coordinator.py").read_text()
        self.assertIn("last_update_duration_seconds", text)
        self.assertIn("perf_counter", text)
        self.assertIn("coordinator update succeeded", text)


if __name__ == "__main__":
    unittest.main()
