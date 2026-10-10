<div align="center">

# PeriHub

A compact Windows tray app for peripheral settings, battery monitoring and keyboard lighting.

![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-4caceb?style=flat-square)
![Version](https://img.shields.io/badge/version-0.6.4-55d076?style=flat-square)

[![Download PeriHub for Windows](images/download-windows.svg)](https://github.com/Saad176/perihub/releases/latest/download/Devices-0.6.4-Setup.exe)

**[Download setup directly](https://github.com/Saad176/perihub/releases/latest/download/Devices-0.6.4-Setup.exe)** · [Release notes](https://github.com/Saad176/perihub/releases/latest)

Everything you need is included in the installer.

</div>

---

## Get the app

1. Click **Download for Windows** above. The Setup EXE downloads directly.
2. Run the downloaded **`Devices-0.6.4-Setup.exe`**.
3. Open **Devices** from the Start menu.

**That single Setup EXE includes everything you need.** The automatically generated **Source code** ZIP and TAR files are for development; they are not the installer.

Desktop shortcuts and startup are optional. To launch quietly when you sign in, right-click the tray icon and tick **Start with Windows**. Closing the window keeps the app in the tray; **Quit** exits it.

This is the main PeriHub repository: source, tests, build scripts and documentation. Installers are distributed through Releases; cloning this repository restores the source needed to rebuild the app.

## A small control panel with character

<table>
<tr>
<td width="50%" align="center"><b>Mouse</b></td>
<td width="50%" align="center"><b>Keyboard</b></td>
</tr>
<tr>
<td><img src="docs/images/mouse.png" alt="Devices mouse settings with six compact DPI stages" width="420"></td>
<td><img src="docs/images/keyboard.png" alt="Devices keyboard lighting controls and effect selection" width="420"></td>
</tr>
</table>

*Representative interface previews use fixture data. Connection, battery and settings reflect your hardware when running the app.*

## Currently supported devices

Support is added per device as its controls are implemented and tested. The current release supports:

| Device | Connection | Available controls |
| :--- | :--- | :--- |
| **AULA SC900 Pro** | Original 8K receiver or USB wired | 1–6 DPI stages, 50-DPI increments, active stage, polling, sensor mode, LOD, Motion Sync, Ripple Control, Angle Snapping, debounce and dormancy |
| **Corsair K95 RGB Platinum** | USB | Onboard restore, Static, Breathe, Rainbow, Soft Rainbow, Wave, Spectrum, Twinkle and Off; brightness, speed and color where applicable |

Have a different device? [Request support](https://github.com/Saad176/perihub/issues/new) with its exact model and connection type. Devices outside this list are not supported yet.

### Mouse details

- Polling selections: **125 / 250 / 500 / 1000 / 2000 / 4000 / 8000 Hz**.
- Type a DPI value, use arrow keys or drag in fine **50-DPI steps**.
- Set the stage count and use the mouse's physical DPI button to cycle stages.
- Battery percentage appears in the app and in the concise tray hover text.
- Wired USB takes priority when both the cable and receiver are present.
- Writes run off the UI thread, with relevant readback checks before success is shown.

### Tray and lighting

- Transparent white outline tray icon.
- One running instance per Windows user.
- Optional **Start with Windows**, with no window popping up at sign-in.
- Keyboard software animations continue while the window is hidden.
- Normal Quit restores the keyboard's saved onboard lighting.
- Device and mouse-tab selections are remembered.
- Device cards and settings appear only when supported hardware is detected. When no supported devices are present, the app shows an empty state. Plugging or unplugging devices updates the list automatically.

## Things to know

Battery reports can take a few seconds to arrive; stale readings become unavailable. Polling changes can briefly interrupt the mouse while its transport reconnects. Keyboard software effects require the app to remain running, and other lighting software can override them.

Compatibility and available controls depend on the device and release. Mouse button remapping, macros, LED modes, profile editing, Bluetooth and firmware flashing are not verified or implemented in this release. See [release status](RELEASE_STATUS.md) for the exact verification boundary.

## Run or build from source

Python is required for development only.

```powershell
python -m pip install -r requirements.txt
pythonw app.py
```

Build the portable app:

```powershell
python -m pip install pyinstaller
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

Build the installer with Inno Setup installed:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build-release.ps1
```

Output: **`Latest build/Devices/Devices.exe`** and **`Latest build/Devices-0.6.4-Setup.exe`**. Portable use requires the complete **Devices** folder, including `_internal`.

Run regression tests:

```powershell
python -m unittest discover -s tests -q
```

## Inside the project

| Path | Purpose |
| :--- | :--- |
| `app.py`, `ui_components.py` | Desktop UI, tray and application lifecycle |
| `mouse_direct.py`, `mouse_commands.py`, `mouse_battery.py` | Mouse transport, verified commands and passive battery reports |
| `keyboard_direct.py` | K95 lighting and software effects |
| `windows_startup.py` | Optional per-user Windows startup |
| `assets/` | App icon and device artwork |
| `images/`, `docs/` | Repository screenshots and guides |
| `tests/`, `devtools/` | Regression tests and development tools |
| `installer/`, `build*.ps1` | Windows packaging |
| `Latest build/`, `Old builds/` | Local generated output and archives; excluded from Git |

## Documentation

- [User guide](docs/USER_GUIDE.md)
- [Current release notes](docs/releases/v0.6.4.md)
- [GitHub setup and release guide](docs/GITHUB_GUIDE.md)
- [Protocol notes](PROTOCOL_NOTES.md)
- [Release status and remaining work](RELEASE_STATUS.md)
- [Requirements and roadmap](REQUIREMENTS.md)
- [Third-party notices](THIRD_PARTY_NOTICES.md)

## Recover the project or sync changes

If the local folder is gone, clone a fresh copy:

```powershell
git clone https://github.com/Saad176/perihub.git
cd perihub
python -m pip install -r requirements.txt
```

For an existing checkout, use `git pull --ff-only`. To save work to GitHub, commit it and push it. Only committed and pushed files can be restored by cloning; local caches, installers and supplied vendor reference software are excluded. Installers belong in GitHub Releases.

## Project status

PeriHub is an independent peripheral control project. The current device integrations have been verified on the developer's hardware; broader hardware testing is ongoing work. The project is not affiliated with device manufacturers.

Source is available for inspection, but no open-source license has been granted. OEM device artwork and dependencies retain their respective rights; unresolved distribution items are listed in [release status](RELEASE_STATUS.md). The older Linux source preview remains a separate local archive, not a Windows release asset.
