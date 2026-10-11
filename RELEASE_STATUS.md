# Devices 0.6.6 — release status

Updated 2026-10-11. PeriHub is a Windows peripheral control app. This release currently supports the SC900 Pro and K95 RGB Platinum.

## Completed

- Version 0.6.6 saves keyboard effect, color, brightness and speed; applies the saved software effect on first detection after startup; remembers Onboard; preserves the preference through Quit and transient disconnections. All 58 automated regressions pass.

- Version 0.6.5 closes the three issues found in the reliability review: exclusive polling selection with pending controls disabled, sensor writes serialized and verified with connection guards, and strict DPI-stage reply validation including stage 1. All 54 automated regressions pass.

- Version 0.6.4 shortens the battery explanation and displays it on two lines.

- Version 0.6.3 adds a small in-app battery information icon. Hover or click to explain temporary charging-related estimate changes; no extra battery polling is introduced.

- Version 0.6.2 shows device cards only for detected supported hardware, hides absent devices, and shows an empty state when neither is present. Detection errors for one device do not hide the other.

- Transparent white outline tray icon at multiple display sizes. Start with Windows can be enabled or disabled directly from the tray menu; it stays off unless selected.

- Exact SC900 Pro detection over original 8K receiver (093A:522C) and USB wired mode (093A:622C); USB is preferred if both are connected.
- Live DPI stage/value/count, polling, sensor and timing readback. Numeric DPI uses 50-DPI steps. Mouse writes run off the UI thread and verify their relevant readback.
- Passive battery input reports: percentage in the app and a concise tray tooltip; stale readings become unavailable.
- Mouse controls are disabled after a failed read and enabled on successful recovery; unavailable devices are retried without blocking the UI.
- Compact concept-style layout, genuine mouse artwork, line icons, wrapped messages, and no horizontal clipping in reconnect regression tests. Resizing remains available.
- K95 static/off/onboard lighting plus the verified software animations, brightness and speed. Effects continue in the tray, resume after detected reconnect, and normal Quit restores onboard mode.
- Selected device and mouse tab persist between launches. One instance per user, an explicit tray Quit action, and a first-close tray hint.
- Portable Windows executable with Python/Qt bundled. Per-user installer with a Start menu entry, optional desktop shortcut and optional launch at sign-in; both options start unchecked. Uninstall preserves device preferences.
- `--quit` supports graceful installer update/uninstall; `--tray` supports optional startup without showing the main window.

## Verification boundary

Earlier sessions verified keyboard effects visually, receiver and wired mouse settings through readback, and live battery values on this PC. The latest changes have mocked UI/transport regression tests, including a deliberately blocked mouse command while the Qt event loop stays responsive. The installer is tested in a separate directory on this development PC, including update/uninstall. This is not a clean-machine or every-firmware certification.

## Unsupported features and remaining verification

- Mouse button remapping, macros, LED indicator modes, onboard profile import/export, firmware version and firmware flashing. The complete protocols are not verified; no dead controls are shown.
- K95 macros/profile editing and native onboard animation speed. Software animations require the app to keep running. Crash/forced-kill recovery is not guaranteed.
- Independent physical polling-rate measurement, power-cycle persistence, every sleep/wake and unplug-during-command scenario, and clean Windows 10/11 machine testing.
- Physical display-scale review at 125%, 150% and 200%, keyboard artwork/layout confirmation, and measured long-term resource use.
- Public distribution decisions: project license, OEM artwork permission, dependency license bundle and code signing. Source and installers are published on GitHub.
- Linux remains an untested source preview; no Linux binary was built on this Windows PC. Its existing shared archive remains unchanged under Old builds/linux-share.

These items do not prevent the verified personal-use controls from working. They are not claims of completed support.
