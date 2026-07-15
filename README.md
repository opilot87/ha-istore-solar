# iStore Solar for Home Assistant

Experimental Home Assistant custom integration for the Australian iStore Solar
cloud portal at `home.istore.net.au`.

## Status

Version 0.5.0 is a private experimental read-only build. It supports automatic
account/password sign-in plus an advanced manual bearer-token fallback, and
exposes validated lifetime solar, grid, and battery energy sensors for Home
Assistant Energy Dashboard testing.

Automatic refresh-token use and public-release hardening are not complete. Do
not use this integration for automation, billing, grid settlement, safety, or
any other critical purpose.

## Supported Features

- Cloud polling through Home Assistant's shared aiohttp session.
- Config flow for automatic sign-in or advanced manual bearer-token setup.
- Reauthentication for automatic credentials or manual-token replacement.
- Options flow for credential replacement and polling interval.
- Polling interval range: 15 to 300 seconds, default 30 seconds.
- Site, inverter, battery, and meter devices where supported by discovered
  assets.
- Sanitized diagnostics and debug logging for troubleshooting.

## Unsupported Features

- Automatic token refresh.
- Multi-site selection.
- Control/write operations.
- Confirmed status-code enum labels.

## Sensors

- Solar power, in kW
- Home consumption power, in kW
- Grid power, in kW, signed
- Grid import power, in kW
- Grid export power, in kW
- Battery power, in kW, signed
- Battery charging power, in kW
- Battery discharging power, in kW
- Battery state of charge, in %
- Energy charged today, in kWh
- Energy discharged today, in kWh
- Grid energy imported today, in kWh
- Grid energy exported today, in kWh
- Total solar production, in kWh
- Total grid imported energy, in kWh
- Total grid exported energy, in kWh
- Total battery charged energy, in kWh
- Total battery discharged energy, in kWh
- Site, inverter, and battery status code diagnostics

Grid power follows the sign convention observed in live Home Assistant testing:
positive values are grid import and negative values are grid export.

- Grid import power = `max(grid_power, 0)`
- Grid export power = `max(-grid_power, 0)`

Battery power follows the sign convention observed in live Home Assistant
testing: positive values are battery charging and negative values are battery
discharging.

- Battery charging power = `max(battery_power, 0)`
- Battery discharging power = `max(-battery_power, 0)`

The daily battery and grid energy sensors come from daily-resetting API fields
and use `total`, not `total_increasing`.

The site, inverter, and battery status entities intentionally expose raw numeric
codes only. Captured responses have shown codes such as `0`, `1`, and `2`, but
the API evidence does not yet include a confirmed enum mapping.

## Energy Dashboard

Version 0.4.0 supports these Home Assistant Energy Dashboard sources:

| Energy Dashboard slot | Entity |
| --- | --- |
| Solar production | Total solar production |
| Grid consumption | Total grid imported energy |
| Return to grid | Total grid exported energy |
| Battery energy in | Total battery charged energy |
| Battery energy out | Total battery discharged energy |

Validated source mappings:

| Entity | Source field |
| --- | --- |
| Total solar production | `TotalActiveProduction:BOL`, falling back to `ActiveProduction:BOL` |
| Total grid imported energy | `METER.APConsumedKWH` |
| Total grid exported energy | `METER.APProductionKWH` |
| Total battery charged energy | `BS.TotalChargingEng` |
| Total battery discharged energy | `BS.TotalDischargingEng` |

Live validation has confirmed the grid lifetime counters are distinct from the
daily grid counters. Continue monitoring for unexpected decreases; the
integration reports decreases but does not clamp or synthesize values.

Do not use daily-resetting entities as Energy Dashboard lifetime sources:

- Grid energy imported today
- Grid energy exported today
- Energy charged today
- Energy discharged today

Runtime diagnostics record whether cumulative fields are detected, missing,
malformed, or decreased, plus sanitized value types. They do not log raw counter
values or device identifiers.

## Manual Installation

1. Copy `custom_components/istore_solar` into your Home Assistant
   `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration from Settings > Devices & services.
4. Choose "Sign in with account" and enter your iStore account/email and
   password, or choose the advanced manual-token fallback.

## HACS Custom Repository Installation

This repository is suitable for use as a HACS custom repository. It is not in
the default HACS repository.

1. In HACS, open Custom repositories.
2. Add this repository URL.
3. Select category Integration.
4. Install iStore Solar.
5. Restart Home Assistant.
6. Add the integration from Settings > Devices & services.

For updates, install the new version manually or through HACS, then restart
Home Assistant. Removing and re-adding the integration is not normally needed.

## Authentication

The recommended setup path is automatic sign-in. Home Assistant fetches the
iStore login public key, encrypts the password locally with RSA-OAEP SHA-256,
signs in, validates the returned access token, and stores the current access
token in the config entry.

Refresh-token behavior is not proven yet. For automatic-login entries, Home
Assistant stores the account/email and password in the config entry so it can
perform one fresh sign-in when the access token expires or is rejected. If that
fresh sign-in fails, Home Assistant starts reauthentication.

Manual bearer-token mode remains available as an advanced fallback. Existing
token-only entries are migrated to explicit `manual_token` mode and do not need
to be removed and re-added.

Switching between automatic sign-in and manual-token mode currently requires
removing and re-adding the integration. Replacing credentials within the current
mode is supported from the integration options flow or reauthentication flow.

## Manual Token Fallback

Chrome:

1. Log in to `https://home.istore.net.au`.
2. Open Developer Tools.
3. Open the Application tab.
4. In Storage, expand Local Storage.
5. Select the iStore site.
6. Copy the value named `dtv_access_token`.
7. Paste it into the Home Assistant setup, reauthentication, or options form.

The access token is a secret. Do not post it in issues, logs, screenshots,
diagnostics, HAR files, or commits. The iStore password is also a secret and is
stored in the Home Assistant config entry only for automatic re-login because
refresh-token support is not implemented yet.

If a manual token expires, replace it from the integration options flow or
complete reauthentication when Home Assistant prompts for a new token. If an
automatic-login token expires, the integration performs one fresh login and
retries the failed request once.

## Troubleshooting

- If setup says credentials are invalid, check the account/email and password,
  or use the manual-token fallback with a fresh `dtv_access_token`.
- If entities become unavailable, check whether the iStore web portal is
  reachable and whether credentials or the manual token have expired.
- Enable debug logging for `custom_components.istore_solar` to inspect sanitized
  request diagnostics.
- Download diagnostics from the integration entry when reporting issues.
- Status code entities remain raw diagnostic values because no confirmed
  code-to-label mapping has been found yet.

Issue reports should include:

- Home Assistant version.
- Integration version.
- Whether the installation is manual or HACS custom repository.
- Sanitized diagnostics.
- Relevant sanitized debug log lines.
- A description of the expected and observed behavior.

Do not include tokens, cookies, site names, addresses, serial numbers, raw HAR
files, or raw API payloads in issues.

## Security

Do not commit HAR files, cookies, tokens, credentials, site IDs, serial numbers,
addresses, or captured API payloads. Private captures and notes should stay
under `private/`, which is ignored by Git.

## Branding

The integration does not bundle an icon or logo. See `docs/branding.md` before
adding any branding assets for public release or HACS presentation.

## License

This project is licensed under the MIT License. See `LICENSE`.
