"""Tests for signed power derivation helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


POWER_MODULE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "istore_solar"
    / "power.py"
)
SPEC = importlib.util.spec_from_file_location("istore_solar_power", POWER_MODULE)
assert SPEC is not None
assert SPEC.loader is not None
power = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(power)


class TestPowerDerivation(unittest.TestCase):
    """Verify derived power values never expose negative values."""

    def test_grid_import_power(self) -> None:
        self.assertEqual(power.positive_power(1.25), 1.25)
        self.assertEqual(power.positive_power(-1.25), 0)
        self.assertEqual(power.positive_power(0), 0)

    def test_grid_export_power(self) -> None:
        self.assertEqual(power.inverted_positive_power(-1.25), 1.25)
        self.assertEqual(power.inverted_positive_power(1.25), 0)
        self.assertEqual(power.inverted_positive_power(0), 0)

    def test_battery_charging_power(self) -> None:
        self.assertEqual(power.positive_power(1.81), 1.81)
        self.assertEqual(power.positive_power(-0.26), 0)
        self.assertEqual(power.positive_power(0), 0)

    def test_battery_discharging_power(self) -> None:
        self.assertEqual(power.inverted_positive_power(-0.26), 0.26)
        self.assertEqual(power.inverted_positive_power(1.81), 0)
        self.assertEqual(power.inverted_positive_power(0), 0)

    def test_missing_source_remains_unavailable(self) -> None:
        self.assertIsNone(power.positive_power(None))
        self.assertIsNone(power.inverted_positive_power(None))


if __name__ == "__main__":
    unittest.main()
