# iStore Solar for Home Assistant

Experimental Home Assistant custom integration for the Australian iStore Solar
cloud portal at `home.istore.net.au`.

## Status

This repository is under active reverse-engineering. Version 0.1.0 is an
experimental read-only integration that uses an access token copied from the
iStore web portal.

Automatic username/password login and token refresh are not supported yet. The
token may expire, and Home Assistant will ask for a replacement token when the
cloud API rejects it.

Do not use this integration for automation, billing, grid settlement, safety, or
any other critical purpose.

## Planned v0.1.0 Sensors

- Solar power, in kW
- Home consumption power, in kW
- Grid power, in kW
- Battery power, in kW
- Battery state of charge, in %
- Battery energy charged today, in kWh
- Battery energy discharged today, in kWh
- Site, inverter, and battery status diagnostics

Grid power is intentionally not split into import/export sensors until both sign
directions are confirmed. Battery power is intentionally not split into
charge/discharge sensors until both signs are confirmed.

No entities are advertised as Home Assistant Energy Dashboard compatible yet.
Lifetime energy candidates will remain disabled or provisional until monotonic
behavior is verified.

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
diagnostics, HAR files, or commits.

## First Test

After adding the integration, confirm that these entities appear:

- Solar power
- Home consumption power
- Grid power
- Battery power
- Battery state of charge
- Battery energy charged today
- Battery energy discharged today
- Site status
- Inverter status
- Battery status

Grid power is a signed sensor. Negative grid power has been observed during
export. Battery power is also a signed sensor, but its charge/discharge sign
convention remains provisional.

## Security

Do not commit HAR files, cookies, tokens, credentials, site IDs, serial numbers,
addresses, or captured API payloads. Private captures and notes should stay
under `private/`, which is ignored by Git.
