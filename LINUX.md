# Smartlight on Linux

English · [Italiano](LINUX.it.md) · [Home](README.md)

Linux and Windows share the same source code. `version.txt` is the common version source, currently 0.4.3. The UI, effects, presets, groups, schedules, MCP server, tray command queue and keyboard restoration fixes are shared.

On Linux, PC lighting uses **OpenRGB only**, including Corsair devices. Windows also supports iCUE and experimental MSI Mystic Light. Devices with identical OpenRGB names receive distinct numbers. A Corsair hub may appear as a single controller in OpenRGB even when iCUE exposes several lighting blocks.

Smartlight has been tested on Windows and Linux with devices from its supported integrations. The OpenRGB catalog describes upstream support; it does not mean every listed model was individually tested with Smartlight.

The default language is **English**. Switch between **English and Italiano** anytime in **Settings → General → Language**. Your choice is saved, and Help offers the same language selector.

## Startup and data

- Leave **Automatic** selected, or choose **OpenRGB** in PC lighting setup. Both use OpenRGB on Linux, including for Corsair. After a change, select **Apply and restart**.
- Smartlight detects OpenRGB and tries to start its SDK server at `127.0.0.1:6742`. If the app is missing or the server cannot be reached, Smartlight shows the status and the next step. Linux does not use iCUE, the MSI SDK or manual DLL paths. OpenRGB still needs the hardware permissions required by your distribution.
- If OpenRGB is already running without its server, open **SDK Server → Start Server**, use port **6742**, then select **Detect again** in Smartlight. Smartlight does not open a second copy.
- Installed software alone does not mean **Ready**: actual controllable devices must be detected.
- State and settings: `$XDG_DATA_HOME/Smartlight`, or `~/.local/share/Smartlight`.
- Login startup: the XDG entry `smartlight.desktop` in `$XDG_CONFIG_HOME/autostart`, or `~/.config/autostart`.
- Tapo credentials use the system keyring. MCP tokens are excluded from backups and use user-only file permissions on Linux.
- `python app.py --mcp-stdio` starts the stdio server without a window. Configure HTTP in the app settings.

## Run from source

On Ubuntu 24.04, you need Python 3.12 with venv, GTK3, PyGObject and WebKit2 4.1. Clipboard support uses `wl-clipboard` on Wayland or `xclip` on X11. A system keyring must be available in the desktop session.

```sh
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

The platform condition in `requirements.txt` installs iCUE dependencies only on Windows.

## Packages

Run the builder **on Linux**, from the source root. Both platform builders read `version.txt`; a build does not automatically change the other platform's version.

```sh
python3 installer/linux/build_linux.py --skip-appimage
python3 installer/linux/build_linux.py
```

The first command builds the `.deb`. The second also builds an AppImage when appimagetool is available. Artifacts are written to `dist/`. To start a new release, use `--bump patch` or explicitly update `version.txt`, then build both platforms.

The `.deb` declares its system dependencies. Install it with `sudo apt install ./Smartlight_0.4.3_amd64.deb`. The AppImage still depends on the Python version and GTK/WebKit system libraries used by the builder; it is not universal across distributions.

Source packages exclude virtual environments, personal data and old executables.
