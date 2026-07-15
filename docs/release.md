# Release And HACS Notes

## HACS

- `hacs.json` is present, renders the README, and declares `country: AU`.
- `custom_components/istore_solar/manifest.json` uses semantic versions.
- GitHub releases should be tagged with the same semantic version as the
  manifest.
- Release archives must include `custom_components/istore_solar`.
- GitHub source archives contain everything HACS needs; no custom ZIP is needed
  for normal releases.
- Do not include `private/`, HAR files, credentials, tokens, or local Home
  Assistant storage in release artifacts.

## Suggested Repository Topics

These are repository settings, not files:

- `home-assistant`
- `homeassistant`
- `custom-component`
- `hacs`
- `istore`
- `solar`
- `battery`
- `energy-monitoring`
- `australia`
- `energy-dashboard`

Suggested repository description:

`Unofficial Home Assistant integration for iStore Solar inverter and battery systems.`

## Manual Release Steps

Do not create a custom ZIP unless HACS requirements change.

```bash
git status --short
git diff --check
python3 -m unittest discover -s tests
git add .
git commit -m "Prepare v0.6.0 public beta release"
git push origin main
git tag -a v0.6.0 -m "iStore Solar v0.6.0 public beta"
git push origin v0.6.0
```

In GitHub:

1. Set the repository description and topics listed above.
2. Confirm Issues are enabled.
3. Confirm HACS, Hassfest, and test workflows pass on the pushed commit.
4. Draft a release for tag `v0.6.0`.
5. Use `iStore Solar v0.6.0 — Public Beta` as the release title.
6. Paste `docs/release-notes-v0.6.0.md` into the release body.
7. Mark the release as a pre-release while it is a public beta.

## Release Notes

Release notes should summarize:

- Authentication changes.
- Entity or device naming changes.
- Entity-registry migrations.
- Energy Dashboard compatibility.
- Known limitations.
- Any required Home Assistant restart or migration notes.
