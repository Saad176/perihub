# PeriHub repository and releases

Main source repository: https://github.com/Saad176/perihub

This public repository holds the code, assets, tests, build scripts and documentation. Windows installers are attached to Releases. It does not contain a folder named after the original local workspace.

## Recover the source

```powershell
git clone https://github.com/Saad176/perihub.git
cd perihub
python -m pip install -r requirements.txt
pythonw app.py
```

Cloning restores committed and pushed files and their history. It does not install Python, restore ignored vendor reference files or download release assets. Use the release page to download a ready-to-install copy.

## Everyday workflow

Get newer source into an existing checkout:

```powershell
git pull --ff-only
```

Save a completed change:

```powershell
git status
git add .
git commit -m "Describe the change"
git push
```

Review git status before committing. The .gitignore excludes generated builds, caches, local tools and the supplied AULA reference software. Keep a separate backup for excluded reference files.

## Build a Windows installer

Install PyInstaller and Inno Setup, then run from the repository root:

```powershell
python -m pip install pyinstaller
powershell -NoProfile -ExecutionPolicy Bypass -File .\build-release.ps1
```

The portable app is under Latest build/Devices; keep its whole folder. The single installer is Latest build/Devices-<version>-Setup.exe.

## Publish a release

1. Commit and push the source for the version you built.
2. Create a release on GitHub.
3. Create the tag matching the app version, targeting the source commit used to build it.
4. Paste the corresponding docs/releases file as the description.
5. Attach the Setup EXE and wait for the upload.
6. Set it as latest and publish after review.
7. If the installer filename changes, update the README download links and the repository About website link to that release's installer. Confirm both links download the EXE directly.

The installer goes in the release attachment area. GitHub's automatic Source code ZIP/TAR files contain source, not a ready-to-run app.

Artwork permissions and third-party distribution items are tracked in RELEASE_STATUS.md and THIRD_PARTY_NOTICES.md.

[Official release instructions](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository)
