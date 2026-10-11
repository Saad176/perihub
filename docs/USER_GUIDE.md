# PeriHub 0.6.6

A compact Windows tray app for peripheral settings, battery monitoring and keyboard lighting.

Currently supported devices: AULA SC900 Pro and Corsair K95 RGB Platinum. Additional devices can be supported as their controls are implemented and tested.

## Install or run

Open `Latest build\Devices-0.6.6-Setup.exe`. It installs for your Windows user, bundles Python and Qt, and creates a Start menu entry. Desktop shortcut and start-at-sign-in are optional and unchecked by default. There is no runtime dependency on AULA, iCUE, OpenRGB, PowerShell, a cloud service, or a separately installed Python.

For portable use, open `Latest build\Devices\Devices.exe` and keep the whole folder together. Quit any older copy from its tray menu before opening an update. The EXE alone is not portable: its `_internal` folder contains the required runtime and assets. To share a single file, use the Setup EXE.

Close hides the window in the tray when a tray is available. The tray icon is a white outline on a transparent background. Right-click it for Open, battery status, Start with Windows and Quit; without a tray, closing exits. Enable **Start with Windows** in the tray menu, or select **Start Devices when I sign in** during installation. It launches quietly in the tray using `--tray`. Untick the tray option to disable it. For portable use, keep the folder in its permanent location before enabling startup; if you move it, enable startup again from the new location. Windows Settings > Apps > Startup also lets you disable Devices. Startup is never enabled automatically. The installer and uninstaller use `--quit` for graceful shutdown. Uninstall preserves your preferences.

## Controls

SC900 Pro: live readback of 1-6 DPI stages, active stage, 50-DPI value steps, polling from 125 to 8000 Hz, LP/HP/Corded sensor modes, 1/2 mm LOD, Ripple Control, Angle Snapping, Motion Sync, debounce, and dormancy. DPI fields accept typing and arrow keys; sliders drag finely in 50-DPI steps. Colored squares select a stage. Refresh reads changes made with the physical DPI button or AULA's software.

The original receiver is `093A:522C`; wired USB is `093A:622C`. USB takes priority if both are connected. The panel and tray identify the active connection. Passive input reports supply battery percentage; the first reading may take several seconds. After two minutes without a valid report, battery becomes unavailable. Polling changes can briefly interrupt the mouse as it reconnects, even though the UI remains responsive.

Mouse writes run in one background queue and check relevant readback before showing success. Controls are disabled when settings cannot be read and enabled after recovery. Reconnect error messages wrap within the panel, so they cannot push DPI values out of view.

K95: Onboard restores its saved animation. Static, Breathe, Rainbow, Soft Rainbow, Wave, Spectrum, Twinkle and Off are software effects with color, brightness and speed where applicable. Onboard brightness uses the physical keyboard brightness key; the app does not edit its saved animation speed. Lighting effect, color, brightness and speed are remembered locally and restored automatically when the keyboard is detected after app startup or reconnect. Selecting Onboard is also remembered. Software effects continue in the tray. Normal Quit restores onboard lighting without erasing the saved software preference; the next launch reapplies it. Competing lighting software can override this app.

## Window and preferences

Default size is 620 x 800, minimum 620 x 640. The window stays resizable. The title bar supports dragging, pinning, minimize/maximize and hiding. Device and mouse tab selection are remembered. Preferences use the current user's Qt settings location, not the install directory. Only detected supported devices and their verified controls appear.

## Build from source

Python 3.10+ is required only for development:

```powershell
python -m pip install -r requirements.txt
pythonw app.py
```

Portable build:

```powershell
python -m pip install pyinstaller
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

Installer build requires Inno Setup (see `build-release.ps1` for compiler locations):

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build-release.ps1
```

Verification uses `python -m unittest discover -s tests -q` and `python tests/smoke_exe.py "Latest build\Devices\Devices.exe"`. Tests mock hardware unless a tool explicitly says it is a live hardware check.

## Remaining support

Button remapping, macros, mouse LED modes, onboard profile editing, firmware reporting/flashing and K95 macro controls are not implemented. Firmware flashing is outside the planned scope. Bluetooth has not been verified. [RELEASE_STATUS.md](../RELEASE_STATUS.md) lists remaining public-release checks, and [PROTOCOL_NOTES.md](../PROTOCOL_NOTES.md) records packet provenance and live hardware evidence.

The Linux archive in `Old builds/linux-share` remains a separate, older source preview. It has setup notes and a Linux build script, but was not built or tested on Linux here. The supplied AULA artwork is included for this personal build; confirm licensing before a public release.

## Project folders and backup

- **Latest build/**: current Windows installer and the complete portable Devices folder. Open the installer, or Devices/Devices.exe for portable use.
- **Old builds/**: build intermediates, installer test logs, UI previews and the older Linux source package. These are kept for reference; nothing here is required to run the current Windows app.
- Source Python files, assets, tests, installer scripts and documentation stay in the project root and their existing development folders. `.build-tools` contains the local installer compiler; `helping stuff` contains the supplied AULA reference software.

The main public repository at https://github.com/Saad176/perihub preserves source, assets, requirements, tests, build scripts, installer definitions and documentation. The .gitignore excludes generated builds, caches, local tools and the AULA reference software. Keep a second backup of the whole folder if you want to preserve those excluded reference files too. Attach the Setup EXE to a GitHub Release to keep a ready-to-install copy alongside a version of the source. Before a public release, resolve the license/artwork items listed in RELEASE_STATUS.md.

Device cards appear only while the corresponding supported hardware is detected. Other mice and keyboards are not listed as these devices.

### Battery estimate information

Hover over or click the small circled information icon beside the mouse battery to learn why the reported estimate may rise while charging and take a few minutes to settle after unplugging. The tray keeps its concise battery display.
