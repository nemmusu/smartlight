# Contributing

[English](CONTRIBUTING.md) · [Italiano](CONTRIBUTING.it.md)

Start with a small issue or change. Include your OS, Smartlight version, backend and device model. Describe expected and actual behavior. Remove credentials, tokens, network addresses and personal names from logs or screenshots.

## Development

Use Python 3.12+ in a virtual environment and install `requirements.txt`. Linux also needs the desktop packages in [LINUX.md](LINUX.md). Run `python app.py` to open the app.

## Tests without hardware

```sh
python -m unittest discover -p "test_*.py" -v
python test_ui_contract.py --serve --rich
```

The second command serves a local demonstration with simulated Tapo/PC devices. It never controls physical lights. The `verify_*_live.py` helpers are separate and may control real hardware: read them before running.

For browser checks, install Node.js, run `npm install` and `npx playwright install chromium`, then pass the printed local demo URL to `npm run test:ui -- <URL>` or `npm run test:i18n -- <URL>`. `npm test` runs the lightweight scope checks.

Keep UI labels in both Italian and English. Preserve user-defined names and stable protocol values. Cover changes to backend routing, settings persistence and SDK failure handling with meaningful tests.

Vendor SDK files and real device configurations must not be committed. Use the clean repository export rather than uploading the entire development folder.
