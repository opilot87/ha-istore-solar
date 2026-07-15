# iStore Solar v0.6.0 — Public Beta

This is an unofficial community integration and is not affiliated with,
endorsed by, or supported by iStore.

## Highlights

- First public beta release for Home Assistant.
- Automatic iStore account/password sign-in.
- Manual access-token fallback for troubleshooting.
- Live solar, home, grid, and battery power sensors.
- Validated lifetime energy sensors for the Home Assistant Energy Dashboard.
- Sanitized diagnostics and local integration branding.

## Supported data

- Site, inverter, battery, and meter devices where the iStore cloud exposes the
  confirmed residential solar asset structure.
- Live power in kW, including signed grid/battery power and derived import,
  export, charging, and discharging power.
- Daily grid and battery energy counters in kWh.
- Lifetime solar, grid import/export, and battery charge/discharge energy
  counters in kWh.

## Authentication

Automatic sign-in encrypts the password locally with the confirmed RSA-OAEP
SHA-256 flow, completes the iStore session sequence, and validates the final
token before setup succeeds.

Refresh-token support is not implemented. Automatic entries store the iStore
account and password in the Home Assistant config entry so the integration can
sign in again when needed. Manual access-token setup remains available as an
advanced fallback.

## Installation

Add `https://github.com/opilot87/ha-istore-solar` as a HACS custom repository
with category `Integration`, install iStore Solar, restart Home Assistant, then
add the integration from Settings > Devices & services.

Manual installation is also possible by copying `custom_components/istore_solar`
into your Home Assistant `custom_components` directory and restarting Home
Assistant.

## Updating

Update through HACS or replace the manual custom component files, then restart
Home Assistant. Removing and re-adding the integration is not normally needed.

## Known limitations

- Cloud polling only; no local Modbus support.
- Read-only; no inverter, battery, or site control.
- Refresh-token lifecycle is not implemented.
- Multi-site selection is not implemented.
- Status-code labels remain unresolved and are disabled diagnostics by default.
- Supported hardware is based on the tested residential site configuration.

## Reporting issues

Use the GitHub bug report template and include the integration version, Home
Assistant version, install method, hardware model, authentication mode, symptoms,
sanitized diagnostics, sanitized logs, and reproduction steps.

Do not post passwords, tokens, Authorization headers, cookies, HAR files,
private captures, addresses, serial numbers, site IDs, device IDs, or raw API
payloads.

## Support development

This integration is developed and maintained independently in spare time.
Support is optional, and all integration functionality remains free and open
source.

You can support development at https://buymeacoffee.com/opilot87.
