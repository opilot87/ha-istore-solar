# iStore Solar for Home Assistant

<p align="center">
  <img
    src="https://raw.githubusercontent.com/opilot87/ha-istore-solar/main/docs/images/istore-logo-blue.png"
    alt="iStore logo"
    width="400"
  >
</p>

## Overview

iStore Solar is a Home Assistant custom integration for the Australian iStore
Solar cloud portal at `home.istore.net.au`.

iStore Solar is an independent community integration and is not affiliated
with, endorsed by, or supported by iStore.

Version 0.6.0 is a public beta. It is read-only, cloud polling based, and
supports automatic account/password sign-in plus an advanced manual access-token
fallback. It exposes live power sensors and validated lifetime energy counters
that can be used with the Home Assistant Energy Dashboard.

This integration is not production-critical software. Do not use it for billing,
grid settlement, safety, or control decisions.

## Supported Devices

The integration has been validated against a residential iStore Solar site with:

- Site
- Inverter
- Battery
- Meter

Other iStore-backed installations may expose different fields or asset types.

## Entities

Core entities:

- Solar power
- Home consumption power
- Grid power
- Grid import power
- Grid export power
- Battery power
- Battery charging power
- Battery discharging power
- Battery state of charge
- Battery charged today
- Battery discharged today
- Grid imported today
- Grid exported today
- Total solar production
- Total grid imported energy
- Total grid exported energy
- Total battery charged energy
- Total battery discharged energy

Diagnostic entities, disabled by default:

- Site status code
- Inverter status code
- Battery status code

Actual entity IDs are assigned by Home Assistant and may differ from examples.
Unique IDs are based on stable site/device identifiers and sensor keys, not on
account names, tokens, cloud display names, or config-entry IDs.

## Installation

### Manual

1. Copy `custom_components/istore_solar` into your Home Assistant
   `custom_components` directory.
2. Restart Home Assistant.
3. Add iStore Solar from Settings > Devices & services.

### HACS Custom Repository

This repository can be installed as a HACS custom repository. It is not in the
default HACS repository.

1. In HACS, open Custom repositories.
2. Add `https://github.com/opilot87/ha-istore-solar`.
3. Select category Integration.
4. Install iStore Solar.
5. Restart Home Assistant.
6. Add iStore Solar from Settings > Devices & services.

HACS releases should use semantic versions and include the
`custom_components/istore_solar` directory in the repository or release archive.

## Setup Using Account/Password

Choose "Sign in with account" during setup.

Home Assistant fetches the iStore login public key, encrypts the password
locally with RSA-OAEP SHA-256, signs in, selects the working session, extracts
the final `session/get` token, and validates it with `user-info`.

Refresh-token support is not implemented because the refresh flow has not been
proven. Automatic sign-in entries store the account and password in the Home
Assistant config entry so the integration can sign in again when the access
token expires.

## Manual Access-Token Fallback

Choose "Use access token manually" only if automatic sign-in is not working.

Chrome:

1. Log in to `https://home.istore.net.au`.
2. Open Developer Tools.
3. Open the Application tab.
4. Expand Local Storage.
5. Select the iStore site.
6. Copy the value named `dtv_access_token`.
7. Paste it into the Home Assistant setup, reauthentication, or options form.

The access token is a secret. Do not post it in issues, logs, screenshots,
diagnostics, HAR files, or commits.

## Energy Dashboard Setup

Recommended Home Assistant Energy Dashboard sources:

| Energy Dashboard slot | Entity |
| --- | --- |
| Solar production | Total solar production |
| Grid consumption | Total grid imported energy |
| Return to grid | Total grid exported energy |
| Battery energy in | Total battery charged energy |
| Battery energy out | Total battery discharged energy |

Do not use daily-resetting entities as lifetime Energy Dashboard sources:

- Grid imported today
- Grid exported today
- Battery charged today
- Battery discharged today

The integration records sanitized diagnostics for detected, missing, malformed,
and decreasing cumulative fields. It does not clamp or synthesize energy values.

## Power Flow Card Plus Example

Replace these generic entity IDs with the IDs created by your Home Assistant
instance.

```yaml
type: custom:power-flow-card-plus
entities:
  solar:
    entity: sensor.istore_solar_site_solar_power
  home:
    entity: sensor.istore_solar_site_home_consumption_power
  grid:
    entity:
      consumption: sensor.istore_solar_site_grid_import_power
      production: sensor.istore_solar_site_grid_export_power
  battery:
    entity:
      consumption: sensor.battery_1_battery_discharging_power
      production: sensor.battery_1_battery_charging_power
    state_of_charge: sensor.battery_1_battery_state_of_charge
```

## Sign Conventions

Confirmed from live Home Assistant observations:

- Grid power positive = importing from grid.
- Grid power negative = exporting to grid.
- Battery power positive = charging battery.
- Battery power negative = discharging battery.

Derived sensors:

- Grid import power = `max(grid_power, 0)`
- Grid export power = `max(-grid_power, 0)`
- Battery charging power = `max(battery_power, 0)`
- Battery discharging power = `max(-battery_power, 0)`

Power values are exposed in kW. Energy values are exposed in kWh.

## Options

Options include:

- Polling interval, 15 to 300 seconds, default 30 seconds.
- Automatic mode: replace account and optionally replace password. Leaving the
  password blank keeps the existing stored password.
- Manual mode: replace access token. Leaving the token blank keeps the existing
  token.

Changing between automatic sign-in and manual access-token mode requires
removing and re-adding the integration.

## Authentication Behaviour

At startup and during polling, the integration uses the latest stored final
access token. If the cloud rejects the token and automatic credentials are
configured, the integration performs one locked fresh sign-in, stores the new
final token, and retries the failed request once.

If automatic sign-in fails, Home Assistant starts reauthentication. Manual-token
entries ask for a replacement access token instead.

Refresh-token support is intentionally not implemented yet.

## Diagnostics

Diagnostics are redacted and include:

- Integration and config-entry version.
- Authentication mode.
- Polling interval.
- Coordinator success and last update duration.
- Entity count by platform.
- Discovered device types.
- Token present true/false.
- Password configured true/false.
- Last auth error class.
- Automatic relogin count.
- Cumulative field availability.

Diagnostics must not include account values, passwords, tokens, public keys,
organization IDs, site IDs, device IDs, serial numbers, addresses, raw payloads,
request IDs, cookies, or Authorization headers.

## Troubleshooting

- If setup says credentials are invalid, check the account/password or try the
  manual access-token fallback.
- If entities are unavailable, check the iStore portal status and whether
  reauthentication is required.
- If Energy Dashboard entities are missing, confirm the meter and battery
  devices were discovered and cumulative fields are available in diagnostics.
- If only optional cumulative entities are unavailable, live power sensors may
  still update normally.
- Enable debug logging for `custom_components.istore_solar` to inspect
  sanitized stage, status, application-code, duration, and exception-class logs.

## Security And Privacy

Never share tokens, passwords, cookies, Authorization headers, raw HAR files,
site IDs, device IDs, serial numbers, NMI values, addresses, or raw API payloads.

Private captures and local notes should stay under `private/`, which is ignored
by Git.

## Known Limitations

- Depends on the iStore cloud portal.
- Refresh-token lifecycle is not implemented.
- iStore API fields may change without notice.
- Read-only integration.
- No local Modbus support.
- No inverter, battery, or site control.
- Multi-site selection is not implemented.
- Status codes remain raw diagnostics because enum labels are not confirmed.
- Supported hardware is based on the tested residential site configuration.
- Entity availability depends on fields returned by the cloud for the site.

## Updating

Install the new version manually or through HACS, then restart Home Assistant.
Removing and re-adding is not normally needed. Existing token-only entries are
migrated to manual access-token mode.

## Removing

Remove the integration from Settings > Devices & services, then remove the
custom component files if installed manually. Home Assistant may retain entity
registry and long-term statistics records according to its normal behavior.

## Contributing

Bug reports and feature requests are welcome. Include sanitized diagnostics and
avoid private values. See `CONTRIBUTING.md` and the issue templates.

## Branding

The integration bundles local iStore brand assets for Home Assistant and HACS
custom-repository presentation. No `manifest.json` key is required for local
brand images. Older Home Assistant versions may still show a generic or
remotely sourced icon.

iStore and its associated logos are trademarks of their respective owners.

## Support development

This integration is developed and maintained independently in spare time.

If it has been useful to you, you can support its ongoing development and
maintenance by [buying me a coffee](https://buymeacoffee.com/opilot87).

Support is entirely optional. All integration functionality remains free and
open source.

## License

MIT. See `LICENSE`.
