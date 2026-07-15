"""Static and artificial-vector tests for iStore Solar authentication."""

from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_PY = ROOT / "custom_components" / "istore_solar" / "api.py"
CONFIG_FLOW_PY = ROOT / "custom_components" / "istore_solar" / "config_flow.py"
INIT_PY = ROOT / "custom_components" / "istore_solar" / "__init__.py"
DIAGNOSTICS_PY = ROOT / "custom_components" / "istore_solar" / "diagnostics.py"
PRIVACY_PY = ROOT / "custom_components" / "istore_solar" / "privacy.py"
MANIFEST_JSON = ROOT / "custom_components" / "istore_solar" / "manifest.json"
VECTOR_JSON = ROOT / "tests" / "fixtures" / "istore_auth_rsa_oaep_sha256_vector.json"


class TestAuthenticationStaticConfig(unittest.TestCase):
    """Verify automatic authentication is wired with the confirmed behavior."""

    def test_fake_vector_round_trips_with_oaep_sha256(self) -> None:
        vector = json.loads(VECTOR_JSON.read_text())
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp = Path(tmp_dir)
            private_key = tmp / "private.pem"
            public_key = tmp / "public.der"
            plaintext = tmp / "password.bin"
            ciphertext = tmp / "cipher.bin"
            decrypted = tmp / "decrypted.bin"

            private_key.write_text(vector["private_key_pem"])
            public_key.write_bytes(base64.b64decode(vector["public_key_der_base64"]))
            plaintext.write_bytes(vector["fake_password"].encode("utf-8"))

            subprocess.run(
                [
                    "openssl",
                    "pkeyutl",
                    "-encrypt",
                    "-pubin",
                    "-keyform",
                    "DER",
                    "-inkey",
                    str(public_key),
                    "-in",
                    str(plaintext),
                    "-out",
                    str(ciphertext),
                    "-pkeyopt",
                    "rsa_padding_mode:oaep",
                    "-pkeyopt",
                    "rsa_oaep_md:sha256",
                    "-pkeyopt",
                    "rsa_mgf1_md:sha256",
                ],
                check=True,
            )
            self.assertEqual(vector["expected_ciphertext_bytes"], ciphertext.stat().st_size)

            subprocess.run(
                [
                    "openssl",
                    "pkeyutl",
                    "-decrypt",
                    "-inkey",
                    str(private_key),
                    "-in",
                    str(ciphertext),
                    "-out",
                    str(decrypted),
                    "-pkeyopt",
                    "rsa_padding_mode:oaep",
                    "-pkeyopt",
                    "rsa_oaep_md:sha256",
                    "-pkeyopt",
                    "rsa_mgf1_md:sha256",
                ],
                check=True,
            )
            self.assertEqual(vector["fake_password"], decrypted.read_text())

    def test_api_uses_confirmed_rsa_oaep_sha256(self) -> None:
        text = API_PY.read_text()
        self.assertIn("serialization.load_der_public_key", text)
        self.assertIn("isinstance(loaded_key, rsa.RSAPublicKey)", text)
        self.assertIn("padding.OAEP", text)
        self.assertGreaterEqual(text.count("hashes.SHA256()"), 2)
        self.assertIn("base64.b64encode(ciphertext)", text)
        self.assertNotIn("PKCS1v15", text)

    def test_login_sequence_fields_are_declared(self) -> None:
        text = API_PY.read_text()
        self.assertIn("/hossain-bff/framework/v1.0/user/public-key", text)
        self.assertIn("/hossain-bff/framework/v1.0/user/login", text)
        self.assertIn('"strategy": key.strategy', text)
        self.assertIn('"account": account', text)
        self.assertIn('"password": encrypted_password', text)
        self.assertIn("/hossain-bff/framework/v1.0/user/set-session", text)
        self.assertIn('"orgId": org_id', text)
        self.assertIn("/app-portal/web/v1/session/get", text)
        self.assertIn('session_data.get("id")', text)
        self.assertIn('user_info.get("token")', text)
        self.assertIn("IStoreSolarTokenMismatchError", text)
        self.assertIn('data.get("organizations")', text)
        self.assertIn('"accessToken"', text)

    def test_login_response_is_not_treated_as_final_proof(self) -> None:
        text = API_PY.read_text()
        self.assertIn('if not response_text.strip():', text)
        self.assertIn('payload = {}', text)
        self.assertIn('body_type = "empty"', text)
        self.assertIn("INVALID_CREDENTIALS_CODE", text)
        self.assertIn('"Login accepted, but no access token was returned"', text)
        self.assertIn('"Access token returned, but validation failed"', text)
        self.assertIn("await self.async_set_session(login_token, org_id)", text)
        self.assertIn("session_token = session_data.get(\"id\")", text)

    def test_automatic_relogin_is_one_shot_and_locked(self) -> None:
        text = API_PY.read_text()
        self.assertIn("self._login_lock = asyncio.Lock()", text)
        self.assertIn("async with self._login_lock", text)
        self.assertIn("allow_relogin=False", text)
        self.assertIn("self._automatic_relogin_count += 1", text)

    def test_config_flow_supports_automatic_and_manual_modes(self) -> None:
        text = CONFIG_FLOW_PY.read_text()
        self.assertIn('AUTH_MODE_AUTOMATIC', text)
        self.assertIn('AUTH_MODE_MANUAL_TOKEN', text)
        self.assertIn('menu_options=["automatic", "manual_token"]', text)
        self.assertIn("async_step_automatic", text)
        self.assertIn("async_step_manual_token", text)
        self.assertIn("blank to keep", (ROOT / "custom_components" / "istore_solar" / "strings.json").read_text())

    def test_token_only_entries_migrate_to_manual_mode(self) -> None:
        text = INIT_PY.read_text()
        self.assertIn("version=4", text)
        self.assertIn('data[CONF_AUTH_MODE] = AUTH_MODE_MANUAL_TOKEN', text)
        self.assertIn("GRID_UNIQUE_ID_SUFFIX_MIGRATIONS", text)

    def test_manifest_declares_crypto_dependency_and_version(self) -> None:
        manifest = json.loads(MANIFEST_JSON.read_text())
        self.assertEqual("0.5.1", manifest["version"])
        self.assertIn("cryptography>=41.0.0", manifest["requirements"])

    def test_diagnostics_and_redaction_cover_auth_secrets(self) -> None:
        diagnostics = DIAGNOSTICS_PY.read_text()
        privacy = PRIVACY_PY.read_text()
        self.assertIn("entry_token_present", diagnostics)
        self.assertIn("entry_password_configured", diagnostics)
        self.assertIn('"publickey"', privacy)
        self.assertIn('"cipher"', privacy)
        self.assertIn('"account"', privacy)
        self.assertIn('"password"', privacy)


if __name__ == "__main__":
    unittest.main()
