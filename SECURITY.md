# Security Policy

## Reporting A Vulnerability

Please do not open public issues containing credentials, access tokens, cookies,
Authorization headers, site identifiers, serial numbers, addresses, HAR files,
or raw API payloads.

For now, report security-sensitive issues privately to the repository owner. If
private reporting is not available on the repository, open a minimal public issue
stating that you have a security concern without including sensitive details.

## Supported Versions

This project is currently a public beta. Security fixes target the latest
published beta version.

## Credential Handling

Automatic sign-in stores the iStore account and password in the Home Assistant
config entry because refresh-token support has not been proven. The integration
must never write credentials, encrypted password payloads, public keys, tokens,
or raw session responses to files, diagnostics, logs, tests, or documentation.
