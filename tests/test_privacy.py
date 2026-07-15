"""Tests for diagnostics and log redaction helpers."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


PRIVACY_MODULE = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "istore_solar"
    / "privacy.py"
)
SPEC = importlib.util.spec_from_file_location("istore_solar_privacy", PRIVACY_MODULE)
assert SPEC is not None
assert SPEC.loader is not None
privacy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(privacy)


class TestPrivacyHelpers(unittest.TestCase):
    """Verify sensitive values cannot leak through diagnostics helpers."""

    def test_sensitive_keys_are_redacted(self) -> None:
        data = {
            "access_token": "APP_PORTAL_S_abcdefghijklmnopqrstuvwxyz123456",
            "serial_number": "SN123456789",
            "safe": "ok",
        }

        redacted = privacy.redact_sensitive_data(data)

        self.assertEqual(redacted["access_token"], privacy.REDACTED)
        self.assertEqual(redacted["serial_number"], privacy.REDACTED)
        self.assertEqual(redacted["safe"], "ok")

    def test_token_like_plain_values_are_redacted(self) -> None:
        data = {
            "last_exception": (
                "Authorization: Bearer APP_PORTAL_S_abcdefghijklmnopqrstuvwxyz123456"
            ),
            "note": "user@example.com",
        }

        redacted = privacy.redact_sensitive_data(data)

        self.assertNotIn("APP_PORTAL_S_", redacted["last_exception"])
        self.assertNotIn("user@example.com", redacted["note"])
        self.assertIn(privacy.REDACTED, redacted["last_exception"])

    def test_response_preview_redacts_json(self) -> None:
        preview = privacy.sanitize_response_preview(
            '{"token":"APP_PORTAL_S_abcdefghijklmnopqrstuvwxyz123456","code":200}',
            "application/json",
        )

        self.assertIsNotNone(preview)
        assert preview is not None
        self.assertNotIn("APP_PORTAL_S_", preview)
        self.assertIn(privacy.REDACTED, preview)

    def test_safe_auth_presence_booleans_are_not_redacted(self) -> None:
        data = {
            "token_present": True,
            "password_configured": True,
            "entry_token_present": False,
            "entry_password_configured": False,
        }

        redacted = privacy.redact_sensitive_data(data)

        self.assertEqual(data, redacted)

    def test_auth_crypto_and_request_keys_are_redacted(self) -> None:
        data = {
            "public_key": "MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AFAKE",
            "ciphertext": "a" * 344,
            "requestId": "abcdef0123456789abcdef0123456789",
            "raw_payload": {"token": "APP_PORTAL_S_abcdefghijklmnopqrstuvwxyz123456"},
        }

        redacted = privacy.redact_sensitive_data(data)

        self.assertEqual(redacted["public_key"], privacy.REDACTED)
        self.assertEqual(redacted["ciphertext"], privacy.REDACTED)
        self.assertEqual(redacted["requestId"], privacy.REDACTED)
        self.assertEqual(redacted["raw_payload"]["token"], privacy.REDACTED)


if __name__ == "__main__":
    unittest.main()
