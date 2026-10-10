# Devices — finished app requirements

**Status:** personal-use Windows release 0.6.2; this document defines the broader public-release target. See RELEASE_STATUS.md for verified completion and remaining gates.
**Initial platform:** Windows 11 x64, with Windows 10 x64 support before a public release.
**Initial hardware:** Corsair K95 RGB Platinum (USB `1B1C:1B2D`) and AULA SC900 Pro with its 2.4 GHz PixArt receiver (USB `093A:522C`, HID product string `SC900PRO`).

## 1. Product goal

Create one small, reliable Windows tray app that recognizes these two devices and offers their useful, verified settings in one interface. The user should be able to install it, open it from an icon, change a setting, and see that change on the device without running iCUE, AULA's software, OpenRGB, Python, or a separate background server.

The concept screenshots in the conversation define the visual direction: a compact dark device window, narrow device list on the left, selected device on the right, restrained blue selection color, thin grey borders, monospaced labels, clear status, device image, and controls grouped into focused tabs. The example Keychron, gamepads, system monitor, and floating panels are **not** part of this two-device release. Device-specific settings must come from the actual hardware, not from the example screenshot.

## 2. Scope and priorities

Priority definitions: **P0** is required for a release for this user; **P1** is required before calling it a polished public release; **Later** is optional expansion.

| Priority | Requirement |
| --- | --- |
| P0 | Detect both exact devices; distinguish a plugged-in mouse receiver from a paired, responding mouse. |
| P0 | Apply and verify K95 static RGB color and lights-off; restore its onboard lighting profile. |
| P0 | Read, edit, apply, and verify SC900 Pro DPI stages and polling rate over its wired or 2.4 GHz interface. |
| P0 | Match the concept's main-window structure and visual character, using accurate images for both devices. |
| P0 | Run from a tray icon, install and launch without a terminal or a user-installed Python runtime. |
| P0 | Never present a control as functional when its device command has not been verified. |
| P1 | Support the other SC900 Pro options confirmed in its installed vendor software and validated on this model. |
| P1 | Support useful K95 lighting controls beyond one static color, where direct control is verified. |
| P1 | Handle sleep, reconnect, competing software, failures, and clean installation/uninstallation. |
| Later | A reviewed device-driver/plugin interface, more devices, community contributions, and AI-assisted driver development. |

## 3. Device discovery and status

- Enumerate HID/USB devices using exact vendor/product IDs and confirm the expected interface and product string. Do not identify every PixArt `093A:522C` receiver as an SC900 Pro without the `SC900PRO` string.
- Show keyboard status as **Connected** only when its lighting interface is available.
- Show mouse states separately: **Receiver found**, **Mouse connected and responding**, and **Unavailable/disconnected**. Merely seeing the dongle is insufficient to claim the mouse is connected, paired, or charged.
- Refresh when devices arrive or leave, and after wake from sleep. Avoid repeated expensive full-system scans.
- Show firmware, battery, connection mode, current DPI, or current polling rate only when a verified readback command supplies the value. Unknown values must be shown as unknown, not guessed.
- If a device is unavailable, disable its write actions and explain why in the UI.

## 4. Corsair K95 RGB Platinum

### Required controls

- Apply a selected static color to the keyboard LEDs through the K95's HID lighting interface.
- Switch lights off and return to the keyboard's onboard lighting profile.
- Show clear feedback for success or failure. A successful USB write alone is not proof that the visible lighting changed; validate on hardware.
- Preserve normal typing, media keys, profile switching, brightness key, and Windows-lock key.
- On quit, crash, reconnect, and wake, define and test whether the app restores the onboard profile or reapplies its last chosen color. The user's chosen behavior should be predictable.

### Further controls, only after verification

- Brightness and supported RGB effects; per-key or zone lighting if the UI remains simple and readback/behavior can be checked.
- Macro G-key assignment and hardware profile editing require separate protocol research and safe tests. They are not implied by the current RGB support.
- Do not show adjustable actuation distance: the K95 Platinum has fixed mechanical switches. Do not show an arbitrary keyboard polling-rate selector; the product's documented report rate is 1000 Hz.

## 5. AULA SC900 Pro

The user's installed AULA driver and screenshot show these categories. Each option must be mapped to a verified SC900 Pro command before it becomes editable. The screenshot shows six DPI stages (400, 800, 1600, 3200, 6400, 26000), 1000 Hz selected, HP sensor mode, 1 mm LOD, Motion Sync on, and Ripple Control and Angle Snapping off. These are **observations of that screenshot**, not values to hardcode as current device state.

### P0: DPI

- Read the number of active stages, each stage value, and the selected stage if the device protocol exposes them.
- Allow selecting a stage, changing its DPI, and choosing the supported stage count (the installed driver shows up to six).
- Enforce device-reported or experimentally verified DPI bounds and increments; avoid arbitrary slider values the device cannot represent.
- Apply to the mouse, read back or otherwise verify the result, and confirm that it persists across reconnect/reboot as intended.
- Clearly distinguish **editing a DPI stage** from **switching the active stage**.

### P0: polling

- Offer only rates supported in the active connection mode. The installed driver shows 125, 250, 500, 1000, 2000, 4000, and 8000 Hz.
- Apply the selected rate and verify it through device readback and an independent report-rate test where practical.
- Warn only when a specific selected rate cannot be used with the current dongle, connection mode, or firmware.

### P1: other verified settings

- Sensor mode: LP, HP, or Corded as supported by the current connection.
- Lift-off distance: 1 mm or 2 mm if both are supported.
- Debounce time, Motion Sync, Angle Snapping, and Ripple Control.
- Button assignments, DPI switching actions, and supported macros, with safeguards against disabling all primary click actions.
- LED/indicator behavior supported by the device: battery warning/status, connection and polling indicators, DPI indication, and off. Do not label the mouse as full RGB if only indicator lighting is exposed.
- Sleep/dormancy time, profiles, import/export, and reset only after safe protocol validation.
- Battery level and firmware version only if actual device readback supports them.

## 6. Mouse protocol work required

The implemented protocol now supports wired and receiver settings readback, all seven polling choices, DPI stage/count/value edits, sensor/timing settings and passive battery reports. Those commands have live hardware evidence in PROTOCOL_NOTES.md. Further protocol expansion must follow this procedure:

1. Record the AULA driver's HID traffic while changing **one setting at a time**. Record before/after values and whether the mouse is wired or using the receiver. The local driver uses HID feature reports, but the observed periodic report is not a decoded settings write.
2. Identify the correct HID interface, report IDs, message lengths, checksums, request/response pairs, and whether an explicit save command is required.
3. Implement read-only queries first. Confirm that decoded values match the AULA driver.
4. Implement one reversible write at a time, starting with a DPI stage and polling rate. Read back and test physical behavior.
5. Test interrupted writes, unplugging, sleep, pairing loss, and switching between wired and receiver modes.
6. Keep the AULA driver closed during normal use of this app if the two programs conflict. The released app must not depend on it.

Do not guess report bytes or repeatedly send unverified commands to the mouse. Do not implement firmware flashing as part of this app.

## 7. Interface and interaction

- One main window modeled on the cropped concept screenshot. Use the broader screenshot for the tray behavior and overall feel, not for extra system/gamepad panels.
- Left column: exactly these two devices for the initial release, with recognizable icons, type, and truthful connection state. The scan action may remain if it provides a useful immediate refresh.
- Right column: device name and status, accurate device image, concise model/connection details, tabs, and controls. Keep controls inside the window at common Windows display scales (100%, 125%, 150%, 200%); no horizontal scrolling or clipped values.
- Mouse tabs should expose verified DPI, Polling, Buttons, LED, and Sensor settings. Unsupported tabs or actions should be omitted or explicitly marked unavailable during development; release UI should avoid dead controls.
- Keyboard tabs should show only working lighting and settings. The bundled K95 image should still be compared with the physical keyboard and regional layout before a public release.
- Use readable contrast, keyboard navigation, tooltips for unfamiliar settings, and a visible focus state. Avoid hiding save/apply behavior.
- Show pending changes, apply success, and device errors in the window. Do not silently swallow USB failures.
- Preserve the chosen device/tab when the window is reopened from the tray.
- Closing the window hides it to the tray; tray menu provides Open and Quit. On first close, explain where the app went once. Do not make it impossible to exit.
- No desktop shortcut or launch-at-login entry by default. Both may be optional installer/settings choices.

## 8. Performance and architecture

- One application process is the target; no mandatory iCUE, AULA, OpenRGB, network server, cloud account, or online connection at runtime.
- Keep idle CPU effectively at rest and memory/install size reasonable for a two-device utility. Measure actual startup time, idle RAM/CPU, and packaged size before deciding whether the Python/Qt prototype is suitable for release or should be ported to a smaller native stack.
- Separate UI, device discovery, K95 transport, SC900 Pro transport, settings persistence, and packaging code. A device error must not freeze the UI.
- Serialize writes per device and avoid simultaneous controllers fighting over one HID interface.
- Store user preferences under the user's Windows application-data directory; do not write into the installation directory. Do not fabricate device state from saved preferences.
- Keep diagnostics local and opt-in to share. No telemetry is required.
- Protocol implementations should identify their source/research notes and be reviewed before distribution. OpenRGB was used as a reference for K95 packet structure; it is **not** a runtime dependency.

## 9. Installer and release

- Provide a Windows `.exe` and an installer that includes the required runtime and assets. End users must not install Python or run PowerShell commands.
- Create a Start menu entry and an app/tray icon. Offer a desktop shortcut only if selected by the user.
- Install and uninstall cleanly without removing user settings unless the user chooses to remove them. Support an in-place update path.
- Run as a normal user if possible. If a specific operation needs elevation, explain exactly why; do not require administrator rights for ordinary color/DPI/polling changes.
- Package both device images within the app. The current images are generated artwork; compare their physical details with the real devices before release.
- Include a version number, license, source attribution, concise setup/help text, and a way to report a device/firmware compatibility problem.
- If distributed publicly, evaluate code signing and Windows reputation behavior; signing is not needed to validate a local prototype.

## 10. Verification and release gates

The first release is complete only when all P0 items pass on the user's hardware and on a clean Windows installation:

- Fresh install, Start menu launch, tray open/hide/quit, and uninstall work without Python, AULA, iCUE, or OpenRGB installed.
- Both devices appear with correct IDs. Unplugging each changes only its own status; plugging it back restores control.
- K95 color and lights-off visibly work. Restore returns to an onboard profile. Typing and special keys still work.
- SC900 Pro DPI stage selection and value editing visibly affect the mouse and read back correctly. Chosen values survive the expected reconnect/restart path.
- SC900 Pro polling selection readback matches the choice, and measured reports are consistent with that choice under appropriate movement/load.
- Failure cases (mouse asleep, receiver only, driver conflict, HID access denied, unplug during apply) show useful errors and leave the app responsive.
- The layout is inspected at common scaling factors and compared with the concept screenshots; no clipping, stale values, or misleading placeholders remain.
- A clean-install test confirms all photos/assets are present and no local AULA installation path is needed.

## 11. Current release versus target

| Area | Current state | Remaining |
| --- | --- | --- |
| Detection | Exact K95 interface, SC900 receiver and wired mouse; USB priority and connection recovery. | Clean-machine, sleep/wake and firmware coverage. |
| K95 lighting | Static/off/onboard plus software effects, brightness/speed, tray operation and reconnect resume. | Forced-kill recovery, macro/profile protocols and artwork confirmation. |
| Mouse controls | Live settings readback, all DPI and polling options, sensor/timing controls, passive battery and asynchronous verified writes. | Button/LED/profile protocols, firmware reporting, power-cycle checks and measured polling timing. |
| Visuals | Reference-style compact UI, line icons, compact details, wrapped errors, layout regression tests. | Physical DPI/display-scale review and artwork rights for public distribution. |
| Distribution | Portable EXE and per-user installer, Start menu entry, optional shortcuts/startup, graceful update/uninstall. | Clean Windows machine validation, source/dependency licensing and public signing/release decisions. |

## 12. Inputs that would accelerate the remaining work

- A short, controlled session on the actual SC900 Pro to capture one AULA setting change at a time; do not change settings while the user is gaming or using the mouse for another task.
- Screenshots of the AULA software's Base, Advanced, LED, Buttons, and profile pages if their options differ from the supplied screenshot.
- Confirmation of wired behavior, receiver firmware version, and whether the chosen settings persist after power cycling the mouse.
- A photo or exact regional layout of the physical K95 if image accuracy and key layout matter beyond a representative product image.

## 13. Reference material

- [Corsair K95 RGB Platinum manual](https://www.corsair.com/us/en/explorer/gamer/keyboards/k95-rgb-platinum-mechanical-keyboard-instruction-manual/)
- [OpenRGB Corsair peripheral controller](https://github.com/CalcProgrammer1/OpenRGB/tree/master/Controllers/CorsairPeripheralController) — protocol research reference only
- The AULA SC900 Pro software installed on the development PC, its English UI strings, and the user-provided screenshot in this conversation
