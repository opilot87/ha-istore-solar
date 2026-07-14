# iStore Solar for Home Assistant

Experimental Home Assistant custom integration for the Australian iStore Solar
cloud portal at `home.istore.net.au`.

## Status

This repository is under active reverse-engineering. Version 0.2.0 is an
experimental read-only integration that uses an access token copied from the
iStore web portal.

Automatic username/password login and token refresh are not supported yet. The
token may expire, and Home Assistant will ask for a replacement token when the
cloud API rejects it.

Do not use this integration for automation, billing, grid settlement, safety, or
any other critical purpose.

## v0.2.0 Sensors

- Solar power, in kW
- Home consumption power, in kW
- Grid power, in kW, signed
- Grid import power, in kW
- Grid export power, in kW
- Battery power, in kW, signed
- Battery charging power, in kW
- Battery discharging power, in kW
- Battery state of charge, in %
- Battery energy charged today, in kWh
- Battery energy discharged today, in kWh
- Site, inverter, and battery status code diagnostics

Grid power follows the sign convention observed in live Home Assistant testing:
positive values are grid import and negative values are grid export. The derived
grid sensors are:

- Grid import power = `max(grid_power, 0)`
- Grid export power = `max(-grid_power, 0)`

Battery power follows the sign convention observed in live Home Assistant
testing: positive values are battery charging and negative values are battery
discharging. The derived battery sensors are:

- Battery charging power = `max(battery_power, 0)`
- Battery discharging power = `max(-battery_power, 0)`

The daily battery energy sensors come from daily-resetting API fields. They are
reported as daily totals and are not intended to be used as lifetime Home
Assistant Energy Dashboard sources.

The site, inverter, and battery status entities intentionally expose raw numeric
codes only. Captured responses have shown codes such as `0`, `1`, and `2`, but
the API evidence does not yet include a confirmed enum mapping. Labels such as
online, running, charging, or fault are therefore not invented.

No entities are enabled as Home Assistant Energy Dashboard lifetime sources yet.
Candidate cumulative fields still need longer validation for monotonic behavior
and reset semantics:

- `TotalActiveProduction:BOL`
- `ActiveProduction:BOL`
- `BS.TotalChargingEng`
- `BS.TotalDischargingEng`
- `METER.APConsumed`
- `METER.APProduction`

## Manual Installation

1. Copy `custom_components/istore_solar` into your Home Assistant
   `custom_components` directory.
2. Restart Home Assistant.
3. Add the integration from Settings > Devices & services.
4. Paste the `dtv_access_token` value when prompted.

At this stage setup is experimental. Multi-site support is incomplete, and the
integration uses the first residential solar site it can discover from the
confirmed API responses.

## Getting The Access Token

Chrome:

1. Log in to `https://home.istore.net.au`.
2. Open Developer Tools.
3. Open the Application tab.
4. In Storage, expand Local Storage.
5. Select the iStore site.
6. Copy the value named `dtv_access_token`.
7. Paste it into the Home Assistant iStore Solar setup form.

The access token is a secret. Do not post it in issues, logs, screenshots,
diagnostics, HAR files, or commits. Manual bearer-token setup is temporary:
automatic username/password login, token refresh, and token storage hardening
are not implemented yet.

## First Test

After adding the integration, confirm that these entities appear:

- Solar power
- Home consumption power
- Grid power
- Grid import power
- Grid export power
- Battery power
- Battery charging power
- Battery discharging power
- Battery state of charge
- Battery energy charged today
- Battery energy discharged today
- Site status code
- Inverter status code
- Battery status code

Grid power is a signed sensor. Negative grid power has been observed during
export and positive grid power has been observed during import. Battery power is
also signed: positive values have been observed while charging and negative
values have been observed while discharging.

## Security

Do not commit HAR files, cookies, tokens, credentials, site IDs, serial numbers,
addresses, or captured API payloads. Private captures and notes should stay
under `private/`, which is ignored by Git.
