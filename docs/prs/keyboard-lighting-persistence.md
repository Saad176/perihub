# Remember and restore keyboard lighting after restart

Selecting static white worked until Quit or Windows restart; a new app instance always started in onboard mode because keyboard preferences were never saved.

Save the chosen effect, color, brightness and speed in the existing per-user settings. Reapply the saved software effect when the supported keyboard is first detected after startup, including when the mouse panel is selected or the keyboard arrives later. Remember Onboard explicitly. Quit returns the device to its existing onboard profile while retaining the software preference for the next launch. Validate saved values before use.

## Verification

- 58 automated regressions pass, including preference reload, all saved software effect modes, delayed detection, Onboard, corrupt preferences, and Quit/error retention.
- Local Windows executable and setup are rebuilt as 0.6.6.
- Packaged startup, single-instance handoff and graceful quit passed.

## Scope

Local preference persistence only; this does not save a new hardware lighting profile. Mouse configuration startup behavior is unchanged. No system-monitor feature is included.
