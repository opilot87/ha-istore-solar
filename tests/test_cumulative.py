"""Tests for experimental cumulative energy helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


CUMULATIVE_MODULE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "istore_solar"
    / "cumulative.py"
)
SPEC = importlib.util.spec_from_file_location(
    "istore_solar_cumulative",
    CUMULATIVE_MODULE,
)
assert SPEC is not None
assert SPEC.loader is not None
cumulative = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cumulative
SPEC.loader.exec_module(cumulative)


class TestCumulativeHelpers(unittest.TestCase):
    """Verify cumulative counter normalization and observation."""

    def test_numeric_strings_and_zero_values(self) -> None:
        self.assertEqual(cumulative.cumulative_native_value("123.45"), 123.45)
        self.assertEqual(cumulative.cumulative_native_value("0"), 0)
        self.assertEqual(cumulative.cumulative_native_value(0), 0)

    def test_malformed_and_negative_values_are_rejected(self) -> None:
        self.assertIsNone(cumulative.cumulative_native_value("not-a-number"))
        self.assertIsNone(cumulative.cumulative_native_value(""))
        self.assertIsNone(cumulative.cumulative_native_value(-1))
        self.assertIsNone(cumulative.cumulative_native_value("-1.25"))
        self.assertIsNone(cumulative.cumulative_native_value(True))

    def test_missing_field_observation(self) -> None:
        observations = {}
        previous = {}
        decreased = set()

        value = cumulative.observe_cumulative_value(
            observations,
            previous,
            decreased,
            "total_solar_production",
            None,
        )

        self.assertIsNone(value)
        self.assertTrue(observations["total_solar_production"].missing)
        self.assertFalse(observations["total_solar_production"].detected)

    def test_malformed_field_observation(self) -> None:
        observations = {}
        previous = {}
        decreased = set()

        value = cumulative.observe_cumulative_value(
            observations,
            previous,
            decreased,
            "total_solar_production",
            "bad",
        )

        self.assertIsNone(value)
        self.assertTrue(observations["total_solar_production"].detected)
        self.assertTrue(observations["total_solar_production"].malformed)

    def test_decrease_detection_preserves_source_value(self) -> None:
        observations = {}
        previous = {}
        decreased = set()

        first = cumulative.observe_cumulative_value(
            observations,
            previous,
            decreased,
            "total_battery_charged_energy",
            10,
        )
        second = cumulative.observe_cumulative_value(
            observations,
            previous,
            decreased,
            "total_battery_charged_energy",
            9,
        )

        self.assertEqual(first, 10)
        self.assertEqual(second, 9)
        self.assertIn("total_battery_charged_energy", decreased)
        self.assertTrue(observations["total_battery_charged_energy"].decreased)

    def test_all_cumulative_entity_keys_normalize_valid_values(self) -> None:
        observations = {}
        previous = {}
        decreased = set()

        for sensor_key, raw_value in (
            ("total_solar_production", "8116.73"),
            ("total_battery_charged_energy", 1234.5),
            ("total_battery_discharged_energy", "987.6"),
        ):
            value = cumulative.observe_cumulative_value(
                observations,
                previous,
                decreased,
                sensor_key,
                raw_value,
            )
            self.assertIsNotNone(value)
            self.assertTrue(observations[sensor_key].detected)
            self.assertFalse(observations[sensor_key].malformed)


if __name__ == "__main__":
    unittest.main()
