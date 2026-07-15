# Branding

The integration includes local brand assets under
`custom_components/istore_solar/brand/`:

- `icon.png`
- `icon@2x.png`
- `logo.png`
- `logo@2x.png`

Home Assistant 2026.3 and newer can use the local brand directory for custom
integrations. HACS custom repositories require at least `brand/icon.png` for
local presentation. No `manifest.json` key is required for these local brand
images.

Older Home Assistant versions continue to load the integration, but may show a
generic icon or use remotely sourced branding instead of the local assets.

iStore Solar is an independent community integration and is not affiliated with,
endorsed by, or supported by iStore.

iStore and its associated logos are trademarks of their respective owners.

Do not commit original unprocessed source artwork from `private/branding/`.
