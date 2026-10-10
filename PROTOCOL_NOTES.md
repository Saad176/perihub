# SC900 Pro protocol notes

## Wired support (Devices 0.5.3, 2026-10-06)

The directly connected mouse enumerates as **093A:622C**, product `SC900PRO`, serial descriptor `Pixart 8K MOUSE`; the receiver is **093A:522C**. Both expose configuration interface 3, usage page FF05. The existing nine-byte feature protocol works unchanged on wired USB. Selection prefers the wired endpoint when both are present and rejects multiple matching mice. Detection and the passive battery listener re-evaluate the connection so plugging in USB does not leave the app reading the dongle.

Live wired checks changed and read back numeric DPI, active stage, stage count, all seven polling codes, LOD, ripple, angle snapping, motion sync, all sensor modes, debounce and dormancy. Every setting was restored, and a complete final read matched the initial state. This verifies settings/readback, not externally measured USB polling timing. `devtools/verify_wired.py` records the reversible procedure.

Wired battery input has the same 33-byte format: `09 CC 10 08 00 0F 0F 01` followed by zeros. Masking CC with 7F yields **76%**, four bars. The status high bit differs from the wireless capture; the app continues to display percentage without claiming a charging state. The panel and tray identify **USB wired** instead of 2.4 GHz / 8K receiver.

These commands were recovered from the user's supplied AULA driver and checked against the user's 2.4 GHz receiver (`093A:522C`, HID interface 3, usage page `FF05`, product `SC900PRO`). Every report is nine bytes, begins with `09`, and uses HID feature reports. The UI reads current settings from the device; receiver detection alone does not prove the mouse is awake.

| Setting | Write report | Query report | Reply value |
| --- | --- | --- | --- |
| DPI stage count and active stage | `09 0B count index a b c 00 00` | `09 8B 00...` | Count at byte 2; zero-based stage at byte 3; preserve `a b c` from reply |
| DPI value | `09 0C index low high 00 00 00 00` | `09 8C index...` | `(little-endian bytes 3–4 + 1) × 50` DPI |
| Polling | `09 0D code 00...` | `09 8D 00...` | Code at byte 2 |
| Sensor setting | `09 0A sub value 00...` | `09 8A sub...` | Value at byte 3 |
| Debounce | `09 09 01 ms 00...` | `09 89 01...` | ms at byte 3 |
| Dormancy | `09 09 03 low high 00...` | `09 89 03...` | Seconds in bytes 3–4 |

Polling codes: `0=1000`, `1=500`, `2=250`, `3=125`, `4=2000`, `5=4000`, `6=8000` Hz. Codes 0–2 were captured from AULA changes. Codes 3–6 follow the driver's UI order and each was accepted and echoed by receiver readback. Actual report timing at those four rates has not been independently measured. Polling changes briefly interrupt the pointer while the receiver reconnects; all reversible probes were restored to 1000 Hz.

Sensor subcommands: `1=LOD` (0=1 mm, 1=2 mm), `2=Ripple Control`, `3=Angle Snapping`, `4=Motion Sync` (0=off, 1=on), `5=Sensor Mode` (0=LP, 1=HP, 2=Corded). These mappings follow the AULA UI state and driver handlers. Subcommands 1–5 were reversibly changed, echoed by readback, and restored. Debounce was changed 8→9→8 ms; dormancy 60→61→60 seconds, each verified by readback. DPI stage and polling writes were originally captured from single AULA UI actions; 800 and 900 DPI values were captured and restored. Current stage and all six current DPI values read correctly from the receiver.

The supplied AULA files also show button remapping, macros, five profiles, and LED indicator modes. Their complete write formats and readback have not been decoded. The app does not expose those controls yet. The AULA mouse image is supplied by the user for their personal build; public redistribution needs a rights review.

## Battery research (2026-10-05)

### Resolved: passive input reports (Devices 0.5.1)

The following earlier feature-report investigation is superseded by tracing the input-report path in the supplied executable. AULA's reader at `0x446750` uses overlapped `ReadFile` for 33 bytes. Reports with ID `09` are packed into window message `0x80A` at `0x446846`. Its handler at `0x435EF0` masks the first payload byte with `0x7F` (`0x435F85`) to obtain charge, then maps values below 20/40/60/80 to 1/2/3/4 bars, with 80 and above giving 5 bars (`0x436072`). It averages a rolling ten samples once ten are available. The high bit is used separately for the image state; charging indication is not exposed in Devices until verified on a charging mouse.

A passive read of interface 3 captured repeated **33-byte** reports beginning `09 3D 10 08 00 0F 0F 01`, followed by zeros. `3D` is 61 decimal and maps to **four bars**, consistent with the user's observed AULA display. Live integration verified the app panel displayed **61%**, and tray tooltip displayed **61% (4/5 bars)**. This is the device's reported estimate, not a measured capacity. Devices displays each reported percentage without AULA's ten-sample averaging.

`mouse_battery.py` keeps a separate read handle open, sends no feature/output reports, retries after unplugging, and clears a reading after 120 seconds without a valid report. Decoder validation requires the observed 33-byte length, report ID 09, and percentage no greater than 100. This avoids mistaking nine-byte feature replies for battery data. Battery reads run off the UI thread with bounded read timeouts and stop on exit.

### Earlier investigation

The AULA UI includes full, empty, and charging battery graphics, but a trustworthy live battery value is not yet identified. `09 8F 00...` currently returns `09 8F 03 0C 02 F0 F0 00 00` from this receiver. Disassembly shows byte 2 is connection status, byte 3 (`0C`) selects the SC900 model, byte 4 is connection type, and `F0` is a device variant code used to select driver features. None is a battery percentage. `0x81` replies contain device identifiers. The ordinary settings replies (`0x89` through `0x8D`) also do not carry a battery level. A bounded read-only probe of `0x80` through `0x8F` found no reliably labeled battery report.

AULA was instrumented through both `HidD_SetFeature`/`HidD_GetFeature` and HID `DeviceIoControl` while its mouse page and battery graphic were visible. After startup it polled only `09 81 01...`, which returned the same device identifier every second. Startup queried known settings and profiles but no separately identifiable battery value. The supplied `battery_fullh.png` graphic itself has five colored bars; AULA may be showing that static image. The user sees four of five bars, so do not conclude the graphic is static without observing it change. Do not show raw bytes as a percentage or derive a live level from the image. Further input-report analysis or two independently observed bar levels with matching HID captures is needed before adding a live level to the display and tray tooltip.

The executable loads only four battery image assets (`battery_fullh.png`, `battery_emptyh.png`, `battery_chargingh.png`, and `battery_chargingeh.png`) into its UI image control. There are no separate images for one through four bars. This narrows the likely path to a dynamic crop or a non-image drawing routine, but the captured HID feature traffic still does not identify a charge value. Devices 0.4.1 therefore shows an explicit unavailable state in the mouse panel, tray menu, and tray tooltip.
