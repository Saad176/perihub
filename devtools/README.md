# Development tools

The application and regression tests do not depend on these tools.

- **render_ui.py** renders interface screenshots using fixture data and mocked hardware.
- **test_installer.py** performs an isolated install/update/uninstall check. It refuses to run if an existing Devices installation or startup entry would be affected.
- **capture_*.py**, **disasm_aula.py**, **find_*.py**, **inspect_controls.py** were used to investigate the owner's AULA software. Some require Frida and local files under helping stuff; these reference files are deliberately excluded from Git.
- **probe_*.py**, **verify_wired.py**, **check_keyboard_quit.py** are live hardware diagnostics. They can change device settings or lighting; inspect each script before running it on connected hardware.

Normal automated verification is `python -m unittest discover -s tests -q`, which mocks hardware. Packaged verification is `python tests/smoke_exe.py "Latest build/Devices/Devices.exe"`, which launches the real application and requests graceful shutdown.
