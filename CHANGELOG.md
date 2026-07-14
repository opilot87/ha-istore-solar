# Changelog

## 0.3.1

- Corrected `METER.APConsumed` and `METER.APProduction` from experimental
  lifetime grid sensors to daily grid import/export energy sensors.
- Renamed grid energy entity keys to `grid_energy_imported_today` and
  `grid_energy_exported_today`.
- Changed grid energy state class from `total_increasing` to `total` because
  live values resemble daily counters.
- Removed grid energy sensors from the documented Energy Dashboard setup.
- Added an entity-registry migration for the two private experimental grid
  unique IDs where Home Assistant supports it.

## 0.3.0

- Added an options flow for manual access-token replacement and configurable
  polling interval from 15 to 300 seconds.
- Added experimental cumulative energy entities for private Energy Dashboard
  validation.
- Added an experimental meter device when a discovered meter provides at least
  one valid cumulative meter counter.
- Added sanitized diagnostics for polling interval, discovery cache state,
  asset types, entity/source availability, and cumulative-counter observations.
- Added conservative one-shot retries for temporary timeout, network, HTTP 429,
  HTTP 502, HTTP 503, and HTTP 504 failures.
- Improved redaction tests so token-like values cannot leak through diagnostics
  helpers.
- Added HACS custom repository installation notes and troubleshooting guidance.
- Continued manual-token authentication. Token refresh is not implemented
  because the refresh flow is not confirmed.

## 0.2.0

- Added derived grid import/export power sensors.
- Added derived battery charging/discharging power sensors.
- Changed daily battery energy state class from `total_increasing` to `total`.
- Preserved raw diagnostic status-code sensors without invented labels.

## 0.1.0

- Added initial private experimental cloud polling integration.
- Added config flow with manual bearer-token setup.
- Added site discovery from confirmed browser request sequence.
- Added initial live power, battery, daily energy, and status-code sensors.
