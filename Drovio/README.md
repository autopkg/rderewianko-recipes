# Drovio Recipes

Drovio now provides a universal binary (since v3.3.0), so use these recipes:

- `drovio.download` - Downloads the latest version
- `drovio.pkg` - Creates an installer package
- `drovio.munki` - Imports into Munki

The ARM-specific recipes (`drovio.arm.*`) are deprecated.

## SERVER_URL Override

The pkg recipe requires a `SERVER_URL` override for your Drovio server:

```
autopkg make-override drovio.pkg
```

Then edit the override to set `SERVER_URL` to your server address.
