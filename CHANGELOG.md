# Changelog

## 0.5.1

- Fixed automatic-login setup when the successful login response contains
  `data.accessToken` and an `organizations` list rather than a final
  `session/get` token or scalar `orgId`.
- Accepted successful empty or minimal login bodies while still requiring
  `session/get.data.id` and `user-info` token validation before setup succeeds.
- Added sanitized debug logging for each automatic-authentication stage.

## 0.5.0

- Added automatic account/password login using the confirmed RSA-OAEP
  SHA-256 password transformation.
- Added automatic one-shot re-login when an automatic-login entry receives an
  authentication failure.
- Kept manual bearer-token setup as an advanced fallback.
- Migrated existing token-only entries to explicit `manual_token` auth mode
  without requiring remove/re-add.
- Added sanitized authentication diagnostics and redaction coverage for account,
  password, encrypted password, public key, token, and session metadata.
- Refresh-token support remains unimplemented; automatic entries store the
  password in the Home Assistant config entry so they can sign in again.

## 0.4.0

- Promoted validated meter lifetime counters to `Total grid imported energy`
  and `Total grid exported energy`.
- Added full documented Home Assistant Energy Dashboard mapping for solar, grid
  import/export, and battery charge/discharge lifetime energy.
- Added entity-registry migration from the v0.3.2 experimental grid lifetime
  keys to the stable v0.4.0 keys.
- Kept daily grid and battery energy counters separate from lifetime Energy
  Dashboard sources.
- Removed internal platform model IDs from Home Assistant hardware-version
  metadata.
- Updated public-readiness, troubleshooting, privacy, HACS, and branding
  documentation.

## 0.3.2

- Added disabled-by-default experimental meter lifetime candidates sourced from
  `METER.APConsumedKWH` and `METER.APProductionKWH`.
- Added optional `Res_Meter` measurement-point retrieval using the confirmed
  `asset/list` request shape.
- Kept daily grid energy sensors unchanged and continued excluding grid meter
  candidates from the documented Energy Dashboard setup.
- Reused sanitized cumulative diagnostics for detected, missing, malformed, and
  decreased candidate fields without logging raw values or device identifiers.

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
