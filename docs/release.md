# Release And HACS Notes

## HACS

- `hacs.json` is present and renders the README.
- `custom_components/istore_solar/manifest.json` uses semantic versions.
- GitHub releases should be tagged with the same semantic version as the
  manifest.
- Release archives must include `custom_components/istore_solar`.
- Do not include `private/`, HAR files, credentials, tokens, or local Home
  Assistant storage in release artifacts.

## Suggested Repository Topics

These are repository settings, not files:

- `home-assistant`
- `home-assistant-custom-component`
- `hacs`
- `istore`
- `solar`
- `energy-dashboard`

## Release Notes

Release notes should summarize:

- Authentication changes.
- Entity or device naming changes.
- Entity-registry migrations.
- Energy Dashboard compatibility.
- Known limitations.
- Any required Home Assistant restart or migration notes.
