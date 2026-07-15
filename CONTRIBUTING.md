# Contributing

Thanks for helping improve iStore Solar for Home Assistant.

## Development Scope

This integration is read-only and cloud-polling based. Public-beta work should
prioritize stability, diagnostics, Home Assistant conventions, and privacy.

Avoid adding control/write operations or refresh-token support until there is
confirmed API evidence and tests.

## Privacy Rules

Never commit or paste:

- Account details, passwords, tokens, cookies, or Authorization headers.
- Public keys captured from real accounts.
- Site IDs, device IDs, organization IDs, serial numbers, NMI values, addresses,
  or coordinates.
- Raw HAR files, raw API payloads, screenshots containing private values, or
  live debug logs with identifiers.

Keep private captures under `private/`, which is ignored by Git.

## Tests

Use fake identifiers, fake credentials, and artificial keys only. Run:

```bash
python3 -m unittest discover -s tests
python3 -m json.tool custom_components/istore_solar/manifest.json
git diff --check
```

## Documentation

Document user-facing behavior in `README.md` and release-facing changes in
`CHANGELOG.md`. Keep known limitations current.
